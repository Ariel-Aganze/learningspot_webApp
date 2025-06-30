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
from django.forms import inlineformset_factory

logger = logging.getLogger(__name__)

from .models import (
    Quiz, Question, Choice, QuizAttempt, QuizAnswer, QuizQuestion,
    TextAnswer, FileAnswer, VoiceRecording
)
from .forms import (
    QuizForm, QuestionForm, QuestionFormSet, ChoiceForm, ChoiceFormSet,
    QuizAnswerForm, TextAnswerForm, FileAnswerForm, VoiceRecordingForm
)
from courses.models import Course, ContentView
from accounts.models import PaymentProof, StudentProfile

# Helper Functions
def get_quiz_questions(quiz):
    """
    Helper function to get all questions for a quiz,
    checking both direct and indirect relationships
    """
    # First try direct relationship
    direct_questions = quiz.questions.all().order_by('order')
    
    # If no direct questions, try through QuizQuestion
    if not direct_questions.exists():
        indirect_questions = Question.objects.filter(
            quizquestion__quiz=quiz
        ).order_by('quizquestion__order')
        return indirect_questions
    
    return direct_questions

def get_quiz_attempt(attempt_id, user):
    """
    Helper function to get quiz attempt,
    checking both student and user fields
    """
    try:
        # First try with student field
        return QuizAttempt.objects.get(id=attempt_id, student=user)
    except Exception:
        # Then try with user field
        try:
            return QuizAttempt.objects.get(id=attempt_id, user=user)
        except Exception:
            return None

