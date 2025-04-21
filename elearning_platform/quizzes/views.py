from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.forms import formset_factory
from django.db.models import Q
from django.urls import reverse
import random

from .models import Question, Choice, Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from .forms import QuestionForm, ChoiceFormSet, QuizForm, QuizQuestionFormSet, QuizAnswerForm
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
    quiz_questions = list(quiz.quiz_questions.all())
    
    # If questions already answered, remove them from the list
    answered_questions = QuizAnswer.objects.filter(attempt=attempt).values_list('question_id', flat=True)
    unanswered_questions = [q for q in quiz_questions if q.id not in answered_questions]
    
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
    
    if request.method == 'POST':
        form = QuizAnswerForm(current_question, request.POST)
        if form.is_valid():
            selected_choice_id = form.cleaned_data['selected_choice']
            time_taken = form.cleaned_data['time_taken']
            
            selected_choice = get_object_or_404(Choice, pk=selected_choice_id)
            
            # Save the answer
            answer = QuizAnswer(
                attempt=attempt,
                question=current_question,
                selected_choice=selected_choice,
                time_taken=time_taken
            )
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
    
    return render(request, 'quizzes/take_quiz.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question': current_question,
        'form': form,
        'remaining_time': remaining_time,
        'question_time_limit': current_question.question.time_limit,
        'progress': len(answered_questions) / len(quiz_questions) * 100
    })

@login_required
def quiz_results(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    
    # If quiz is not completed yet, redirect to continue
    if attempt.status == 'in_progress':
        return redirect('take_quiz', attempt_id=attempt.id)
    
    # Get all answers for this attempt
    answers = attempt.answers.all().select_related('question', 'question__question', 'selected_choice')
    
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
        form = QuestionForm(request.POST)
        formset = ChoiceFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            question = form.save()
            formset.instance = question
            formset.save()
            
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
        form = QuestionForm(request.POST, instance=question)
        formset = ChoiceFormSet(request.POST, instance=question)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
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