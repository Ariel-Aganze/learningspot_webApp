from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from courses.models import Assignment, Course, CourseMaterial, CourseProgress
from events.forms import EventForm
from events.models import TimeOption
 
from .models import CoursePeriod, Organization, User, StudentProfile, PaymentProof
from .forms import (
    CoursePeriodForm,
    PasswordChangeForm,
    StudentCreationForm,
    StudentProfileUpdateForm,
    TeacherProfileUpdateForm,
    UserRegisterForm, 
    OrganizationForm, 
    CustomAuthenticationForm, 
    PaymentProofForm,
    TeacherAssignmentForm,
    TeacherCreateForm
)
from django.db.models import Max

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from .models import User, StudentProfile, Organization, CourseApproval
from datetime import datetime  

from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator
from pathlib import Path
import mimetypes
from django.utils import timezone
from datetime import datetime



def is_admin(user):
    return user.is_staff or user.is_superuser

def is_teacher(user):
    return user.user_type == 'teacher'

def signup_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create student profile for all users
            StudentProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Your account has been created successfully!')
            return redirect('student_dashboard')
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

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
    
    # Get course periods for this student
    course_periods = CoursePeriod.objects.filter(student=request.user)
    
    # Create a dictionary to map courses to their periods
    course_period_dict = {period.course_id: period for period in course_periods}
    
    # Get courses ending soon (within 3 days)
    ending_soon_periods = [period for period in course_periods if period.is_ending_soon()]
    
    # Add course progress and period data to payment proofs
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
            
            # Add course period if it exists
            payment.course_period = course_period_dict.get(payment.course.id)
    
    # Check for pending placement tests
    has_pending_placement_test = False
    for payment in payment_proofs:
        if payment.status == 'approved':
            # Only consider courses that are within their access period or don't have a period set
            course_period = course_period_dict.get(payment.course.id)
            if not course_period or (course_period and course_period.is_active()):
                # Check if there's a placement test for this course
                has_placement_test = payment.course.quizzes.filter(
                    is_placement_test=True,
                    is_active=True
                ).exists()
                
                if has_placement_test and not student_profile.proficiency_level:
                    has_pending_placement_test = True
                    break
    
    context = {
        'student_profile': student_profile,
        'payment_proofs': payment_proofs,
        'has_pending_placement_test': has_pending_placement_test,
        'course_periods': course_periods,
        'ending_soon_periods': ending_soon_periods
    }
    
    return render(request, 'accounts/student_dashboard.html', context)

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
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from accounts.models import Organization  # Add this import

    # Get all data with proper ordering
    pending_payments = PaymentProof.objects.filter(status='pending').order_by('-submitted_at')
    students = User.objects.filter(user_type='student').order_by('-date_joined')
    teachers = User.objects.filter(user_type='teacher').order_by('-date_joined')
    
    # Updated to use Organization model
    organizations = Organization.objects.all().order_by('-created_at')
    
    # Get assignments data with submission counts
    assignments = Assignment.objects.all().order_by('-created_at')
    for assignment in assignments:
        assignment.submission_count = assignment.submissions.count()
        assignment.ungraded_count = assignment.submissions.filter(status='submitted').count()
    
    # Get materials data
    materials = CourseMaterial.objects.all().order_by('course__title', 'order')
    
    # Pagination - 5 items per page for each tab
    paginator_payments = Paginator(pending_payments, 5)
    paginator_students = Paginator(students, 5)
    paginator_teachers = Paginator(teachers, 5)
    paginator_organizations = Paginator(organizations, 5)
    paginator_assignments = Paginator(assignments, 5)
    paginator_materials = Paginator(materials, 5)
    
    # Get page numbers from request with correct parameter names
    page_payments = request.GET.get('pending_page', 1)
    page_students = request.GET.get('students_page', 1)
    page_teachers = request.GET.get('teachers_page', 1)
    page_organizations = request.GET.get('organizations_page', 1)
    page_assignments = request.GET.get('assignments_page', 1)
    page_materials = request.GET.get('materials_page', 1)
    
    # Get the paginated data with error handling
    def get_paginated_page(paginator, page_num):
        try:
            return paginator.page(page_num)
        except PageNotAnInteger:
            return paginator.page(1)
        except EmptyPage:
            return paginator.page(paginator.num_pages)
    
    pending_payments_page = get_paginated_page(paginator_payments, page_payments)
    students_page = get_paginated_page(paginator_students, page_students)
    teachers_page = get_paginated_page(paginator_teachers, page_teachers)
    organizations_page = get_paginated_page(paginator_organizations, page_organizations)
    assignments_page = get_paginated_page(paginator_assignments, page_assignments)
    materials_page = get_paginated_page(paginator_materials, page_materials)
    
    # Context with paginated data
    context = {
        # Paginated versions
        'pending_payments': pending_payments_page,
        'students': students_page,
        'teachers': teachers_page,
        'organizations': organizations_page,
        'assignments': assignments_page,
        'materials': materials_page,
        'now': timezone.now(),
    }
    
    return render(request, 'accounts/admin_dashboard.html', context)

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

