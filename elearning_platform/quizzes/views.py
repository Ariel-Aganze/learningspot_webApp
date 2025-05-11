from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.forms import formset_factory
from django.db.models import Q
from django.urls import reverse
import random
import logging
from django.db.models import Avg, Count, F, Q

logger = logging.getLogger(__name__)

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

def is_teacher_or_admin(user):
    return user.user_type == 'teacher' or user.is_staff or user.is_superuser

@login_required
@user_passes_test(lambda u: u.user_type == 'teacher')
def teacher_dashboard(request):
    from django.db.models import Avg, Count, F, Q

    # Get assigned students
    assigned_students = StudentProfile.objects.filter(assigned_teacher=request.user)
    
    # Get all courses (since there's no direct teacher-course relationship in your models)
    courses = Course.objects.filter(is_active=True)
    
    # Get recent quizzes across all courses
    recent_quizzes = Quiz.objects.filter(
        course__in=courses,
        is_active=True
    ).select_related('course').order_by('-created_at')[:5]
    
    # Get student IDs assigned to this teacher
    student_ids = list(assigned_students.values_list('user_id', flat=True))
    
    # Only get attempts if there are assigned students
    recent_attempts = []
    if student_ids:
        # Get recent quiz attempts from assigned students
        recent_attempts = QuizAttempt.objects.filter(
            user_id__in=student_ids,
            status__in=['completed', 'timed_out']
        ).select_related('user', 'quiz').order_by('-end_time')[:10]
        
        # Add a flag for each attempt to indicate if it has submissions that need grading
        for attempt in recent_attempts:
            pending_grading = False
            try:
                pending_grading = (
                    QuizAnswer.objects.filter(
                        attempt=attempt,
                        text_answer__isnull=False
                    ).exists() or 
                    QuizAnswer.objects.filter(
                        attempt=attempt,
                        file_answer__isnull=False
                    ).exists() or 
                    QuizAnswer.objects.filter(
                        attempt=attempt,
                        voice_recording__isnull=False
                    ).exists()
                )
            except Exception as e:
                print(f"Error checking pending grading: {e}")
            
            attempt.has_pending_grading = pending_grading
    
    # Question stats - count questions across all courses
    questions = Question.objects.filter(course__in=courses)
    
    question_stats = {
        'total': questions.count(),
        'multiple_choice': questions.filter(question_type='multiple_choice').count(),
        'other': questions.exclude(question_type='multiple_choice').count()
    }
    
    # Quiz stats
    quiz_stats = {
        'total_quizzes': Quiz.objects.filter(course__in=courses).count(),
        'total_attempts': 0,
        'avg_score': 0,
        'pass_rate': 0
    }
    
    # Only calculate stats if there are assigned students
    if student_ids:
        attempts = QuizAttempt.objects.filter(
            user_id__in=student_ids,
            status__in=['completed', 'timed_out']
        )
        
        # Count attempts
        total_attempts = attempts.count()
        quiz_stats['total_attempts'] = total_attempts
        
        # Calculate average score
        if total_attempts > 0:
            avg_score = attempts.aggregate(avg_score=Avg('score'))['avg_score'] or 0
            quiz_stats['avg_score'] = avg_score
            
            # Calculate pass rate
            passed_attempts = 0
            for attempt in attempts:
                if attempt.score >= attempt.quiz.passing_score:
                    passed_attempts += 1
            
            if total_attempts > 0:
                quiz_stats['pass_rate'] = (passed_attempts / total_attempts) * 100
    
    context = {
        'assigned_students': assigned_students,
        'recent_quizzes': recent_quizzes,
        'recent_attempts': recent_attempts,
        'question_stats': question_stats,
        'quiz_stats': quiz_stats,
    }
    
    return render(request, 'accounts/teacher_dashboard.html', context)

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
    
    # Get all the questions for this quiz in order
    quiz_questions = list(quiz.quiz_questions.all().order_by('order').select_related('question'))
    total_questions = len(quiz_questions)
    
    # Get all answered questions
    answered_questions = QuizAnswer.objects.filter(attempt=attempt)
    answered_question_ids = [answer.question_id for answer in answered_questions]
    answered_count = len(answered_question_ids)
    
    # Find the first unanswered question
    current_question = None
    for q in quiz_questions:
        if q.id not in answered_question_ids:
            current_question = q
            break
    
    # Log debugging info
    logger.debug(f"Quiz has {total_questions} questions")
    logger.debug(f"User has answered {answered_count} questions")
    logger.debug(f"Answered question IDs: {answered_question_ids}")
    
    # If all questions are answered, complete the quiz
    if current_question is None:
        attempt.status = 'completed'
        attempt.end_time = timezone.now()
        attempt.calculate_score()
        attempt.determine_level()
        attempt.save()
        
        # Update student profile with the determined level
        student_profile = StudentProfile.objects.get(user=request.user)
        student_profile.proficiency_level = attempt.result
        student_profile.save()
        
        messages.success(request, 'Quiz completed successfully!')
        return redirect('quiz_results', attempt_id=attempt.id)
    
    question_type = current_question.question.question_type
    logger.debug(f"Current question: {current_question.id}, type: {question_type}")
    
    # Check if the question has choices if it's a choice-based question type
    has_valid_choices = True
    if current_question.question.is_multiple_choice_type():
        has_valid_choices = current_question.question.choices.exists()
        if not has_valid_choices:
            logger.error(f"Question {current_question.id} has no choices")
            # Mark as answered incorrectly and move to next question
            QuizAnswer.objects.create(
                attempt=attempt,
                question=current_question,
                is_correct=False,
                time_taken=0
            )
            return redirect('take_quiz', attempt_id=attempt.id)
    
    # Handle form submission
    if request.method == 'POST':
        # Get the submitted question ID and verify it matches the current question
        submitted_question_id = request.POST.get('question_id')
        logger.debug(f"Submitted question ID: {submitted_question_id}, Current question ID: {current_question.id}")
        
        # Make sure we're processing the right question
        if submitted_question_id and int(submitted_question_id) != current_question.id:
            logger.warning(f"Question mismatch: submitted {submitted_question_id}, current {current_question.id}")
            # Force skip to the correct current question
            return redirect('take_quiz', attempt_id=attempt.id)
        
        # Extract time taken
        time_taken = request.POST.get('time_taken', '0')
        try:
            time_taken = int(time_taken)
        except ValueError:
            time_taken = 0
        
        # Create a QuizAnswer object
        answer = QuizAnswer(
            attempt=attempt,
            question=current_question,
            time_taken=time_taken
        )
        
        # Process answer based on question type
        if question_type in ['multiple_choice', 'true_false', 'dropdown', 'star_rating', 'image_choice', 'image_rating', 'likert_scale']:
            selected_choice_id = request.POST.get('selected_choice')
            
            if selected_choice_id:
                try:
                    selected_choice = Choice.objects.get(pk=selected_choice_id, question=current_question.question)
                    answer.selected_choice = selected_choice
                    answer.is_correct = selected_choice.is_correct
                    logger.debug(f"Selected choice: {selected_choice.text}, is_correct: {selected_choice.is_correct}")
                except Choice.DoesNotExist:
                    answer.is_correct = False
            else:
                # No choice selected - mark as incorrect
                answer.is_correct = False
        
        elif question_type == 'multi_select':
            selected_choice_ids = request.POST.getlist('selected_choices')
            
            if selected_choice_ids:
                try:
                    # Store the first choice for database reference
                    first_choice_id = selected_choice_ids[0]
                    first_choice = Choice.objects.get(pk=first_choice_id, question=current_question.question)
                    answer.selected_choice = first_choice
                    
                    # Check if all correct choices are selected and no incorrect ones
                    all_choices = current_question.question.choices.all()
                    correct_choice_ids = {str(c.id) for c in all_choices if c.is_correct}
                    selected_choice_ids_set = set(selected_choice_ids)
                    
                    # Multi-select is correct only if exact match
                    answer.is_correct = (correct_choice_ids == selected_choice_ids_set)
                    logger.debug(f"Multi-select: correct_ids={correct_choice_ids}, selected={selected_choice_ids_set}")
                except (IndexError, Choice.DoesNotExist) as e:
                    logger.error(f"Error processing multi-select: {str(e)}")
                    answer.is_correct = False
            else:
                answer.is_correct = False
        
        # Handle other question types...
        elif question_type == 'matrix':
            # Processing for matrix questions
            matrix_keys = [k for k in request.POST.keys() if k.startswith('matrix_')]
            if matrix_keys:
                # Store one answer for database
                matrix_value = request.POST[matrix_keys[0]]
                option_id, choice_id = matrix_value.split('_')
                try:
                    selected_choice = Choice.objects.get(pk=option_id, question=current_question.question)
                    answer.selected_choice = selected_choice
                    answer.is_correct = selected_choice.is_correct
                except Choice.DoesNotExist:
                    answer.is_correct = False
            else:
                answer.is_correct = False
        
        elif question_type in ['matching']:
            # Process matching questions
            match_keys = [k for k in request.POST.keys() if k.startswith('match_')]
            if match_keys:
                # Check if all matches are correct
                all_correct = True
                for match_key in match_keys:
                    left_id = match_key.split('_')[1]
                    right_id = request.POST[match_key]
                    if right_id:
                        try:
                            left_choice = Choice.objects.get(pk=left_id, question=current_question.question)
                            right_choice = Choice.objects.get(pk=right_id, question=current_question.question)
                            # If match_text doesn't match text, it's incorrect
                            if right_choice.match_text != left_choice.text:
                                all_correct = False
                                break
                        except Choice.DoesNotExist:
                            all_correct = False
                            break
                    else:
                        all_correct = False
                        break
                
                # Store the first match for database reference
                try:
                    first_match_key = match_keys[0]
                    first_right_id = request.POST[first_match_key]
                    if first_right_id:
                        selected_choice = Choice.objects.get(pk=first_right_id, question=current_question.question)
                        answer.selected_choice = selected_choice
                    answer.is_correct = all_correct
                except (IndexError, Choice.DoesNotExist):
                    answer.is_correct = False
            else:
                answer.is_correct = False
        
        elif question_type in ['short_answer', 'long_answer']:
    # Process text answers
            text = request.POST.get('text_answer', '')
            if text.strip():
                try:
            # Check if an answer already exists
                    existing_text_answer = TextAnswer.objects.filter(
                        question=current_question.question,
                        student=request.user
                    ).first()
            
                    if existing_text_answer:
                # Update the existing text answer
                        existing_text_answer.text = text
                        existing_text_answer.save()
                        answer.text_answer = existing_text_answer
                    else:
                # Create a new text answer
                        text_answer = TextAnswer.objects.create(
                            question=current_question.question,
                            student=request.user,
                            text=text
                        )
                        answer.text_answer = text_answer
            
            # Text answers need to be manually graded
                    answer.is_correct = False
                except Exception as e:
                    logger.error(f"Error processing text answer: {str(e)}")
                    answer.is_correct = False
            else:
                answer.is_correct = False
        
        elif question_type in ['file_upload']:
    # Process file uploads
            uploaded_file = request.FILES.get('file_answer')
            if uploaded_file:
                try:
            # Check if an answer already exists
                    existing_file_answer = FileAnswer.objects.filter(
                        question=current_question.question,
                        student=request.user
                    ).first()
            
                    if existing_file_answer:
                # Update the existing file answer
                        existing_file_answer.file = uploaded_file
                        existing_file_answer.file_type = uploaded_file.content_type
                        existing_file_answer.save()
                        answer.file_answer = existing_file_answer
                    else:
                # Create a new file answer
                        file_answer = FileAnswer.objects.create(
                            question=current_question.question,
                            student=request.user,
                            file=uploaded_file,
                            file_type=uploaded_file.content_type
                        )
                        answer.file_answer = file_answer
            
            # File uploads need to be manually graded
                    answer.is_correct = False
                except Exception as e:
                    logger.error(f"Error processing file upload: {str(e)}")
                    answer.is_correct = False
            else:
                answer.is_correct = False
        
        elif question_type == 'voice_record':
    # Process voice recordings from base64 string
            voice_data = request.POST.get('file_answer', '')
            if voice_data and voice_data.startswith('data:audio'):
                try:
            # Extract base64 part
                    format, base64_data = voice_data.split(';base64,')
            # Create a ContentFile from the base64 data
                    from django.core.files.base import ContentFile
                    import base64
            
                    file_data = base64.b64decode(base64_data)
                    file_content = ContentFile(file_data)
            
            # Create a name for the file
                    import uuid
                    file_name = f"voice_{uuid.uuid4()}.mp3"
            
            # Check if a voice recording already exists
                    existing_voice_recording = VoiceRecording.objects.filter(
                        question=current_question.question,
                        student=request.user
                    ).first()
            
                    if existing_voice_recording:
                # Update the existing voice recording
                        existing_voice_recording.audio_file.save(file_name, file_content, save=True)
                        existing_voice_recording.duration = 0  # Reset duration or calculate new one
                        existing_voice_recording.save()
                        answer.voice_recording = existing_voice_recording
                    else:
                # Create a new voice recording
                        voice_recording = VoiceRecording.objects.create(
                            question=current_question.question,
                            student=request.user,
                            duration=0  # We don't know the duration
                        )
                # Save the file to the model
                        voice_recording.audio_file.save(file_name, file_content, save=True)
                        answer.voice_recording = voice_recording
            
            # Voice recordings need to be manually graded
                    answer.is_correct = False
                except Exception as e:
                    logger.error(f"Error processing voice recording: {str(e)}")
                    answer.is_correct = False
            else:
                answer.is_correct = False
        
        # Save the answer
        try:
            answer.save()
            logger.debug(f"Answer saved successfully for question {current_question.id}, correct: {answer.is_correct}")
        except Exception as e:
            logger.error(f"Error saving answer: {str(e)}")
            messages.error(request, "There was an error saving your answer. Please try again.")
            # If we couldn't save the answer, just render the form again
            form = QuizAnswerForm(current_question)
        else:
            # Successfully saved answer, redirect to next question
            return redirect('take_quiz', attempt_id=attempt.id)
    else:
        # GET request - show the question form
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
    
    # Calculate progress percentage
    progress = (answered_count / total_questions * 100) if total_questions > 0 else 0
    
    return render(request, 'quizzes/take_quiz.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question': current_question,
        'form': form,
        'remaining_time': remaining_time,
        'question_time_limit': current_question.question.time_limit,
        'question_type': question_type,
        'has_valid_choices': has_valid_choices,
        'progress': progress,
        'total_questions': total_questions,
        'answered_count': answered_count
    })


