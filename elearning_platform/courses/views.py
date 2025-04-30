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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Assignment, AssignmentSubmission
from .forms import AssignmentForm, AssignmentSubmissionForm, GradeSubmissionForm

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




def is_teacher(user):
    return user.user_type == 'teacher'

# Teacher views for assignments
@login_required
@user_passes_test(is_teacher)
def assignment_list(request):
    """View for teachers to see all assignments they can manage"""
    # Get all courses where the teacher has assigned students
    teacher_students = StudentProfile.objects.filter(assigned_teacher=request.user)
    student_ids = teacher_students.values_list('user_id', flat=True)
    
    # Get courses for these students
    course_ids = set()
    for student_id in student_ids:
        student_payments = PaymentProof.objects.filter(
            user_id=student_id, 
            status='approved'
        )
        course_ids.update(student_payments.values_list('course_id', flat=True))
    
    # Get assignments for these courses
    assignments = Assignment.objects.filter(course_id__in=course_ids).order_by('-created_at')
    
    # Get submission counts for each assignment
    for assignment in assignments:
        assignment.submission_count = assignment.submissions.count()
        assignment.ungraded_count = assignment.submissions.filter(status='submitted').count()
    
    context = {
        'assignments': assignments
    }
    
    return render(request, 'courses/assignment_list.html', context)

@login_required
@user_passes_test(is_teacher)
def assignment_create(request):
    """View for teachers to create a new assignment"""
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment created successfully!")
            return redirect('assignment_list')
    else:
        form = AssignmentForm()
    
    return render(request, 'courses/assignment_form.html', {
        'form': form,
        'title': 'Create Assignment'
    })

@login_required
@user_passes_test(is_teacher)
def assignment_update(request, assignment_id):
    """View for teachers to update an existing assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated successfully!")
            return redirect('assignment_list')
    else:
        form = AssignmentForm(instance=assignment)
    
    return render(request, 'courses/assignment_form.html', {
        'form': form,
        'assignment': assignment,
        'title': 'Update Assignment'
    })

@login_required
@user_passes_test(is_teacher)
def assignment_submissions(request, assignment_id):
    """View for teachers to see all submissions for an assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    submissions = assignment.submissions.all().select_related('student')
    
    return render(request, 'courses/assignment_submissions.html', {
        'assignment': assignment,
        'submissions': submissions
    })

@login_required
@user_passes_test(is_teacher)
def grade_submission(request, submission_id):
    """View for teachers to grade a specific submission"""
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    assignment = submission.assignment
    
    # Verify this teacher is assigned to the student
    if not StudentProfile.objects.filter(user=submission.student, assigned_teacher=request.user).exists():
        messages.error(request, "You are not authorized to grade this submission.")
        return redirect('assignment_list')
    
    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            grade_submission = form.save(commit=False)
            grade_submission.status = 'graded'
            grade_submission.graded_at = timezone.now()
            grade_submission.save()
            
            messages.success(request, f"Submission graded successfully!")
            return redirect('assignment_submissions', assignment_id=assignment.id)
    else:
        form = GradeSubmissionForm(instance=submission)
    
    return render(request, 'courses/grade_submission.html', {
        'form': form,
        'submission': submission,
        'assignment': assignment
    })

# Student views for assignments
@login_required
def student_assignments(request, course_slug):
    """View for students to see all assignments for a specific course"""
    course = get_object_or_404(Course, slug=course_slug)
    
    # Verify the student is enrolled
    if not PaymentProof.objects.filter(user=request.user, course=course, status='approved').exists():
        messages.error(request, "You are not enrolled in this course.")
        return redirect('student_dashboard')
    
    # Get all assignments for this course
    assignments = Assignment.objects.filter(course=course, status='published')
    
    # Add submission status for each assignment
    for assignment in assignments:
        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=request.user
        ).first()
        
        if submission:
            assignment.submission_status = submission.status
            assignment.submission_id = submission.id
        else:
            assignment.submission_status = None
    
    return render(request, 'courses/student_assignments.html', {
        'course': course,
        'assignments': assignments
    })

@login_required
def assignment_detail(request, assignment_id):
    """View for students to see assignment details and submit work"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Verify the student is enrolled in the course
    if not PaymentProof.objects.filter(user=request.user, course=assignment.course, status='approved').exists():
        messages.error(request, "You are not enrolled in this course.")
        return redirect('student_dashboard')
    
    # Check if student has already submitted
    submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()
    
    if request.method == 'POST' and (not submission or submission.status == 'resubmit'):
        form = AssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            
            # Set status based on due date
            if assignment.is_past_due():
                submission.status = 'late'
            else:
                submission.status = 'submitted'
                
            # Store the original filename
            if submission.submission_file:
                submission.submission_file_name = submission.submission_file.name
                
            submission.save()
            messages.success(request, "Assignment submitted successfully!")
            return redirect('student_assignments', course_slug=assignment.course.slug)
    else:
        form = AssignmentSubmissionForm(instance=submission)
    
    context = {
        'assignment': assignment,
        'submission': submission,
        'form': form,
        'is_past_due': assignment.is_past_due()
    }
    
    return render(request, 'courses/assignment_detail.html', context)

@login_required
def submission_detail(request, submission_id):
    """View for students to see their submission details and grade"""
    submission = get_object_or_404(AssignmentSubmission, id=submission_id, student=request.user)
    assignment = submission.assignment
    
    return render(request, 'courses/submission_detail.html', {
        'submission': submission,
        'assignment': assignment
    })