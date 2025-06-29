from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Avg, Count, F, Q
from django.db import transaction
from django.urls import reverse
import json
import logging
from datetime import timedelta
from django.urls import reverse
import logging
logger = logging.getLogger(__name__)


from .models import (
    Quiz, Question, Choice, QuizAttempt, QuizAnswer,
    TextAnswer, FileAnswer, VoiceRecording
)
from .forms import (
    QuizForm, QuestionForm, QuestionFormSet, ChoiceForm, ChoiceFormSet,
    QuizAnswerForm, TextAnswerForm, FileAnswerForm, VoiceRecordingForm
)
from courses.models import Course
from accounts.models import PaymentProof, StudentProfile

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_staff or user.is_superuser

def is_teacher_or_admin(user):
    return user.user_type == 'teacher' or user.is_staff or user.is_superuser

# Quiz Management Views (Teacher/Admin)

@login_required
@user_passes_test(is_teacher_or_admin)
def quiz_list(request):
    """View to list all quizzes for a teacher"""
    quizzes = Quiz.objects.all().order_by('-created_at')
    
    return render(request, 'quizzes/quiz_list.html', {
        'quizzes': quizzes
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def create_quiz(request):
    """View to create a new quiz with questions"""
    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)
        
        if quiz_form.is_valid():
            quiz = quiz_form.save(commit=False)
            quiz.save()
            
            # Redirect to add questions
            messages.success(request, f"Quiz '{quiz.title}' created successfully. Now add questions.")
            return redirect('edit_quiz_questions', quiz_id=quiz.id)
    else:
        quiz_form = QuizForm()
    
    return render(request, 'quizzes/create_quiz.html', {
        'quiz_form': quiz_form
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def edit_quiz(request, quiz_id):
    """View to edit quiz details"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, f"Quiz '{quiz.title}' updated successfully.")
            return redirect('quiz_list')
    else:
        form = QuizForm(instance=quiz)
    
    return render(request, 'quizzes/edit_quiz.html', {
        'form': form,
        'quiz': quiz
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def edit_quiz_questions(request, quiz_id):
    """View to edit questions for a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.method == 'POST':
        formset = QuestionFormSet(request.POST, request.FILES, instance=quiz)
        
        if formset.is_valid():
            questions = formset.save(commit=False)
            
            # Process the saved and deleted forms
            for question in formset.deleted_objects:
                question.delete()
            
            for question in questions:
                question.save()
            
            formset.save_m2m()
            
            messages.success(request, "Questions updated successfully.")
            return redirect('quiz_detail', quiz_id=quiz.id)
    else:
        formset = QuestionFormSet(instance=quiz)
    
    # Calculate total points
    total_points = quiz.questions.aggregate(total=Sum('points'))['total'] or 0
    
    return render(request, 'quizzes/edit_quiz_questions.html', {
        'quiz': quiz,
        'formset': formset,
        'total_points': total_points,
        'max_points': quiz.max_points
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def edit_question_choices(request, question_id):
    """View to edit choices for a question"""
    question = get_object_or_404(Question, id=question_id)
    quiz = question.quiz
    
    if request.method == 'POST':
        formset = ChoiceFormSet(request.POST, request.FILES, instance=question)
        
        if formset.is_valid():
            choices = formset.save(commit=False)
            
            # Process the saved and deleted forms
            for choice in formset.deleted_objects:
                choice.delete()
            
            for choice in choices:
                choice.save()
            
            formset.save_m2m()
            
            messages.success(request, "Choices updated successfully.")
            return redirect('edit_quiz_questions', quiz_id=quiz.id)
    else:
        formset = ChoiceFormSet(instance=question)
    
    return render(request, 'quizzes/edit_question_choices.html', {
        'question': question,
        'quiz': quiz,
        'formset': formset
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def quiz_detail(request, quiz_id):
    """View to show quiz details and questions"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all().order_by('order')
    
    # Calculate total points and check if they match max_points
    total_points = questions.aggregate(total=Sum('points'))['total'] or 0
    points_match = total_points == quiz.max_points
    
    return render(request, 'quizzes/quiz_detail.html', {
        'quiz': quiz,
        'questions': questions,
        'total_points': total_points,
        'points_match': points_match
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def delete_quiz(request, quiz_id):
    """View to delete a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.method == 'POST':
        quiz_title = quiz.title
        quiz.delete()
        messages.success(request, f"Quiz '{quiz_title}' has been deleted.")
        return redirect('quiz_list')
    
    return render(request, 'quizzes/delete_quiz.html', {
        'quiz': quiz
    })

# Quiz Taking Views (Students)

@login_required
def student_quiz_list(request):
    """View to list available quizzes for students"""
    # Get quizzes from courses the student is enrolled in
    student_courses = request.user.course_periods.all().values_list('course', flat=True)
    available_quizzes = Quiz.objects.filter(
        course__in=student_courses, 
        is_active=True
    ).order_by('course__title', 'title')
    
    # Get quizzes the student has already attempted
    attempted_quizzes = QuizAttempt.objects.filter(
        student=request.user
    ).values_list('quiz_id', flat=True)
    
    return render(request, 'quizzes/student_quiz_list.html', {
        'available_quizzes': available_quizzes,
        'attempted_quizzes': attempted_quizzes
    })

@login_required
def start_quiz(request, quiz_id):
    """View to start a quiz attempt"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if quiz is active
    if not quiz.is_active:
        messages.error(request, "This quiz is not currently available.")
        return redirect('student_quiz_list')
    
    # Check if student is enrolled in the course
    student_courses = request.user.course_periods.all().values_list('course', flat=True)
    if quiz.course.id not in student_courses and not quiz.is_placement_test:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('student_quiz_list')
    
    # Check if the quiz has any questions
    if quiz.questions.count() == 0:
        messages.error(request, "This quiz has no questions yet.")
        return redirect('student_quiz_list')
    
    # Create a new quiz attempt
    attempt = QuizAttempt.objects.create(
        student=request.user,
        quiz=quiz
    )
    
    return redirect('take_quiz', attempt_id=attempt.id)



@login_required
def take_quiz(request, attempt_id):
    """View to take a quiz with enforced time limits and no ability to change previous answers"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    quiz = attempt.quiz
    
    # Check if the attempt is already completed
    if attempt.completed:
        return redirect('quiz_results', attempt_id=attempt.id)
    
    # Get all questions for this quiz
    questions = quiz.questions.all().order_by('order')
    
    if not questions.exists():
        messages.error(request, "This quiz doesn't have any questions.")
        return redirect('student_quiz_list')
    
    # Get the current question (from GET parameter or first question)
    current_question_num = int(request.GET.get('question', 1))
    
    # Check if the student is trying to go back to a previous question
    max_answered_question = QuizAnswer.objects.filter(
        quiz_attempt=attempt
    ).count()
    
    # If trying to access a previous question, redirect to the current unanswered question
    # Allow viewing the current question or the next unanswered one
    if current_question_num < max_answered_question + 1:
        messages.warning(request, "You cannot go back to previous questions once they are answered.")
        return redirect(f"{reverse('take_quiz', kwargs={'attempt_id': attempt.id})}?question={max_answered_question + 1}")
    
    # Make sure the question number is valid
    if current_question_num < 1:
        current_question_num = 1
    
    if current_question_num > questions.count():
        # If all questions are answered, complete the quiz
        if max_answered_question >= questions.count():
            attempt.complete()
            return redirect('quiz_results', attempt_id=attempt.id)
        else:
            current_question_num = max_answered_question + 1
    
    current_question = questions[current_question_num - 1]
    
    # Check if an answer already exists for this question
    existing_answer = QuizAnswer.objects.filter(
        quiz_attempt=attempt,
        question=current_question
    ).first()
    
    # If answer exists for this question, proceed to the next unanswered question
    if existing_answer:
        next_unanswered = max_answered_question + 1
        if next_unanswered <= questions.count():
            return redirect(f"{reverse('take_quiz', kwargs={'attempt_id': attempt.id})}?question={next_unanswered}")
        else:
            # All questions answered, complete the quiz
            attempt.complete()
            return redirect('quiz_results', attempt_id=attempt.id)
    
    # Check if the timer for this question has expired
    question_timer_key = f'{attempt.id}_{current_question.id}'
    timer_data = request.session.get('quiz_timers', {}).get(question_timer_key)
    
    if timer_data is not None and int(timer_data) <= 0:
        # Time expired for this question, create an empty answer and move to the next question
        QuizAnswer.objects.create(
            quiz_attempt=attempt,
            question=current_question,
            is_correct=False,
            points_earned=0
        )
        
        # Move to next question
        next_question = current_question_num + 1
        if next_question <= questions.count():
            messages.warning(request, "Time expired for the previous question.")
            return redirect(f"{reverse('take_quiz', kwargs={'attempt_id': attempt.id})}?question={next_question}")
        else:
            # All questions answered, complete the quiz
            attempt.complete()
            return redirect('quiz_results', attempt_id=attempt.id)
    
    if request.method == 'POST':
        # Handle different question types
        if current_question.question_type in ['multiple_choice', 'true_false', 'dropdown']:
            # Handle choice-based questions
            choice_id = request.POST.get('choice')
            if not choice_id:
                messages.error(request, "Please select an answer.")
                return redirect('take_quiz', attempt_id=attempt.id)
            
            selected_choice = get_object_or_404(Choice, id=choice_id, question=current_question)
            
            # Create answer (always create new, not update)
            answer = QuizAnswer.objects.create(
                quiz_attempt=attempt,
                question=current_question,
                selected_choice=selected_choice,
                is_correct=selected_choice.is_correct,
                points_earned=current_question.points if selected_choice.is_correct else 0
            )
        
        elif current_question.question_type == 'multi_select':
            # Handle multi-select questions
            choice_ids = request.POST.getlist('choices[]')
            
            if not choice_ids:
                messages.error(request, "Please select at least one answer.")
                return redirect('take_quiz', attempt_id=attempt.id)
            
            # Get the selected choices
            selected_choices = Choice.objects.filter(id__in=choice_ids, question=current_question)
            
            # Check if all selected choices are correct
            all_correct = all(choice.is_correct for choice in selected_choices)
            # Check if all correct choices were selected
            all_correct_selected = selected_choices.filter(is_correct=True).count() == current_question.choices.filter(is_correct=True).count()
            
            # A multi-select question is correct only if all correct choices are selected and no incorrect choices are selected
            is_correct = all_correct and all_correct_selected
            
            # Create the answer
            answer = QuizAnswer.objects.create(
                quiz_attempt=attempt,
                question=current_question,
                is_correct=is_correct,
                points_earned=current_question.points if is_correct else 0
            )
            
            # Add selected choices
            answer.selected_choices.add(*selected_choices)
        
        elif current_question.question_type in ['short_answer', 'long_answer']:
            # Handle text-based questions
            text_answer = request.POST.get('text_answer', '')
            
            # Create or update the TextAnswer
            text_obj, created = TextAnswer.objects.update_or_create(
                question=current_question,
                student=request.user,
                defaults={'text': text_answer}
            )
            
            # Create the QuizAnswer
            answer = QuizAnswer.objects.create(
                quiz_attempt=attempt,
                question=current_question,
                text_answer=text_answer
            )
        
        elif current_question.question_type == 'file_upload':
            # Handle file upload questions
            if 'file_answer' in request.FILES:
                uploaded_file = request.FILES['file_answer']
                
                # Create or update the FileAnswer
                file_obj, created = FileAnswer.objects.update_or_create(
                    question=current_question,
                    student=request.user,
                    defaults={
                        'file': uploaded_file,
                        'file_type': uploaded_file.content_type
                    }
                )
                
                # Create the QuizAnswer
                answer = QuizAnswer.objects.create(
                    quiz_attempt=attempt,
                    question=current_question,
                    file_answer=file_obj
                )
            else:
                messages.error(request, "Please upload a file.")
                return redirect('take_quiz', attempt_id=attempt.id)
        
        elif current_question.question_type == 'voice_record':
            # Handle voice recording questions
            if 'voice_data' in request.POST:
                # Process voice recordings from base64 string
                voice_data = request.POST.get('voice_data', '')
                if voice_data and voice_data.startswith('data:audio'):
                    try:
                        # Extract base64 part
                        format, base64_data = voice_data.split(';base64,')
                        # Create a ContentFile from the base64 data
                        from django.core.files.base import ContentFile
                        import base64
                        import uuid
                
                        file_data = base64.b64decode(base64_data)
                        file_content = ContentFile(file_data)
                        
                        # Generate a unique filename
                        filename = f"voice_{uuid.uuid4()}.wav"
                        
                        # Create or update the VoiceRecording
                        voice_obj, created = VoiceRecording.objects.update_or_create(
                            question=current_question,
                            student=request.user,
                            defaults={'duration': request.POST.get('duration', 0)}
                        )
                        voice_obj.recording.save(filename, file_content, save=True)
                        
                        # Create the QuizAnswer
                        answer = QuizAnswer.objects.create(
                            quiz_attempt=attempt,
                            question=current_question,
                            voice_answer=voice_obj
                        )
                    except Exception as e:
                        logger.error(f"Error processing voice recording: {str(e)}")
                        messages.error(request, "There was an error processing your voice recording.")
                        return redirect('take_quiz', attempt_id=attempt.id)
                else:
                    messages.error(request, "Please record your voice.")
                    return redirect('take_quiz', attempt_id=attempt.id)
            else:
                messages.error(request, "Please record your voice.")
                return redirect('take_quiz', attempt_id=attempt.id)
        
        else:
            # Handle other question types or fallback
            messages.warning(request, f"Question type '{current_question.get_question_type_display()}' is not fully supported yet.")
            # Create a placeholder answer to allow progress
            answer = QuizAnswer.objects.create(
                quiz_attempt=attempt,
                question=current_question,
                is_correct=False,
                points_earned=0
            )
        
        # Clear timer for this question
        if 'quiz_timers' in request.session:
            if question_timer_key in request.session['quiz_timers']:
                del request.session['quiz_timers'][question_timer_key]
                request.session.modified = True
        
        # Move to the next question or complete the quiz
        if current_question_num < questions.count():
            # Use query string for next question
            base_url = reverse('take_quiz', kwargs={'attempt_id': attempt.id})
            next_question = current_question_num + 1
            return redirect(f"{base_url}?question={next_question}")
        else:
            # Complete the quiz attempt
            attempt.complete()
            return redirect('quiz_results', attempt_id=attempt.id)
    
    # For GET requests, show the form for the current question
    if current_question.question_type in ['multiple_choice', 'true_false', 'dropdown']:
        choices = current_question.choices.all()
        selected_choice_id = None
        if existing_answer and existing_answer.selected_choice:
            selected_choice_id = existing_answer.selected_choice.id
        
        return render(request, 'quizzes/take_quiz.html', {
            'attempt': attempt,
            'quiz': quiz,
            'question': current_question,
            'question_number': current_question_num,
            'total_questions': questions.count(),
            'choices': choices,
            'selected_choice_id': selected_choice_id,
            'time_limit': current_question.time_limit
        })
    
    elif current_question.question_type == 'multi_select':
        choices = current_question.choices.all()
        
        # Get previously selected choices
        selected_choice_ids = []
        if existing_answer:
            # Retrieve previously selected choices
            selected_choices = existing_answer.selected_choices.all() if hasattr(existing_answer, 'selected_choices') else []
            selected_choice_ids = [choice.id for choice in selected_choices]
        
        return render(request, 'quizzes/take_quiz_multi_select.html', {
            'attempt': attempt,
            'quiz': quiz,
            'question': current_question,
            'question_number': current_question_num,
            'total_questions': questions.count(),
            'choices': choices,
            'selected_choice_ids': selected_choice_ids,
            'time_limit': current_question.time_limit
        })
    
    elif current_question.question_type in ['short_answer', 'long_answer']:
        # Retrieve existing text answer if any
        text_answer = ''
        if existing_answer and existing_answer.text_answer:
            text_answer = existing_answer.text_answer
        
        return render(request, 'quizzes/take_quiz_text.html', {
            'attempt': attempt,
            'quiz': quiz,
            'question': current_question,
            'question_number': current_question_num,
            'total_questions': questions.count(),
            'text_answer': text_answer,
            'time_limit': current_question.time_limit
        })
    
    elif current_question.question_type == 'file_upload':
        # Check if there's an existing file
        existing_file = None
        if existing_answer and existing_answer.file_answer:
            existing_file = existing_answer.file_answer.file
        
        return render(request, 'quizzes/take_quiz_file.html', {
            'attempt': attempt,
            'quiz': quiz,
            'question': current_question,
            'question_number': current_question_num,
            'total_questions': questions.count(),
            'existing_file': existing_file,
            'time_limit': current_question.time_limit
        })
    
    elif current_question.question_type == 'voice_record':
        # Check if there's an existing recording
        existing_recording = None
        if existing_answer and existing_answer.voice_answer:
            existing_recording = existing_answer.voice_answer.recording
        
        return render(request, 'quizzes/take_quiz_voice.html', {
            'attempt': attempt,
            'quiz': quiz,
            'question': current_question,
            'question_number': current_question_num,
            'total_questions': questions.count(),
            'existing_recording': existing_recording,
            'time_limit': current_question.time_limit
        })
    
    # Default fallback template for other question types
    return render(request, 'quizzes/take_quiz_generic.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question': current_question,
        'question_number': current_question_num,
        'total_questions': questions.count(),
        'time_limit': current_question.time_limit
    })


@login_required
def quiz_results(request, attempt_id):
    """View to show results of a quiz attempt"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    quiz = attempt.quiz
    
    # Mark the attempt as completed if not already
    if not attempt.completed:
        attempt.complete()
    
    # Get all questions and answers
    questions = quiz.questions.all().order_by('order')
    answers = attempt.answers.all()
    
    # Create a dictionary mapping questions to answers
    question_answers = {}
    for answer in answers:
        question_answers[answer.question_id] = answer
    
    # Calculate statistics
    total_questions = questions.count()
    answered_questions = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    
    # Calculate total points earned and possible
    points_earned = answers.aggregate(total=Sum('points_earned'))['total'] or 0
    total_possible = questions.aggregate(total=Sum('points'))['total'] or 0
    
    # Determine if this is a placement test
    is_placement_test = quiz.is_placement_test
    
    # For placement tests, update the student's proficiency level
    if is_placement_test and attempt.result:
        profile = StudentProfile.objects.get(user=request.user)
        profile.proficiency_level = attempt.result
        profile.save()
    
    return render(request, 'quizzes/quiz_results.html', {
        'attempt': attempt,
        'quiz': quiz,
        'questions': questions,
        'question_answers': question_answers,
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'correct_answers': correct_answers,
        'points_earned': points_earned,
        'total_possible': total_possible,
        'is_placement_test': is_placement_test
    })

@login_required
def quiz_review(request, attempt_id):
    """View to review a completed quiz with answers"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    quiz = attempt.quiz
    
    # Only allow reviewing completed quizzes
    if not attempt.completed:
        messages.error(request, "You can only review completed quizzes.")
        return redirect('student_quiz_list')
    
    # Get all questions and answers
    questions = quiz.questions.all().order_by('order')
    answers = attempt.answers.all()
    
    # Create a dictionary mapping questions to answers
    question_answers = {}
    for answer in answers:
        question_answers[answer.question_id] = answer
    
    return render(request, 'quizzes/quiz_review.html', {
        'attempt': attempt,
        'quiz': quiz,
        'questions': questions,
        'question_answers': question_answers
    })

# Teacher/Admin Analytics Views

@login_required
@user_passes_test(is_teacher_or_admin)
def quiz_analytics(request, quiz_id):
    """View to show analytics for a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Get all attempts for this quiz
    attempts = QuizAttempt.objects.filter(quiz=quiz, completed=True)
    
    # Calculate general statistics
    total_attempts = attempts.count()
    if total_attempts > 0:
        avg_score = attempts.aggregate(avg=Avg('score'))['avg']
        pass_rate = attempts.filter(result='passed').count() / total_attempts * 100
    else:
        avg_score = 0
        pass_rate = 0
    
    # Get question-level statistics
    questions = quiz.questions.all().order_by('order')
    question_stats = []
    
    for question in questions:
        # Get all answers for this question
        answers = QuizAnswer.objects.filter(
            quiz_attempt__in=attempts,
            question=question
        )
        
        # Calculate question statistics
        total_answers = answers.count()
        if total_answers > 0:
            correct_answers = answers.filter(is_correct=True).count()
            correct_rate = correct_answers / total_answers * 100
        else:
            correct_answers = 0
            correct_rate = 0
        
        question_stats.append({
            'question': question,
            'total_answers': total_answers,
            'correct_answers': correct_answers,
            'correct_rate': correct_rate
        })
    
    return render(request, 'quizzes/quiz_analytics.html', {
        'quiz': quiz,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'pass_rate': pass_rate,
        'question_stats': question_stats
    })

# AJAX Views for handling dynamic functionality

@login_required
@user_passes_test(is_teacher_or_admin)
def update_question_order(request):
    """AJAX view to update question order"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            question_id = data.get('question_id')
            new_order = data.get('order')
            
            if question_id and new_order is not None:
                question = Question.objects.get(id=question_id)
                question.order = new_order
                question.save()
                return JsonResponse({'success': True})
            
            return JsonResponse({'success': False, 'error': 'Invalid data'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def update_timer(request, attempt_id):
    """AJAX view to update question timer"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get data from request
            data = json.loads(request.body)
            question_id = data.get('question_id')
            time_remaining = data.get('time_remaining')
            
            # Verify the attempt belongs to the user
            attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
            
            # Store the time remaining in the session
            if not request.session.get('quiz_timers'):
                request.session['quiz_timers'] = {}
            
            request.session['quiz_timers'][f'{attempt_id}_{question_id}'] = time_remaining
            request.session.modified = True
            
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def get_timer(request, attempt_id):
    """AJAX view to get question timer"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get question ID from GET parameters
            question_id = request.GET.get('question_id')
            
            # Verify the attempt belongs to the user
            attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
            
            # Get the time remaining from the session
            quiz_timers = request.session.get('quiz_timers', {})
            time_remaining = quiz_timers.get(f'{attempt_id}_{question_id}')
            
            # If no time is stored, use the question's time limit
            if time_remaining is None:
                question = get_object_or_404(Question, id=question_id)
                time_remaining = question.time_limit
            
            return JsonResponse({'success': True, 'time_remaining': time_remaining})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def take_placement_test(request, course_id):
    """View to take a placement test for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Find the placement test for this course
    placement_test = get_object_or_404(Quiz, course=course, is_placement_test=True, is_active=True)
    
    # Check if the student is enrolled or has an approved payment for this course
    is_enrolled = False
    student_payment = PaymentProof.objects.filter(
        user=request.user,
        course=course,
        status='approved'
    ).exists()
    
    if student_payment:
        is_enrolled = True
    
    if not is_enrolled:
        messages.error(request, "You must be enrolled in this course to take the placement test.")
        return redirect('student_dashboard')
    
    # Check if the student has already taken the placement test
    existing_attempt = QuizAttempt.objects.filter(
        student=request.user,
        quiz=placement_test,
        completed=True
    ).exists()
    
    if existing_attempt:
        messages.info(request, "You have already taken the placement test for this course.")
        return redirect('student_dashboard')
    
    # Start a new quiz attempt
    attempt = QuizAttempt.objects.create(
        student=request.user,
        quiz=placement_test
    )
    
    return redirect('take_quiz', attempt_id=attempt.id)