def process_quiz_answer_form(form, attempt, question):
    """Helper function to process quiz answer form with field compatibility"""
    answer = form.save(commit=False)
    
    # Set both field patterns for maximum compatibility
    answer.quiz_attempt = attempt
    answer.attempt = attempt
    answer.question = question
    
    # If QuizQuestion exists, set it too
    quiz_question = QuizQuestion.objects.filter(quiz=attempt.quiz, question=question).first()
    if quiz_question:
        answer.quiz_question = quiz_question
    
    answer.save()
    return answer

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
            return redirect('quiz_detail', quiz_id=quiz.id)
    else:
        form = QuizForm(instance=quiz)
    
    return render(request, 'quizzes/edit_quiz.html', {
        'quiz': quiz,
        'form': form
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def edit_quiz_questions(request, quiz_id):
    """View to edit quiz questions"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Get existing questions from both relationships
    existing_questions = get_quiz_questions(quiz)
    
    # Calculate total points
    total_points = existing_questions.aggregate(total=Sum('points'))['total'] or 0
    max_points = quiz.max_points
    
    if request.method == 'POST':
        formset = QuestionFormSet(request.POST, request.FILES, instance=quiz)
        
        if formset.is_valid():
            # Save formset
            questions = formset.save(commit=False)
            
            # Process each question
            for question in questions:
                question.quiz = quiz
                question.save()
            
            # Handle deleted questions
            for obj in formset.deleted_objects:
                obj.delete()
                
            # Save many-to-many relations
            formset.save_m2m()
            
            messages.success(request, "Questions saved successfully.")
            return redirect('quiz_detail', quiz_id=quiz.id)
        else:
            messages.error(request, "There were errors in the form. Please check below.")
    else:
        formset = QuestionFormSet(instance=quiz)
    
    return render(request, 'quizzes/edit_quiz_questions.html', {
        'quiz': quiz,
        'formset': formset,
        'total_points': total_points,
        'max_points': max_points
    })

@login_required
@user_passes_test(is_teacher_or_admin)
def edit_question_choices(request, question_id):
    """View to edit choices for a question"""
    question = get_object_or_404(Question, id=question_id)
    quiz = question.quiz
    
    # Use the existing ChoiceFormSet from forms.py instead of redefining it here
    
    if request.method == 'POST':
        formset = ChoiceFormSet(request.POST, request.FILES, instance=question)
        if formset.is_valid():
            formset.save()
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
    questions = get_quiz_questions(quiz)
    
    # Calculate total points and check if they match max_points
    total_points = questions.aggregate(total=Sum('points'))['total'] or 0
    points_match = total_points == quiz.max_points
    
    # Handle points adjustment if form submitted
    if request.method == 'POST' and 'adjust_max_points' in request.POST:
        adjustment_type = request.POST.get('adjustment_type')
        
        if adjustment_type == 'set_to_total':
            # Update max_points to match total
            quiz.max_points = total_points
            quiz.save()
            messages.success(request, f"Quiz max points updated to {total_points}.")
            return redirect('quiz_detail', quiz_id=quiz.id)
            
        elif adjustment_type == 'adjust_questions' and questions.exists():
            # Distribute max_points evenly among questions
            question_count = questions.count()
            points_per_question = quiz.max_points // question_count
            remainder = quiz.max_points % question_count
            
            with transaction.atomic():
                for i, question in enumerate(questions):
                    # Add remainder to first question if needed
                    if i == 0:
                        question.points = points_per_question + remainder
                    else:
                        question.points = points_per_question
                    question.save()
            
            messages.success(request, f"Points distributed evenly across {question_count} questions.")
            return redirect('quiz_detail', quiz_id=quiz.id)
    
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

@login_required
@user_passes_test(is_teacher_or_admin)
def quiz_analytics(request, quiz_id):
    """View to show analytics for a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Get all attempts for this quiz
    attempts = QuizAttempt.objects.filter(quiz=quiz).select_related('student')
    
    # Calculate statistics
    total_attempts = attempts.count()
    completed_attempts = attempts.filter(Q(completed=True) | Q(status='completed')).count()
    
    # Calculate average score for completed attempts
    avg_score = attempts.filter(
        Q(completed=True) | Q(status='completed')
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    # Calculate result distribution
    result_counts = attempts.filter(
        Q(completed=True) | Q(status='completed')
    ).values('result').annotate(count=Count('id'))
    
    result_distribution = {}
    for item in result_counts:
        if item['result']:
            result_distribution[item['result']] = item['count']
    
    # Get top-performing questions (highest percentage of correct answers)
    questions = get_quiz_questions(quiz)
    question_stats = []
    
    for question in questions:
        # Get answers for this question using both relationship patterns
        answers = QuizAnswer.objects.filter(
            Q(question=question) | Q(quiz_question__question=question)
        ).filter(
            Q(quiz_attempt__quiz=quiz) | Q(attempt__quiz=quiz)
        )
        
        total_answers = answers.count()
        correct_answers = answers.filter(is_correct=True).count()
        
        if total_answers > 0:
            correct_percentage = (correct_answers / total_answers) * 100
        else:
            correct_percentage = 0
        
        question_stats.append({
            'question': question,
            'total_answers': total_answers,
            'correct_answers': correct_answers,
            'correct_percentage': correct_percentage
        })
    
    # Sort question stats by correct percentage (lowest first)
    question_stats.sort(key=lambda x: x['correct_percentage'])
    
    return render(request, 'quizzes/quiz_analytics.html', {
        'quiz': quiz,
        'total_attempts': total_attempts,
        'completed_attempts': completed_attempts,
        'avg_score': avg_score,
        'result_distribution': result_distribution,
        'question_stats': question_stats
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
    
    # Get all of the student's completed quiz attempts
    completed_attempts = QuizAttempt.objects.filter(
        student=request.user,
        quiz__in=available_quizzes
    ).filter(
        Q(completed=True) | Q(status='completed')
    ).select_related('quiz')
    
    # Create a dictionary mapping quiz IDs to attempt IDs
    attempt_dict = {attempt.quiz_id: attempt.id for attempt in completed_attempts}
    
    # Enhance quiz objects with attempt information
    quiz_data = []
    for quiz in available_quizzes:
        quiz_data.append({
            'quiz': quiz,
            'is_attempted': quiz.id in attempt_dict,
            'attempt_id': attempt_dict.get(quiz.id)
        })
    
    return render(request, 'quizzes/student_quiz_list.html', {
        'quiz_data': quiz_data
    })

@login_required
def take_placement_test(request, course_id):
    """View to take a placement test for a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Find the placement test for this course
    placement_test = Quiz.objects.filter(
        course=course, 
        is_placement_test=True,
        is_active=True
    ).first()
    
    if not placement_test:
        messages.error(request, "No placement test is available for this course.")
        return redirect('course_detail', slug=course.slug)
    
    # Check if the student has already taken this placement test
    existing_attempt = QuizAttempt.objects.filter(
        (Q(student=request.user) | Q(user=request.user)) &
        Q(quiz=placement_test) &
        (Q(completed=True) | Q(status='completed'))
    ).first()
    
    if existing_attempt:
        messages.info(request, "You have already taken the placement test for this course.")
        return redirect('quiz_results', attempt_id=existing_attempt.id)
    
    # Create a new quiz attempt
    attempt = QuizAttempt.objects.create(
        student=request.user,
        quiz=placement_test
    )
    
    return redirect('take_quiz', attempt_id=attempt.id)

@login_required
def start_quiz(request, quiz_id):
    """View to start a quiz attempt"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if quiz is active
    if not quiz.is_active:
        messages.error(request, "This quiz is not currently available.")
        return redirect('student_quiz_list')
    
    # Check if student has already completed this quiz
    existing_completed_attempts = QuizAttempt.objects.filter(
        student=request.user, 
        quiz=quiz
    ).filter(
        Q(completed=True) | Q(status='completed')
    ).exists()
    
    if existing_completed_attempts:
        messages.warning(request, "You have already completed this quiz. Only one attempt is allowed.")
        return redirect('student_quiz_list')
    
    # Check if student is enrolled in the course - Use PaymentProof instead of course_periods
    is_enrolled = PaymentProof.objects.filter(
        user=request.user,
        course=quiz.course,
        status='approved'
    ).exists()
    
    # Allow access if enrollment exists or it's a placement test
    if not is_enrolled and not quiz.is_placement_test:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('student_quiz_list')
    
    # Check if the quiz has any questions
    if quiz.get_question_count() == 0:
        messages.error(request, "This quiz has no questions yet.")
        return redirect('student_quiz_list')
    
    # Create a new quiz attempt
    attempt = QuizAttempt.objects.create(
        student=request.user,
        quiz=quiz
    )
    
    # Track that the student has viewed this quiz
    ContentView.objects.get_or_create(
        user=request.user,
        course=quiz.course,
        content_type='quiz',
        content_id=quiz.id
    )
    
    return redirect('take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    """View to take a quiz with enforced time limits and no ability to change previous answers"""
    # Get the attempt, ensuring it belongs to the current user
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    quiz = attempt.quiz
    
    # Check if the attempt is already completed
    if attempt.completed or attempt.status == 'completed':
        messages.info(request, "You have already completed this quiz.")
        return redirect('quiz_results', attempt_id=attempt.id)
    
    # Check if the student already has a completed attempt for this quiz (any attempt, not just this one)
    existing_completed_attempts = QuizAttempt.objects.filter(
        student=request.user, 
        quiz=quiz,
        completed=True
    ).exclude(id=attempt.id).exists()
    
    if existing_completed_attempts:
        messages.warning(request, "You have already completed this quiz. Only one attempt is allowed.")
        return redirect('student_quiz_list')
    
    # Get all questions for this quiz
    questions = get_quiz_questions(quiz)
    
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
    if current_question_num < max_answered_question + 1:
        messages.warning(request, "You cannot go back to previous questions once they are answered.")
        return redirect(f"{reverse('take_quiz', args=[attempt.id])}?question={max_answered_question + 1}")
    
    # Make sure the question number is valid
    if current_question_num > questions.count():
        # All questions have been answered, complete the quiz
        attempt.end_time = timezone.now()
        attempt.completed = True
        attempt.status = 'completed'
        attempt.score = attempt.calculate_score()
        attempt.result = attempt.determine_result()
        attempt.save()
        
        return redirect('quiz_results', attempt_id=attempt.id)
    
    # Get the current question
    current_question = questions[current_question_num - 1]
    
    # Check if this question has already been answered
    existing_answer = QuizAnswer.objects.filter(
        quiz_attempt=attempt,
        question=current_question
    ).first()
    
    if existing_answer:
        # Redirect to the next unanswered question
        return redirect(f"{reverse('take_quiz', args=[attempt.id])}?question={current_question_num + 1}")
    
    # Get the start time for this question
    # We'll store this in the session to track per-question time
    session_key = f'question_start_time_{attempt.id}_{current_question.id}'
    if session_key not in request.session:
        request.session[session_key] = timezone.now().timestamp()
    
    # Process form submission
    if request.method == 'POST':
        # Calculate time taken on this question
        start_time = request.session.get(session_key, timezone.now().timestamp())
        time_taken = int(timezone.now().timestamp() - start_time)
        
        # Clear the session key
        if session_key in request.session:
            del request.session[session_key]
        
        # Initialize variables
        is_correct = False
        points_earned = 0
        
        # Process the answer based on question type
        if current_question.question_type == 'multiple_choice':
            # Get the selected choice
            selected_choice_id = request.POST.get('choice')
            
            if selected_choice_id:
                selected_choice = Choice.objects.get(id=selected_choice_id)
                
                # Check if correct
                if selected_choice.is_correct:
                    is_correct = True
                    points_earned = current_question.points
                
                # Create the answer
                answer = QuizAnswer.objects.create(
                    quiz_attempt=attempt,
                    question=current_question,
                    selected_choice=selected_choice,
                    is_correct=is_correct,
                    points_earned=points_earned,
                    time_taken=time_taken
                )
        
        # Handle other question types...
        # [rest of the answer processing code]
        
        # Redirect to the next question
        next_question = current_question_num + 1
        
        if next_question <= questions.count():
            return redirect(f"{reverse('take_quiz', args=[attempt.id])}?question={next_question}")
        else:
            # Complete the quiz if this was the last question
            return redirect(f"{reverse('take_quiz', args=[attempt.id])}?question={next_question}")
    
    # Prepare the context for the template
    choices = None
    if current_question.question_type in ['multiple_choice', 'true_false', 'dropdown', 'multi_select']:
        choices = current_question.choices.all()
    
    # Calculate progress
    progress_percentage = int((current_question_num / questions.count()) * 100)
    
    # Use the question-specific time limit instead of the quiz's overall time limit
    remaining_time = current_question.time_limit  # This is in seconds already
    
    # If we've already started this question, calculate the remaining time
    if session_key in request.session:
        elapsed_time = int(timezone.now().timestamp() - request.session[session_key])
        remaining_time = max(0, current_question.time_limit - elapsed_time)
        
        # If time is up, auto-submit with no answer
        if remaining_time <= 0:
            # Create a blank answer
            QuizAnswer.objects.create(
                quiz_attempt=attempt,
                question=current_question,
                is_correct=False,
                points_earned=0,
                time_taken=current_question.time_limit
            )
            
            # Clear the session key
            del request.session[session_key]
            
            # Show message and redirect to next question
            messages.warning(request, "Time's up for this question! Moving to the next question.")
            next_question = current_question_num + 1
            
            if next_question <= questions.count():
                return redirect(f"{reverse('take_quiz', args=[attempt.id])}?question={next_question}")
            else:
                # Complete the quiz if this was the last question
                attempt.end_time = timezone.now()
                attempt.completed = True
                attempt.status = 'completed'
                attempt.score = attempt.calculate_score()
                attempt.result = attempt.determine_result()
                attempt.save()
                
                return redirect('quiz_results', attempt_id=attempt.id)
    
    return render(request, 'quizzes/take_quiz.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question': current_question,
        'question_number': current_question_num,
        'total_questions': questions.count(),
        'progress_percentage': progress_percentage,
        'choices': choices,
        'remaining_time': remaining_time
    })

@login_required
def quiz_results(request, attempt_id):
    """View to show quiz results after completion"""
    logger.debug(f"Accessing quiz_results for attempt_id: {attempt_id}")
    
    try:
        # Check if the user is a teacher or admin
        is_teacher_admin = request.user.user_type == 'teacher' or request.user.is_staff or request.user.is_superuser
        
        if is_teacher_admin:
            # Teachers and admins can view any attempt
            attempt = get_object_or_404(QuizAttempt, id=attempt_id)
            
            # Check if teacher is assigned to the student who made this attempt
            if request.user.user_type == 'teacher' and not request.user.is_staff:
                student_ids = StudentProfile.objects.filter(
                    assigned_teacher=request.user
                ).values_list('user_id', flat=True)
                
                if attempt.student.id not in student_ids:
                    messages.error(request, "You don't have permission to view this student's quiz results.")
                    return redirect('quiz_list')
        else:
            # Regular students can only view their own attempts
            attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
        
        if not attempt:
            messages.error(request, "Quiz attempt not found.")
            return redirect('student_quiz_list')
            
        logger.debug(f"Found attempt for quiz: {attempt.quiz.title}")
        quiz = attempt.quiz
        
        # If quiz is not completed yet, redirect to continue
        is_completed = attempt.completed or attempt.status == 'completed'
        if not is_completed and request.user == attempt.student:
            logger.debug("Attempt not completed, redirecting to take_quiz")
            return redirect('take_quiz', attempt_id=attempt.id)
        
        # Ensure both status and completed flags are set correctly
        if is_completed and (attempt.status != 'completed' or not attempt.completed):
            attempt.status = 'completed'
            attempt.completed = True
            attempt.save()
            logger.debug("Updated attempt status to completed")
        
        # Get all answers for this attempt
        answers = attempt.get_answers()
        logger.debug(f"Found {answers.count()} answers for attempt")
        
        # Calculate statistics for the results page
        total_questions = answers.count()
        correct_answers = answers.filter(is_correct=True).count()
        
        # Calculate points
        points_earned = answers.aggregate(total=Sum('points_earned'))['total'] or 0
        total_possible = quiz.get_total_points()
        
        if total_questions > 0:
            accuracy_percentage = int((correct_answers / total_questions) * 100)
        else:
            accuracy_percentage = 0
        
        # For placement tests, show the detailed score breakdown
        beginner_percentage = 0
        intermediate_percentage = 0
        advanced_percentage = 0
        
        if quiz.is_placement_test:
            try:
                # Calculate percentages for each level
                # This is a simplistic calculation and might need to be adjusted
                # based on your specific requirements
                if accuracy_percentage < 40:
                    beginner_percentage = 100
                elif accuracy_percentage < 75:
                    beginner_percentage = 100
                    intermediate_percentage = accuracy_percentage
                else:
                    beginner_percentage = 100
                    intermediate_percentage = 100
                    advanced_percentage = (accuracy_percentage - 75) * 4  # Scale to 100
                    
                # Update the student's proficiency level in their profile
                if is_completed and request.user == attempt.student:
                    student_profile = StudentProfile.objects.get(user=request.user)
                    student_profile.proficiency_level = attempt.result  # The result is already 'beginner', 'intermediate', or 'advanced'
                    student_profile.save()
                    logger.debug(f"Updated student proficiency level to: {attempt.result}")
            except Exception as e:
                logger.error(f"Error calculating level percentages or updating profile: {str(e)}")
        
        return render(request, 'quizzes/quiz_results.html', {
            'attempt': attempt,
            'quiz': quiz,
            'answers': answers,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'accuracy_percentage': accuracy_percentage,
            'beginner_percentage': beginner_percentage,
            'intermediate_percentage': intermediate_percentage,
            'advanced_percentage': advanced_percentage,
            'points_earned': points_earned,
            'total_possible': total_possible,
            'is_placement_test': quiz.is_placement_test,
            'is_teacher_view': is_teacher_admin
        })
    except Exception as e:
        logger.error(f"Error in quiz_results: {str(e)}", exc_info=True)
        messages.error(request, f"There was an error loading your quiz results: {str(e)}")
        # Try to at least show a basic result page without the answers
        try:
            if 'attempt' in locals() and attempt:
                return render(request, 'quizzes/quiz_results.html', {
                    'attempt': attempt,
                    'quiz': getattr(attempt, 'quiz', None),
                    'answers': [],
                    'total_questions': 0,
                    'correct_answers': 0,
                    'accuracy_percentage': 0,
                    'points_earned': 0,
                    'total_possible': 0,
                    'is_placement_test': getattr(attempt, 'quiz', None) and getattr(attempt.quiz, 'is_placement_test', False),
                    'error_message': f"Could not load all quiz data: {str(e)}",
                    'is_teacher_view': is_teacher_admin
                })
        except Exception as inner_e:
            logger.error(f"Fallback error in quiz_results: {str(inner_e)}", exc_info=True)
            
        if is_teacher_admin:
            return redirect('quiz_list')
        else:
            return redirect('student_dashboard')

@login_required
def quiz_review(request, attempt_id):
    """View to review a completed quiz with answers"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    quiz = attempt.quiz
    
    # Only allow reviewing completed quizzes
    is_completed = attempt.completed or attempt.status == 'completed'
    if not is_completed:
        messages.error(request, "You can only review completed quizzes.")
        return redirect('student_quiz_list')
    
    # Get all answers for this attempt
    answers = attempt.get_answers().select_related(
        'question', 'selected_choice', 'quiz_question', 'file_answer', 'voice_answer'
    ).prefetch_related('selected_choices')
    
    # Get all questions for this quiz
    questions = get_quiz_questions(quiz)
    
    # Create a dictionary of answers keyed by question id
    answer_dict = {}
    for answer in answers:
        question_id = answer.question_id if answer.question_id else (
            answer.quiz_question.question_id if answer.quiz_question else None
        )
        if question_id:
            answer_dict[question_id] = answer
    
    # Build a list of questions with their answers directly attached
    question_answers = []
    for question in questions:
        question_answers.append({
            'question': question,
            'answer': answer_dict.get(question.id)
        })
    
    return render(request, 'quizzes/quiz_review.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question_answers': question_answers
    })

# AJAX Endpoints
@login_required
@user_passes_test(is_teacher_or_admin)
def update_question_order(request):
    """AJAX endpoint to update question order"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question_ids = data.get('question_ids', [])
            
            with transaction.atomic():
                for index, question_id in enumerate(question_ids):
                    question = Question.objects.get(id=question_id)
                    question.order = index
                    question.save(update_fields=['order'])
                    
                    # Update QuizQuestion order if it exists
                    quiz_question = QuizQuestion.objects.filter(question_id=question_id).first()
                    if quiz_question:
                        quiz_question.order = index
                        quiz_question.save(update_fields=['order'])
                        
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error updating question order: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def update_timer(request, attempt_id):
    """AJAX endpoint to update timer for a quiz attempt"""
    if request.method == 'POST':
        try:
            # Get the attempt using both field patterns
            attempt = get_quiz_attempt(attempt_id, request.user)
            if not attempt:
                return JsonResponse({'success': False, 'error': 'Quiz attempt not found'})
                
            # Only update if not completed
            is_completed = attempt.completed or attempt.status == 'completed'
            if is_completed:
                return JsonResponse({'success': False, 'error': 'Quiz already completed'})
                
            # Check for time limit
            if attempt.quiz.time_limit:
                elapsed_time = timezone.now() - attempt.start_time
                total_seconds = attempt.quiz.time_limit * 60  # Convert minutes to seconds
                remaining_seconds = total_seconds - elapsed_time.total_seconds()
                
                if remaining_seconds <= 0:
                    # Time's up
                    attempt.status = 'timed_out'
                    attempt.completed = True
                    attempt.end_time = timezone.now()
                    attempt.save()
                    
                    return JsonResponse({
                        'success': True, 
                        'timed_out': True,
                        'redirect_url': reverse('quiz_results', args=[attempt.id])
                    })
                
                return JsonResponse({
                    'success': True,
                    'remaining_seconds': int(remaining_seconds)
                })
            
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error updating timer: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def get_timer(request, attempt_id):
    """AJAX endpoint to get timer for a quiz attempt"""
    if request.method == 'GET':
        try:
            # Get the attempt using both field patterns
            attempt = get_quiz_attempt(attempt_id, request.user)
            if not attempt:
                return JsonResponse({'success': False, 'error': 'Quiz attempt not found'})
                
            # Only update if not completed
            is_completed = attempt.completed or attempt.status == 'completed'
            if is_completed:
                return JsonResponse({'success': False, 'error': 'Quiz already completed'})
                
            # Check for time limit
            if attempt.quiz.time_limit:
                elapsed_time = timezone.now() - attempt.start_time
                total_seconds = attempt.quiz.time_limit * 60  # Convert minutes to seconds
                remaining_seconds = total_seconds - elapsed_time.total_seconds()
                
                if remaining_seconds <= 0:
                    # Time's up
                    attempt.status = 'timed_out'
                    attempt.completed = True
                    attempt.end_time = timezone.now()
                    attempt.save()
                    
                    return JsonResponse({
                        'success': True, 
                        'timed_out': True,
                        'redirect_url': reverse('quiz_results', args=[attempt.id])
                    })
                
                return JsonResponse({
                    'success': True,
                    'remaining_seconds': int(remaining_seconds)
                })
            
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Error getting timer: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})