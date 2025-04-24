from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.forms import formset_factory
from django.db.models import Q
from django.urls import reverse
import random

from .models import (
    Question, Choice, Quiz, QuizQuestion, QuizAttempt, QuizAnswer,
    TextAnswer, FileAnswer, VoiceRecording
)
from .forms import (
    QuestionForm, ChoiceFormSet, QuizForm, QuizQuestionFormSet, QuizAnswerForm,
    TextAnswerForm, FileAnswerForm, VoiceRecordingForm
)
from courses.models import Course
from accounts.models import StudentProfile, PaymentProof

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
def take_placement_test(request, course_id):
    course = get_object_or_404(Course, pk=course_id, is_active=True)
    
    # Check if payment is approved
    payment = get_object_or_404(
        PaymentProof, 
        user=request.user, 
        course=course, 
        status='approved'
    )
    
    # Check if user already has a proficiency level
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    if student_profile.proficiency_level:
        messages.info(request, 'You have already taken the placement test.')
        return redirect('student_dashboard')
    
    # Get the placement test quiz for this course
    quiz = get_object_or_404(Quiz, course=course, is_active=True)
    
    # Check if there's an ongoing attempt
    attempt = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz,
        status='in_progress'
    ).first()
    
    if not attempt:
        # Show instructions before starting
        return render(request, 'quizzes/test_instructions.html', {
            'course': course,
            'quiz': quiz
        })
    else:
        # Continue with the ongoing attempt
        return redirect('take_quiz', attempt_id=attempt.id)

