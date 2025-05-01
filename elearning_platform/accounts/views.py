from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from courses.models import Course, CourseProgress
from events.forms import EventForm
from events.models import TimeOption

from .models import User, StudentProfile, PaymentProof
from .forms import (
    UserRegisterForm, 
    OrganizationForm, 
    CustomAuthenticationForm, 
    PaymentProofForm,
    TeacherAssignmentForm,
    TeacherCreateForm
)

def is_admin(user):
    return user.is_staff or user.is_superuser

def is_teacher(user):
    return user.user_type == 'teacher'

def signup_view(request):
    if request.method == 'POST':
        user_form = UserRegisterForm(request.POST)
        org_form = OrganizationForm(request.POST)
        
        if user_form.is_valid():
            user = user_form.save(commit=False)
            
            # Handle organization information if checked
            if user_form.cleaned_data.get('is_organization'):
                if org_form.is_valid():
                    user.is_organization = True
                    user.company_name = org_form.cleaned_data.get('company_name')
                    user.contact_person = org_form.cleaned_data.get('contact_person')
                    user.phone_number = org_form.cleaned_data.get('phone_number')
                    user.number_of_trainees = org_form.cleaned_data.get('number_of_trainees')
                    messages.success(request, 'Organization registration submitted. Our team will contact you shortly.')
                else:
                    return render(request, 'accounts/signup.html', {
                        'user_form': user_form,
                        'org_form': org_form
                    })
            
            user.save()
            
            # Create student profile for non-organization users
            if not user.is_organization:
                StudentProfile.objects.create(user=user)
                login(request, user)
                return redirect('student_dashboard')
            else:
                return redirect('login')
    else:
        user_form = UserRegisterForm()
        org_form = OrganizationForm()
    
    return render(request, 'accounts/signup.html', {
        'user_form': user_form,
        'org_form': org_form
    })

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Your account is deactivated or has expired.')
                    return redirect('login')
                
                login(request, user)
                
                # Redirect based on user type
                if user.is_staff or user.is_superuser:
                    return redirect('admin_dashboard')
                elif user.user_type == 'teacher':
                    return redirect('teacher_dashboard')
                else:
                    return redirect('student_dashboard')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def student_dashboard(request):
    if not request.user.is_student():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    student_profile = StudentProfile.objects.get(user=request.user)
    payment_proofs = PaymentProof.objects.filter(user=request.user)
    
    # Add course progress data
    for payment in payment_proofs:
        if payment.status == 'approved':
            try:
                # Try to get the associated course progress
                progress = CourseProgress.objects.filter(
                    user=request.user,
                    course=payment.course
                ).first()
                
                payment.progress = progress
            except:
                payment.progress = None
    
    return render(request, 'accounts/student_dashboard.html', {
        'student_profile': student_profile,
        'payment_proofs': payment_proofs
    })