@login_required
@user_passes_test(is_admin)
def assign_student_id(request, student_id):
    """View for admin to assign a unique 5-digit Student ID to a student"""
    student = get_object_or_404(User, id=student_id, user_type='student')
    
    # Check if student already has an ID
    if student.student_id:
        messages.info(request, f"Student already has ID: {student.student_id}")
        return redirect('admin_dashboard')
    
    # Find the highest existing student ID and increment by 1, starting from "00000"
    max_id = User.objects.filter(student_id__isnull=False).exclude(student_id='').aggregate(
        Max('student_id')
    )['student_id__max']
    
    if max_id:
        # Convert the highest ID to integer and increment
        try:
            next_id = int(max_id) + 1
        except ValueError:
            # If conversion fails, start from 0
            next_id = 0
    else:
        # If no IDs exist yet, start from 0
        next_id = 0
    
    # Format as 5-digit string with leading zeros
    new_id = f"{next_id:05d}"
    
    # Assign the new ID to the student
    student.student_id = new_id
    student.save()
    
    messages.success(request, f"Student ID {new_id} assigned to {student.get_full_name() or student.username} successfully.")
    return redirect('admin_dashboard')

@login_required
def update_profile(request):
    """View for students to update their profile information and password"""
    # Check if user is a student
    if not request.user.user_type == 'student':
        messages.error(request, "Only students can access this page.")
        return redirect('home')
    
    # Handle profile update form
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = StudentProfileUpdateForm(request.POST, instance=request.user)
            password_form = PasswordChangeForm(user=request.user)
            
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile has been updated successfully!")
                return redirect('update_profile')
                
        # Handle password change form
        elif 'change_password' in request.POST:
            profile_form = StudentProfileUpdateForm(instance=request.user)
            password_form = PasswordChangeForm(request.user, request.POST)
            
            if password_form.is_valid():
                password_form.save()
                # Re-authenticate the user with new password
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)  # Keep the user logged in
                messages.success(request, "Your password has been changed successfully!")
                return redirect('update_profile')
    else:
        profile_form = StudentProfileUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)
    
    return render(request, 'accounts/update_profile.html', {
        'profile_form': profile_form,
        'password_form': password_form
    })

@login_required
@user_passes_test(is_teacher)
def teacher_update_profile(request):
    """View for teachers to update their profile information and password"""
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = TeacherProfileUpdateForm(request.POST, instance=request.user)
            password_form = PasswordChangeForm(user=request.user)
            
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile has been updated successfully!")
                return redirect('teacher_update_profile')
                
        # Handle password change form
        elif 'change_password' in request.POST:
            profile_form = TeacherProfileUpdateForm(instance=request.user)
            password_form = PasswordChangeForm(request.user, request.POST)
            
            if password_form.is_valid():
                password_form.save()
                # Re-authenticate the user with new password
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)  # Keep the user logged in
                messages.success(request, "Your password has been changed successfully!")
                return redirect('teacher_update_profile')
    else:
        profile_form = TeacherProfileUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)
    
    return render(request, 'accounts/teacher_update_profile.html', {
        'profile_form': profile_form,
        'password_form': password_form
    })