@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_active=True)
    
    # Check for existing attempts
    existing_attempt = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz,
        status='in_progress'
    ).first()
    
    if existing_attempt:
        return redirect('take_quiz', attempt_id=existing_attempt.id)
    
    # Create a new attempt
    attempt = QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz
    )
    
    return redirect('take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    quiz = attempt.quiz
    
    # If quiz is already completed, show the results
    if attempt.status in ['completed', 'timed_out']:
        return redirect('quiz_results', attempt_id=attempt.id)
    
    # Get all the questions for this quiz
    quiz_questions = list(quiz.quiz_questions.all().select_related('question'))
    
    # If questions already answered, remove them from the list
    answered_question_ids = QuizAnswer.objects.filter(attempt=attempt).values_list('question_id', flat=True)
    unanswered_questions = [q for q in quiz_questions if q.id not in answered_question_ids]
    
    # Debug info - remove in production
    print(f"Quiz has {len(quiz_questions)} questions")
    print(f"User has answered {len(answered_question_ids)} questions")
    print(f"Unanswered questions: {len(unanswered_questions)}")
    
    # If all questions are answered, complete the quiz
    if not unanswered_questions:
        attempt.status = 'completed'
        attempt.end_time = timezone.now()
        attempt.calculate_score()
        attempt.determine_level()
        attempt.save()
        
        # Update student profile with the determined level
        student_profile = StudentProfile.objects.get(user=request.user)
        student_profile.proficiency_level = attempt.result
        student_profile.save()
        
        return redirect('quiz_results', attempt_id=attempt.id)
    
    # Get a random question from the unanswered questions
    current_question = random.choice(unanswered_questions)
    question_type = current_question.question.question_type
    
    # Check if the question has choices if it's a choice-based question type
    if current_question.question.is_multiple_choice_type():
        choices_count = current_question.question.choices.count()
        if choices_count == 0:
            # Log an error for questions without choices
            print(f"ERROR: Question {current_question.id} has no choices")
            # Skip this question by marking it as answered incorrectly
            QuizAnswer.objects.create(
                attempt=attempt,
                question=current_question,
                is_correct=False,
                time_taken=0
            )
            # Redirect to get a new question
            return redirect('take_quiz', attempt_id=attempt.id)
    
    if request.method == 'POST':
        form = QuizAnswerForm(current_question, request.POST, request.FILES)
        
        if form.is_valid():
            time_taken = form.cleaned_data['time_taken']
            
            # Create a new QuizAnswer
            answer = QuizAnswer(
                attempt=attempt,
                question=current_question,
                time_taken=time_taken
            )
            
            # Process answer based on question type
            if question_type in ['multiple_choice', 'true_false', 'dropdown', 'star_rating', 'image_choice', 'image_rating']:
                # For single-select questions
                selected_choice_id = form.cleaned_data['selected_choice']
                if selected_choice_id:
                    try:
                        selected_choice = Choice.objects.get(pk=selected_choice_id, question=current_question.question)
                        answer.selected_choice = selected_choice
                        answer.is_correct = selected_choice.is_correct
                    except Choice.DoesNotExist:
                        # Handle case where the choice doesn't exist
                        answer.is_correct = False
                else:
                    # No choice selected
                    answer.is_correct = False
            
            elif question_type in ['multi_select', 'likert_scale', 'matrix']:
                # For multi-select questions
                selected_choice_ids = form.cleaned_data['selected_choices']
                if selected_choice_ids and len(selected_choice_ids) > 0:
                    # We'll need custom handling for multi-select questions
                    try:
                        # For now, just select the first choice and mark it correct if it's a correct answer
                        first_choice_id = selected_choice_ids[0]
                        selected_choice = Choice.objects.get(pk=first_choice_id, question=current_question.question)
                        answer.selected_choice = selected_choice
                        answer.is_correct = selected_choice.is_correct
                    except (IndexError, Choice.DoesNotExist):
                        answer.is_correct = False
                else:
                    # No choices selected
                    answer.is_correct = False
            
            elif question_type in ['short_answer', 'long_answer']:
                # For text-based answers
                text = form.cleaned_data['text_answer']
                if text:
                    text_answer = TextAnswer.objects.create(
                        question=current_question.question,
                        student=request.user,
                        text=text
                    )
                    answer.text_answer = text_answer
                    # Text answers need to be manually graded
                    answer.is_correct = False
            
            elif question_type in ['file_upload', 'voice_record']:
                # For file uploads and voice recordings
                uploaded_file = form.cleaned_data['file_answer']
                if uploaded_file:
                    if question_type == 'file_upload':
                        file_answer = FileAnswer.objects.create(
                            question=current_question.question,
                            student=request.user,
                            file=uploaded_file,
                            file_type=uploaded_file.content_type
                        )
                        answer.file_answer = file_answer
                    else:  # voice_record
                        voice_recording = VoiceRecording.objects.create(
                            question=current_question.question,
                            student=request.user,
                            audio_file=uploaded_file,
                            # Would need additional processing to get duration
                            duration=0
                        )
                        answer.voice_recording = voice_recording
                    
                    # File uploads need to be manually graded
                    answer.is_correct = False
            
            answer.save()
            
            # Redirect to continue the quiz
            return redirect('take_quiz', attempt_id=attempt.id)
    else:
        form = QuizAnswerForm(current_question)
    
    # Calculate the time elapsed and remaining
    elapsed_time = (timezone.now() - attempt.start_time).total_seconds()
    total_time = quiz.time_limit * 60  # convert minutes to seconds
    remaining_time = max(0, total_time - elapsed_time)
    
    # Check if time is up
    if remaining_time <= 0:
        attempt.status = 'timed_out'
        attempt.end_time = timezone.now()
        attempt.calculate_score()
        attempt.determine_level()
        attempt.save()
        
        # Update student profile with the determined level
        student_profile = StudentProfile.objects.get(user=request.user)
        student_profile.proficiency_level = attempt.result
        student_profile.save()
        
        messages.warning(request, 'Time is up! Your quiz has been submitted automatically.')
        return redirect('quiz_results', attempt_id=attempt.id)
    
    # Check if the question has valid choices
    has_valid_choices = True
    if current_question.question.is_multiple_choice_type():
        has_valid_choices = current_question.question.choices.exists()
    
    return render(request, 'quizzes/take_quiz.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question': current_question,
        'form': form,
        'remaining_time': remaining_time,
        'question_time_limit': current_question.question.time_limit,
        'question_type': question_type,
        'has_valid_choices': has_valid_choices,
        'progress': len(answered_question_ids) / len(quiz_questions) * 100
    })

