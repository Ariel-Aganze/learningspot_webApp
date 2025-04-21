from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from quizzes.models import Quiz, QuizAttempt

from .models import AssignmentSubmission, Course, CourseLevel, CourseProgress
from .forms import CourseForm, CourseLevelForm
from accounts.models import PaymentProof, StudentProfile
from accounts.forms import PaymentProofForm

def is_admin(user):
    return user.is_staff or user.is_superuser

def course_list(request):
    courses = Course.objects.filter(is_active=True)
    return render(request, 'courses/course_list.html', {'courses': courses})

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    levels = course.levels.all()
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'levels': levels
    })

@login_required
def course_enroll(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Check if the user has already enrolled in this course
    existing_payment = PaymentProof.objects.filter(user=request.user, course=course).first()
    
    if existing_payment:
        if existing_payment.status == 'approved':
            messages.info(request, 'You have already enrolled in this course.')
            return redirect('student_dashboard')
        elif existing_payment.status == 'pending':
            messages.info(request, 'Your payment for this course is pending approval.')
            return redirect('student_dashboard')
    
    # Redirect to payment page
    return redirect('course_payment', course_id=course.id)

@login_required
def course_payment(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    if request.method == 'POST':
        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            payment_proof = form.save(commit=False)
            payment_proof.user = request.user
            payment_proof.course = course
            payment_proof.save()
            messages.success(request, 'Payment proof uploaded successfully. Awaiting admin approval.')
            return redirect('payment_pending', course_id=course.id)
    else:
        form = PaymentProofForm()
    
    return render(request, 'courses/course_payment.html', {
        'course': course,
        'form': form
    })

@login_required
def payment_pending(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'courses/payment_pending.html', {'course': course})

@login_required
@user_passes_test(is_admin)
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, 'Course created successfully.')
            return redirect('course_detail', slug=course.slug)
    else:
        form = CourseForm()
    
    return render(request, 'courses/course_form.html', {'form': form, 'title': 'Create Course'})

@login_required
@user_passes_test(is_admin)
def course_update(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('course_detail', slug=course.slug)
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'courses/course_form.html', {
        'form': form,
        'title': 'Update Course',
        'course': course
    })

@login_required
@user_passes_test(is_admin)
def course_level_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        form = CourseLevelForm(request.POST)
        if form.is_valid():
            level = form.save(commit=False)
            level.course = course
            level.save()
            messages.success(request, 'Course level created successfully.')
            return redirect('course_detail', slug=course.slug)
    else:
        form = CourseLevelForm()
    
    return render(request, 'courses/course_level_form.html', {
        'form': form,
        'course': course,
        'title': 'Add Course Level'
    })

@login_required
@user_passes_test(is_admin)
def course_level_update(request, level_id):
    level = get_object_or_404(CourseLevel, id=level_id)
    course = level.course
    
    if request.method == 'POST':
        form = CourseLevelForm(request.POST, instance=level)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course level updated successfully.')
            return redirect('course_detail', slug=course.slug)
    else:
        form = CourseLevelForm(instance=level)
    
    return render(request, 'courses/course_level_form.html', {
        'form': form,
        'course': course,
        'level': level,
        'title': 'Update Course Level'
    })

def course_detail_by_id(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    levels = course.levels.all()
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'levels': levels
    })

# courses/views.py
@login_required
def student_course_dashboard(request, slug):
    course = get_object_or_404(Course, slug=slug, is_active=True)
    
    # Verify the student is enrolled in this course
    payment = get_object_or_404(PaymentProof, user=request.user, course=course, status='approved')
    
    # Get or create course progress
    progress, created = CourseProgress.objects.get_or_create(
        user=request.user,
        course=course
    )
    
    # Get course materials
    materials = course.materials.all()
    
    # Get assignments
    assignments = course.assignments.all()
    assignment_submissions = AssignmentSubmission.objects.filter(
        student=request.user,
        assignment__course=course
    ).select_related('assignment')
    
    # Create a dictionary that maps assignment IDs to their submissions
    submissions_dict = {}
    for submission in assignment_submissions:
        submissions_dict[submission.assignment_id] = submission
    
    # Get quizzes related to this course
    quizzes = Quiz.objects.filter(course=course)
    
    # Get quiz attempts and organize them by quiz ID
    quiz_attempts = QuizAttempt.objects.filter(
        user=request.user,
        quiz__in=quizzes
    ).select_related('quiz')
    
    attempts_dict = {}
    for attempt in quiz_attempts:
        attempts_dict[attempt.quiz_id] = attempt
    
    # Calculate overall progress
    total_items = materials.count() + assignments.count() + quizzes.count()
    completed_items = 0
    
    # Count completed materials (implement a system to track this)
    # Count completed assignments
    completed_items += assignment_submissions.filter(status='graded').count()
    # Count completed quizzes
    completed_items += quiz_attempts.filter(status__in=['completed', 'timed_out']).count()
    
    if total_items > 0:
        progress_percentage = int((completed_items / total_items) * 100)
        if progress_percentage != progress.progress_percentage:
            progress.progress_percentage = progress_percentage
            
            # Mark as completed if 100%
            if progress_percentage == 100 and progress.status != 'completed':
                progress.status = 'completed'
                progress.completed_at = timezone.now()
            
            progress.save()
    
    context = {
        'course': course,
        'progress': progress,
        'materials': materials,
        'assignments': assignments,
        'submissions_dict': submissions_dict,
        'quizzes': quizzes,
        'attempts_dict': attempts_dict
    }
    
    return render(request, 'courses/student_course_dashboard.html', context)

# courses/views.py
@login_required
@user_passes_test(lambda u: u.user_type == 'teacher')
def teacher_course_management(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    # Verify that this teacher has students assigned to this course
    student_profiles = StudentProfile.objects.filter(
        assigned_teacher=request.user,
        user__payment_proofs__course=course,
        user__payment_proofs__status='approved'
    ).distinct()
    
    if not student_profiles.exists():
        messages.error(request, "You don't have any students assigned to this course.")
        return redirect('teacher_dashboard')
    
    # Get course materials
    materials = course.materials.all()
    
    # Get assignments
    assignments = course.assignments.all()
    
    # Get quizzes
    quizzes = Quiz.objects.filter(course=course)
    
    context = {
        'course': course,
        'materials': materials,
        'assignments': assignments,
        'quizzes': quizzes,
        'student_profiles': student_profiles
    }
    
    return render(request, 'courses/teacher_course_management.html', context)