@login_required
@user_passes_test(is_admin)
def set_course_periods(request, student_id):
    """View for admin to set course periods for a student"""
    student = get_object_or_404(User, id=student_id, user_type='student')
    
    # Get existing course periods for this student
    existing_periods = CoursePeriod.objects.filter(student=student)
    
    if request.method == 'POST':
        # Handle form submission for a specific course period
        if 'course_period_id' in request.POST:
            # Update an existing course period
            course_period = get_object_or_404(CoursePeriod, 
                id=request.POST.get('course_period_id'), 
                student=student
            )
            form = CoursePeriodForm(student, request.POST, instance=course_period)
            
            if form.is_valid():
                form.save()
                messages.success(request, f"Course period for {course_period.course.title} updated successfully.")
                return redirect('set_course_periods', student_id=student.id)
        
        # Handle form submission for a new course period
        elif 'add_new_period' in request.POST:
            form = CoursePeriodForm(student, request.POST)
            
            if form.is_valid():
                course_period = form.save(commit=False)
                course_period.student = student
                
                # Check if a period already exists for this course and student
                existing = CoursePeriod.objects.filter(
                    student=student,
                    course=course_period.course
                ).first()
                
                if existing:
                    # Update the existing period
                    existing.start_date = course_period.start_date
                    existing.end_date = course_period.end_date
                    existing.save()
                    messages.success(request, f"Course period for {existing.course.title} updated successfully.")
                else:
                    # Save the new period
                    course_period.save()
                    messages.success(request, f"Course period for {course_period.course.title} added successfully.")
                
                return redirect('set_course_periods', student_id=student.id)
        
        # Handle deletion of a course period
        elif 'delete_period' in request.POST:
            period_id = request.POST.get('period_id')
            course_period = get_object_or_404(CoursePeriod, id=period_id, student=student)
            course_title = course_period.course.title
            course_period.delete()
            messages.success(request, f"Course period for {course_title} deleted successfully.")
            return redirect('set_course_periods', student_id=student.id)
    
    # Create a form for adding a new course period
    form = CoursePeriodForm(student)
    
    # Create forms for editing existing course periods
    edit_forms = []
    for period in existing_periods:
        edit_form = CoursePeriodForm(student, instance=period)
        edit_forms.append({
            'period': period,
            'form': edit_form
        })
    
    return render(request, 'accounts/set_course_periods.html', {
        'student': student,
        'form': form,
        'edit_forms': edit_forms,
        'existing_periods': existing_periods
    })

User = get_user_model()


def forgot_password(request):
    """View for initiating the password reset process"""
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build the reset URL
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Prepare email
            subject = 'Reset Your Password'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
                'site_name': settings.SITE_NAME,
            })
            
            # Send email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=message,
            )
            
            messages.success(request, 'Password reset instructions have been sent to your email.')
            return redirect('password_reset_done')
        except User.DoesNotExist:
            # Don't reveal if the email exists for security reasons
            messages.success(request, 'Password reset instructions have been sent to your email if the account exists.')
            return redirect('password_reset_done')
    
    return render(request, 'accounts/forgot_password.html')

def password_reset_done(request):
    """View shown after password reset email is sent"""
    return render(request, 'accounts/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    """View for confirming the reset token and setting new password"""
    try:
        # Decode the user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        # Verify token
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                # Process the form
                password1 = request.POST.get('password1')
                password2 = request.POST.get('password2')
                
                if password1 and password2 and password1 == password2:
                    # Set new password
                    user.set_password(password1)
                    user.save()
                    messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
                    return redirect('login')
                else:
                    messages.error(request, 'Passwords do not match.')
            
            # Show the form
            return render(request, 'accounts/password_reset_confirm.html', {'validlink': True})
        else:
            # Invalid token
            return render(request, 'accounts/password_reset_confirm.html', {'validlink': False})
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        # Invalid user id
        return render(request, 'accounts/password_reset_confirm.html', {'validlink': False})
    
# accounts/views.py

@login_required
@user_passes_test(is_admin)
def create_organization(request):
    """View for admin to create a new organization"""
    if request.method == 'POST':
        form = OrganizationForm(request.POST)
        if form.is_valid():
            organization = form.save()
            messages.success(request, f"Organization '{organization.name}' created successfully.")
            return redirect('admin_dashboard')
    else:
        form = OrganizationForm()
    
    return render(request, 'accounts/organization_form.html', {
        'form': form,
        'title': 'Create Organization'
    })

@login_required
@user_passes_test(is_admin)
def update_organization(request, organization_id):
    """View for admin to update an organization"""
    organization = get_object_or_404(Organization, id=organization_id)
    
    if request.method == 'POST':
        form = OrganizationForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            messages.success(request, f"Organization '{organization.name}' updated successfully.")
            return redirect('admin_dashboard')
    else:
        form = OrganizationForm(instance=organization)
    
    return render(request, 'accounts/organization_form.html', {
        'form': form,
        'organization': organization,
        'title': 'Update Organization'
    })

@login_required
@user_passes_test(is_admin)
def set_organization_period(request, organization_id):
    """View for admin to set/update subscription period for an organization"""
    organization = get_object_or_404(Organization, id=organization_id)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if start_date and end_date:
            # Convert to dates
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if end_date < start_date:
                messages.error(request, "End date cannot be before start date.")
            else:
                organization.start_date = start_date
                organization.end_date = end_date
                organization.save()
                messages.success(request, f"Subscription period for '{organization.name}' set successfully.")
                return redirect('admin_dashboard')
    
    return render(request, 'accounts/set_organization_period.html', {
        'organization': organization
    })

# accounts/views.py

@login_required
@user_passes_test(is_admin)
def create_student(request):
    """View for admin to create a student account"""
    if request.method == 'POST':
        form = StudentCreationForm(request.POST)
        if form.is_valid():
            # Get form data
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            organization = form.cleaned_data.get('organization')
            
            # Create user with student type
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type='student'
            )
            
            # Create student profile and connect to organization if selected
            student_profile, created = StudentProfile.objects.get_or_create(user=user)
            if organization:
                student_profile.organization = organization
                student_profile.save()
                
                # If student is from an organization, exempt from placement test payment
                if organization.is_subscription_active:
                    # Automatically create a placement test approval
                    CourseApproval.objects.create(
                        student=user,
                        is_placement_test_paid=True,
                        approved_by=request.user,
                        approval_date=timezone.now()
                    )
            
            messages.success(request, f"Student account for {user.get_full_name()} created successfully.")
            return redirect('admin_dashboard')
    else:
        form = StudentCreationForm()
    
    return render(request, 'accounts/create_student.html', {
        'form': form,
    })