@login_required
def quiz_results(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    
    # If quiz is not completed yet, redirect to continue
    if attempt.status == 'in_progress':
        return redirect('take_quiz', attempt_id=attempt.id)
    
    try:
        # Get all answers for this attempt
        answers = attempt.answers.all().select_related(
            'question', 'question__question', 'selected_choice',
            'text_answer', 'file_answer', 'voice_recording'
        )
        
        # Calculate statistics for the results page
        total_questions = answers.count()
        correct_answers = answers.filter(is_correct=True).count()
        accuracy_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Group questions by difficulty
        beginner_questions = answers.filter(question__question__difficulty='beginner').count()
        intermediate_questions = answers.filter(question__question__difficulty='intermediate').count()
        advanced_questions = answers.filter(question__question__difficulty='advanced').count()
        
        beginner_correct = answers.filter(question__question__difficulty='beginner', is_correct=True).count()
        intermediate_correct = answers.filter(question__question__difficulty='intermediate', is_correct=True).count()
        advanced_correct = answers.filter(question__question__difficulty='advanced', is_correct=True).count()
        
        # Calculate percentages safely
        beginner_percentage = (beginner_correct / beginner_questions * 100) if beginner_questions > 0 else 0
        intermediate_percentage = (intermediate_correct / intermediate_questions * 100) if intermediate_questions > 0 else 0
        advanced_percentage = (advanced_correct / advanced_questions * 100) if advanced_questions > 0 else 0
        
        return render(request, 'quizzes/quiz_results.html', {
            'attempt': attempt,
            'answers': answers,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'accuracy_percentage': accuracy_percentage,
            'beginner_percentage': beginner_percentage,
            'intermediate_percentage': intermediate_percentage,
            'advanced_percentage': advanced_percentage
        })
    except Exception as e:
        logger.error(f"Error in quiz_results: {str(e)}")
        messages.error(request, "There was an error loading your quiz results.")
        return redirect('student_dashboard')

@login_required
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
@user_passes_test(is_teacher_or_admin)
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
        try:
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
                    try:
                        student_profile = StudentProfile.objects.get(user=request.user)
                        student_profile.proficiency_level = attempt.result
                        student_profile.save()
                    except StudentProfile.DoesNotExist:
                        pass
                    
                    return JsonResponse({'status': 'timeout', 'redirect': reverse('quiz_results', args=[attempt.id])})
                
                return JsonResponse({'status': 'ok', 'remaining_time': remaining_time})
            else:
                return JsonResponse({'status': 'completed', 'redirect': reverse('quiz_results', args=[attempt.id])})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in quiz_timer_update: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An error occurred'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

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

@login_required
@user_passes_test(lambda u: u.user_type == 'teacher')
def grade_submissions_all(request):
    # Get all the students assigned to this teacher
    student_ids = StudentProfile.objects.filter(assigned_teacher=request.user).values_list('user_id', flat=True)
    
    # Get all quizzes with pending submissions
    quizzes_with_pending = Quiz.objects.filter(
        attempts__user_id__in=student_ids,
        attempts__status__in=['completed', 'timed_out'],
        attempts__answers__text_answer__isnull=False
    ).distinct() | Quiz.objects.filter(
        attempts__user_id__in=student_ids,
        attempts__status__in=['completed', 'timed_out'],
        attempts__answers__file_answer__isnull=False
    ).distinct() | Quiz.objects.filter(
        attempts__user_id__in=student_ids,
        attempts__status__in=['completed', 'timed_out'],
        attempts__answers__voice_recording__isnull=False
    ).distinct()
    
    return render(request, 'quizzes/grade_submissions_all.html', {
        'quizzes': quizzes_with_pending
    })

@login_required
@user_passes_test(lambda u: u.user_type == 'teacher')
def quiz_results_all(request):
    # Get all the students assigned to this teacher
    student_ids = StudentProfile.objects.filter(assigned_teacher=request.user).values_list('user_id', flat=True)
    
    # Get all quiz attempts for these students
    attempts = QuizAttempt.objects.filter(
        user_id__in=student_ids,
        status__in=['completed', 'timed_out']
    ).select_related('user', 'quiz').order_by('-end_time')
    
    return render(request, 'quizzes/quiz_results_all.html', {
        'attempts': attempts
    })