@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    """
    Teacher dashboard view with data for confirmed timesheets and course materials
    """
    import json
    from django.utils import timezone
    from django.db.models import Q
    from events.models import Event, Timesheet
    from quizzes.models import Quiz, QuizAttempt, QuizAnswer, Question
    from courses.models import CourseMaterial, Course, Assignment, AssignmentSubmission
    
    # Initialize variables
    assigned_students = []
    events = []
    recent_quizzes = []
    recent_attempts = []
    confirmed_timesheets = []
    course_materials = []
    teacher_courses = []
    recent_submissions = []
    assignments = []
    error_message = None
    debug_info = {}
    
    try:
        # Get assigned students
        assigned_students = StudentProfile.objects.filter(assigned_teacher=request.user).select_related('user')
        debug_info['assigned_student_count'] = assigned_students.count()
        
        # Get confirmed timesheets
        confirmed_timesheets = Timesheet.objects.filter(
            teacher=request.user,
            status='confirmed'
        ).select_related('student').prefetch_related('time_options')
        debug_info['confirmed_timesheet_count'] = confirmed_timesheets.count()
        
        # Get upcoming events
        today = timezone.now()
        events = Event.objects.filter(
            teacher=request.user,
            end_datetime__gte=today
        ).order_by('start_datetime')[:5]
        debug_info['upcoming_event_count'] = events.count()
        
        # Get student IDs
        student_ids = list(assigned_students.values_list('user_id', flat=True))
        debug_info['student_ids'] = student_ids
        
        courses = Course.objects.none()
        course_ids = set()
        
        # Only process data if there are assigned students
        if student_ids:
            # Get courses with assigned students
            for student_id in student_ids:
                # Get approved payments for each student
                student_payments = PaymentProof.objects.filter(
                    user_id=student_id, 
                    status='approved'
                )
                # Add course IDs to the set
                student_course_ids = list(student_payments.values_list('course_id', flat=True))
                course_ids.update(student_course_ids)
                debug_info[f'student_{student_id}_courses'] = student_course_ids
            
            # Get all relevant courses
            courses = Course.objects.filter(id__in=course_ids)
            debug_info['course_ids'] = list(course_ids)
            debug_info['course_count'] = courses.count()
            
            # Get teacher's courses for the course materials section
            teacher_courses = courses
            
            # Get course materials for courses taught by this teacher
            course_materials = CourseMaterial.objects.filter(
                course__in=courses
            ).select_related('course').order_by('-id')[:5]
            debug_info['course_materials_count'] = course_materials.count()
            
            # Get assignments for these courses
            assignments = Assignment.objects.filter(
                course__in=courses
            ).order_by('-created_at')[:5]
            
            # Get submission counts for each assignment
            for assignment in assignments:
                assignment.submission_count = assignment.submissions.count()
                assignment.ungraded_count = assignment.submissions.filter(status='submitted').count()
            
            # Get recent quiz information
            if courses.exists():
                recent_quizzes = Quiz.objects.filter(
                    course__in=courses,
                    is_active=True
                ).select_related('course').order_by('-created_at')[:5]
                debug_info['recent_quiz_count'] = recent_quizzes.count()
            
            # Get recent quiz attempts
            recent_attempts = QuizAttempt.objects.filter(
                user_id__in=student_ids,
                status__in=['completed', 'timed_out']
            ).select_related('user', 'quiz').order_by('-end_time')[:10]
            debug_info['recent_attempt_count'] = recent_attempts.count()
            
            # Add pending grading flag to each attempt
            for attempt in recent_attempts:
                # Check if this attempt has any answers that need manual grading
                pending_grading = QuizAnswer.objects.filter(
                    attempt=attempt
                ).filter(
                    Q(text_answer__isnull=False) | 
                    Q(file_answer__isnull=False) | 
                    Q(voice_recording__isnull=False)
                ).exists()
                attempt.has_pending_grading = pending_grading
            
            # Get recent assignment submissions
            recent_submissions = AssignmentSubmission.objects.filter(
                assignment__course__in=courses,
                student_id__in=student_ids
            ).select_related('student', 'assignment').order_by('-submitted_at')[:5]
    
        # Calculate quiz and question statistics
        quiz_stats, question_stats = calculate_quiz_stats(student_ids, courses)
        debug_info['quiz_stats'] = quiz_stats
        debug_info['question_stats'] = question_stats
        
    except Exception as e:
        import traceback
        error_message = f"An error occurred while loading the dashboard: {str(e)}"
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
    
    # Prepare context with all data
    context = {
        'assigned_students': assigned_students,
        'confirmed_timesheets': confirmed_timesheets,
        'events': events,
        'recent_quizzes': recent_quizzes,
        'recent_attempts': recent_attempts,
        'question_stats': question_stats if 'question_stats' in locals() else {'total': 0, 'multiple_choice': 0, 'other': 0},
        'quiz_stats': quiz_stats if 'quiz_stats' in locals() else {'total_quizzes': 0, 'total_attempts': 0, 'avg_score': 0, 'pass_rate': 0},
        'error_message': error_message,
        'debug_info': json.dumps(debug_info, indent=2) if request.user.is_staff else None,
        'course_materials': course_materials,
        'teacher_courses': teacher_courses,
        'recent_submissions': recent_submissions,
        'assignments': assignments
    }
    
    return render(request, 'accounts/teacher_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    pending_payments = PaymentProof.objects.filter(status='pending')
    students = User.objects.filter(user_type='student')
    teachers = User.objects.filter(user_type='teacher')
    organizations = User.objects.filter(is_organization=True)
    
    return render(request, 'accounts/admin_dashboard.html', {
        'pending_payments': pending_payments,
        'students': students,
        'teachers': teachers,
        'organizations': organizations
    })

@login_required
@user_passes_test(is_admin)
def payment_approval(request, payment_id):
    payment = get_object_or_404(PaymentProof, id=payment_id)
    action = request.POST.get('action')
    
    if action == 'approve':
        payment.status = 'approved'
        payment.processed_at = timezone.now()
        payment.save()
        
        # Activate the user's account for the course
        messages.success(request, f'Payment for {payment.user.username} has been approved')
    
    elif action == 'reject':
        payment.status = 'rejected'
        payment.processed_at = timezone.now()
        payment.save()
        messages.info(request, f'Payment for {payment.user.username} has been rejected')
    
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def assign_teacher(request, student_id):
    student = get_object_or_404(User, id=student_id, user_type='student')
    student_profile = get_object_or_404(StudentProfile, user=student)
    
    if request.method == 'POST':
        form = TeacherAssignmentForm(request.POST, instance=student_profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Teacher assigned to {student.username} successfully')
            return redirect('admin_dashboard')
    else:
        form = TeacherAssignmentForm(instance=student_profile)
    
    return render(request, 'accounts/assign_teacher.html', {
        'form': form,
        'student': student
    })

@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if user.is_active:
        user.is_active = False
        status_msg = 'deactivated'
    else:
        user.is_active = True
        status_msg = 'activated'
    
    user.save()
    messages.success(request, f'{user.username}\'s account has been {status_msg}')
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def create_teacher(request):
    if request.method == 'POST':
        form = TeacherCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Teacher account created successfully')
            return redirect('admin_dashboard')
    else:
        form = TeacherCreateForm()
    
    return render(request, 'accounts/create_teacher.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def set_student_dates(request, student_id):
    student = get_object_or_404(User, id=student_id, user_type='student')
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if start_date and end_date:
            student.start_date = start_date
            student.end_date = end_date
            student.save()
            messages.success(request, f'Start and end dates set for {student.username}')
            return redirect('admin_dashboard')
    
    return render(request, 'accounts/set_student_dates.html', {'student': student})

def calculate_quiz_stats(student_ids, courses):
    """
    Helper function to calculate quiz statistics for the teacher dashboard
    """
    from django.db.models import Avg, Count, Q
    from quizzes.models import Quiz, QuizAttempt, Question
    
    # Initialize stats dictionaries
    quiz_stats = {
        'total_quizzes': 0,
        'total_attempts': 0,
        'avg_score': 0,
        'pass_rate': 0
    }
    
    question_stats = {
        'total': 0,
        'multiple_choice': 0,
        'other': 0
    }
    
    # Calculate quiz stats
    if courses.exists():
        quiz_stats['total_quizzes'] = Quiz.objects.filter(course__in=courses).count()
        
        attempts = QuizAttempt.objects.filter(
            user_id__in=student_ids,
            status__in=['completed', 'timed_out']
        )
        
        quiz_stats['total_attempts'] = attempts.count()
        
        if attempts.exists():
            avg_score_result = attempts.aggregate(avg=Avg('score'))
            quiz_stats['avg_score'] = round(avg_score_result['avg'] or 0, 1)
            
            # Calculate pass rate
            passed_attempts = sum(1 for attempt in attempts if attempt.score >= attempt.quiz.passing_score)
            quiz_stats['pass_rate'] = round((passed_attempts / attempts.count() * 100), 1) if attempts.count() > 0 else 0
    
    # Calculate question stats
    questions = Question.objects.filter(course__in=courses)
    if questions.exists():
        question_stats['total'] = questions.count()
        question_stats['multiple_choice'] = questions.filter(
            question_type__in=['multiple_choice', 'true_false', 'dropdown']
        ).count()
        question_stats['other'] = question_stats['total'] - question_stats['multiple_choice']
    
    return quiz_stats, question_stats