@login_required
@user_passes_test(is_admin)
def media_management(request):
    """View for admin to manage media files"""
    
    # Get all media files
    media_root = Path(settings.MEDIA_ROOT)
    files_info = []
    total_size = 0
    
    if media_root.exists():
        for file_path in media_root.rglob('*'):
            if file_path.is_file():
                try:
                    file_stat = file_path.stat()
                    file_size = file_stat.st_size
                    total_size += file_size
                    
                    # Get relative path from media root
                    relative_path = file_path.relative_to(media_root)
                    
                    # Get file info
                    file_info = {
                        'name': file_path.name,
                        'path': str(relative_path),
                        'full_path': str(file_path),
                        'size': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2),
                        'modified': datetime.fromtimestamp(file_stat.st_mtime),
                        'type': mimetypes.guess_type(str(file_path))[0] or 'unknown',
                        'folder': str(relative_path.parent) if relative_path.parent != Path('.') else 'root'
                    }
                    files_info.append(file_info)
                except (OSError, PermissionError):
                    continue
    
    # Sort by size (largest first) by default
    sort_by = request.GET.get('sort', 'size')
    if sort_by == 'size':
        files_info.sort(key=lambda x: x['size'], reverse=True)
    elif sort_by == 'name':
        files_info.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'modified':
        files_info.sort(key=lambda x: x['modified'], reverse=True)
    elif sort_by == 'type':
        files_info.sort(key=lambda x: x['type'])
    
    # Filter by file type if requested
    file_type = request.GET.get('type', '')
    if file_type:
        if file_type == 'images':
            files_info = [f for f in files_info if f['type'] and f['type'].startswith('image/')]
        elif file_type == 'documents':
            files_info = [f for f in files_info if f['type'] and (f['type'].startswith('application/') or f['type'] == 'text/plain')]
        elif file_type == 'videos':
            files_info = [f for f in files_info if f['type'] and f['type'].startswith('video/')]
        elif file_type == 'audio':
            files_info = [f for f in files_info if f['type'] and f['type'].startswith('audio/')]
    
    # Pagination
    paginator = Paginator(files_info, 20)  # 20 files per page
    page = request.GET.get('page', 1)
    
    try:
        files = paginator.page(page)
    except:
        files = paginator.page(1)
    
    # Calculate total size in different units
    total_size_mb = round(total_size / (1024 * 1024), 2)
    total_size_gb = round(total_size / (1024 * 1024 * 1024), 2)
    
    # Get file type counts
    type_counts = {}
    for file_info in files_info:
        file_type = file_info['type'].split('/')[0] if file_info['type'] and '/' in file_info['type'] else 'other'
        type_counts[file_type] = type_counts.get(file_type, 0) + 1
    
    context = {
        'files': files,
        'total_files': len(files_info),
        'total_size': total_size,
        'total_size_mb': total_size_mb,
        'total_size_gb': total_size_gb,
        'current_sort': sort_by,
        'current_type': file_type,
        'type_counts': type_counts,
    }
    
    return render(request, 'accounts/media_management.html', context)