@login_required
def quiz_results(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    
    # If quiz is not completed yet, redirect to continue
    if attempt.status == 'in_progress':
        return redirect('take_quiz', attempt_id=attempt.id)
    
    # Get all answers for this attempt
    answers = attempt.answers.all().select_related(
        'question', 'question__question', 'selected_choice',
        'text_answer', 'file_answer', 'voice_recording'
    )
    
    return render(request, 'quizzes/quiz_results.html', {
        'attempt': attempt,
        'answers': answers
    })

@login_required
@user_passes_test(is_admin)
def question_list(request):
    questions = Question.objects.all().select_related('course')
    
    # Filter options
    courses = Course.objects.all()
    difficulty_choices = Question.DIFFICULTY_CHOICES
    
    # Apply filters
    course_id = request.GET.get('course')
    difficulty = request.GET.get('difficulty')
    search = request.GET.get('search')
    
    if course_id:
        questions = questions.filter(course_id=course_id)
    
    if difficulty:
        questions = questions.filter(difficulty=difficulty)
    
    if search:
        questions = questions.filter(text__icontains=search)
    
    return render(request, 'quizzes/question_list.html', {
        'questions': questions,
        'courses': courses,
        'difficulty_choices': difficulty_choices
    })

@login_required
@user_passes_test(is_admin)
def question_create(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        
        if form.is_valid():
            question = form.save()
            
            # Only process formset for multiple choice type questions
            if question.is_multiple_choice_type():
                formset = ChoiceFormSet(request.POST, request.FILES, instance=question)
                if formset.is_valid():
                    formset.save()
                else:
                    # If formset is invalid, delete the question and show errors
                    question.delete()
                    return render(request, 'quizzes/question_form.html', {
                        'form': form,
                        'formset': formset,
                        'title': 'Create Question'
                    })
            
            messages.success(request, 'Question created successfully.')
            return redirect('question_list')
    else:
        form = QuestionForm()
        formset = ChoiceFormSet()
    
    return render(request, 'quizzes/question_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Question'
    })

@login_required
@user_passes_test(is_admin)
def question_update(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES, instance=question)
        
        if form.is_valid():
            question = form.save()
            
            # Only process formset for multiple choice type questions
            if question.is_multiple_choice_type():
                formset = ChoiceFormSet(request.POST, request.FILES, instance=question)
                if formset.is_valid():
                    formset.save()
                else:
                    return render(request, 'quizzes/question_form.html', {
                        'form': form,
                        'formset': formset,
                        'question': question,
                        'title': 'Update Question'
                    })
            
            messages.success(request, 'Question updated successfully.')
            return redirect('question_list')
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)
    
    return render(request, 'quizzes/question_form.html', {
        'form': form,
        'formset': formset,
        'question': question,
        'title': 'Update Question'
    })

@login_required
@user_passes_test(is_admin)
def quiz_list(request):
    quizzes = Quiz.objects.all().select_related('course')
    
    # Filter options
    courses = Course.objects.all()
    
    # Apply filters
    course_id = request.GET.get('course')
    active = request.GET.get('active')
    search = request.GET.get('search')
    
    if course_id:
        quizzes = quizzes.filter(course_id=course_id)
    
    if active == 'true':
        quizzes = quizzes.filter(is_active=True)
    elif active == 'false':
        quizzes = quizzes.filter(is_active=False)
    
    if search:
        quizzes = quizzes.filter(title__icontains=search)
    
    return render(request, 'quizzes/quiz_list.html', {
        'quizzes': quizzes,
        'courses': courses
    })

@login_required
@user_passes_test(is_admin)
def quiz_create(request):
    if request.method == 'POST':
        form = QuizForm(request.POST)
        
        if form.is_valid():
            quiz = form.save()
            messages.success(request, 'Quiz created successfully. Now add questions to it.')
            return redirect('quiz_questions', quiz_id=quiz.id)
    else:
        form = QuizForm()
    
    return render(request, 'quizzes/quiz_form.html', {
        'form': form,
        'title': 'Create Quiz'
    })

@login_required
@user_passes_test(is_admin)
def quiz_update(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Quiz updated successfully.')
            return redirect('quiz_list')
    else:
        form = QuizForm(instance=quiz)
    
    return render(request, 'quizzes/quiz_form.html', {
        'form': form,
        'quiz': quiz,
        'title': 'Update Quiz'
    })

@login_required
@user_passes_test(is_admin)
def quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    if request.method == 'POST':
        formset = QuizQuestionFormSet(request.POST, instance=quiz)
        
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Quiz questions updated successfully.')
            return redirect('quiz_list')
    else:
        formset = QuizQuestionFormSet(instance=quiz)
    
    # Get all available questions for this course
    available_questions = Question.objects.filter(course=quiz.course, is_active=True)
    
    return render(request, 'quizzes/quiz_questions.html', {
        'formset': formset,
        'quiz': quiz,
        'available_questions': available_questions
    })

@login_required
@user_passes_test(is_admin)
def quiz_results_admin(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    attempts = QuizAttempt.objects.filter(quiz=quiz, status__in=['completed', 'timed_out'])
    
    return render(request, 'quizzes/quiz_results_admin.html', {
        'quiz': quiz,
        'attempts': attempts
    })

@login_required
def quiz_timer_update(request, attempt_id):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
        
        if attempt.status == 'in_progress':
            # Check if time is up
            elapsed_time = (timezone.now() - attempt.start_time).total_seconds()
            total_time = attempt.quiz.time_limit * 60  # convert minutes to seconds
            remaining_time = max(0, total_time - elapsed_time)
            
            if remaining_time <= 0:
                attempt.status = 'timed_out'
                attempt.end_time = timezone.now()
                attempt.calculate_score()
                attempt.determine_level()
                attempt.save()
                
                # Update student profile
                student_profile = StudentProfile.objects.get(user=request.user)
                student_profile.proficiency_level = attempt.result
                student_profile.save()
                
                return JsonResponse({'status': 'timeout', 'redirect': reverse('quiz_results', args=[attempt.id])})
            
            return JsonResponse({'status': 'ok', 'remaining_time': remaining_time})
    
    return JsonResponse({'status': 'error'}, status=400)

# Teacher views for grading file and text submissions
@login_required
@user_passes_test(lambda u: u.user_type == 'teacher')
def grade_submissions(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    # Get all the students assigned to this teacher
    student_ids = StudentProfile.objects.filter(assigned_teacher=request.user).values_list('user_id', flat=True)
    
    # Get all attempts by those students for this quiz
    attempts = QuizAttempt.objects.filter(
        quiz=quiz, 
        user_id__in=student_ids,
        status__in=['completed', 'timed_out']
    ).select_related('user')
    
    # Get all answers that need grading (text/file/voice answers)
    pending_answers = QuizAnswer.objects.filter(
        attempt__in=attempts
    ).select_related(
        'attempt', 'question', 'question__question', 
        'text_answer', 'file_answer', 'voice_recording'
    ).filter(
        Q(text_answer__isnull=False) | 
        Q(file_answer__isnull=False) | 
        Q(voice_recording__isnull=False)
    )
    
    return render(request, 'quizzes/grade_submissions.html', {
        'quiz': quiz,
        'attempts': attempts,
        'pending_answers': pending_answers
    })

@login_required
@user_passes_test(lambda u: u.user_type == 'teacher')
def grade_answer(request, answer_id):
    answer = get_object_or_404(QuizAnswer, pk=answer_id)
    
    # Make sure this student is assigned to the teacher
    student_profile = get_object_or_404(StudentProfile, user=answer.attempt.user, assigned_teacher=request.user)
    
    if request.method == 'POST':
        is_correct = request.POST.get('is_correct') == 'true'
        feedback = request.POST.get('feedback', '')
        
        answer.is_correct = is_correct
        answer.feedback = feedback
        answer.save()
        
        # Recalculate the quiz score
        attempt = answer.attempt
        attempt.calculate_score()
        attempt.save()
        
        messages.success(request, 'Answer graded successfully.')
        return redirect('grade_submissions', quiz_id=answer.attempt.quiz.id)
    
    return render(request, 'quizzes/grade_answer.html', {
        'answer': answer
    })