@login_required
@user_passes_test(is_admin)
def delete_media_file(request):
    """AJAX view to delete a media file"""
    if request.method == 'POST':
        file_path = request.POST.get('file_path')
        
        if not file_path:
            return JsonResponse({'success': False, 'message': 'No file path provided'})
        
        # Security check - ensure the file is within media root
        media_root = Path(settings.MEDIA_ROOT)
        full_path = media_root / file_path
        
        try:
            # Resolve to absolute path and check if it's within media root
            resolved_path = full_path.resolve()
            if not str(resolved_path).startswith(str(media_root.resolve())):
                return JsonResponse({'success': False, 'message': 'Invalid file path'})
            
            if resolved_path.exists() and resolved_path.is_file():
                file_size = resolved_path.stat().st_size
                resolved_path.unlink()  # Delete the file
                
                # Also try to remove empty parent directories
                parent = resolved_path.parent
                try:
                    if parent != media_root and not any(parent.iterdir()):
                        parent.rmdir()
                except OSError:
                    pass  # Directory not empty or other error
                
                return JsonResponse({
                    'success': True, 
                    'message': f'File deleted successfully',
                    'freed_space': round(file_size / (1024 * 1024), 2)  # MB
                })
            else:
                return JsonResponse({'success': False, 'message': 'File not found'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error deleting file: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
@user_passes_test(is_admin)
def bulk_delete_media(request):
    """AJAX view to delete multiple media files"""
    if request.method == 'POST':
        import json
        
        try:
            data = json.loads(request.body)
            file_paths = data.get('file_paths', [])
        except:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
        
        if not file_paths:
            return JsonResponse({'success': False, 'message': 'No files selected'})
        
        media_root = Path(settings.MEDIA_ROOT)
        deleted_count = 0
        total_freed_space = 0
        errors = []
        
        for file_path in file_paths:
            try:
                full_path = media_root / file_path
                resolved_path = full_path.resolve()
                
                # Security check
                if not str(resolved_path).startswith(str(media_root.resolve())):
                    errors.append(f"Invalid path: {file_path}")
                    continue
                
                if resolved_path.exists() and resolved_path.is_file():
                    file_size = resolved_path.stat().st_size
                    resolved_path.unlink()
                    deleted_count += 1
                    total_freed_space += file_size
                    
                    # Try to remove empty parent directory
                    parent = resolved_path.parent
                    try:
                        if parent != media_root and not any(parent.iterdir()):
                            parent.rmdir()
                    except OSError:
                        pass
                else:
                    errors.append(f"File not found: {file_path}")
                    
            except Exception as e:
                errors.append(f"Error deleting {file_path}: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'freed_space': round(total_freed_space / (1024 * 1024), 2),  # MB
            'errors': errors
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
@user_passes_test(is_admin)
def cleanup_orphaned_files(request):
    """Remove files that are no longer referenced in the database"""
    if request.method == 'POST':
        from accounts.models import PaymentProof
        from courses.models import CourseMaterial, AssignmentSubmission
        
        # Get all file paths referenced in the database
        referenced_files = set()
        
        # Payment proof images
        for proof in PaymentProof.objects.exclude(proof_image=''):
            if proof.proof_image:
                referenced_files.add(proof.proof_image.name)
        
        # Course material files
        for material in CourseMaterial.objects.exclude(file=''):
            if material.file:
                referenced_files.add(material.file.name)
        
        # Assignment submission files
        for submission in AssignmentSubmission.objects.exclude(submission_file=''):
            if submission.submission_file:
                referenced_files.add(submission.submission_file.name)
        
        # Get all actual files
        media_root = Path(settings.MEDIA_ROOT)
        actual_files = []
        
        if media_root.exists():
            for file_path in media_root.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(media_root)
                    actual_files.append(str(relative_path))
        
        # Find orphaned files
        orphaned_files = []
        for file_path in actual_files:
            if file_path not in referenced_files:
                orphaned_files.append(file_path)
        
        # Delete orphaned files if confirmed
        if request.POST.get('confirm') == 'true':
            deleted_count = 0
            total_freed_space = 0
            
            for file_path in orphaned_files:
                try:
                    full_path = media_root / file_path
                    if full_path.exists():
                        file_size = full_path.stat().st_size
                        full_path.unlink()
                        deleted_count += 1
                        total_freed_space += file_size
                except Exception:
                    continue
            
            return JsonResponse({
                'success': True,
                'deleted_count': deleted_count,
                'freed_space': round(total_freed_space / (1024 * 1024), 2)
            })
        else:
            # Just return the count for confirmation
            total_size = 0
            for file_path in orphaned_files:
                try:
                    full_path = media_root / file_path
                    if full_path.exists():
                        total_size += full_path.stat().st_size
                except Exception:
                    continue
            
            return JsonResponse({
                'success': True,
                'orphaned_count': len(orphaned_files),
                'orphaned_size': round(total_size / (1024 * 1024), 2),
                'preview': orphaned_files[:10]  # Show first 10 files as preview
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})