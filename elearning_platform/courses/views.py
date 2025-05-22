from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from quizzes.models import Quiz, QuizAttempt

from .models import Assignment, AssignmentSubmission, Course, CourseLevel, CourseProgress, CourseMaterial
from .forms import CourseForm, CourseLevelForm, AssignmentForm, AssignmentSubmissionForm, GradeSubmissionForm, CourseMaterialForm
from accounts.models import PaymentProof, StudentProfile, User
from accounts.forms import PaymentProofForm

from django.http import JsonResponse
from .models import ContentView
from django.db.models import Max
from datetime import timedelta

import uuid
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone



def is_admin(user):
    """Check if user is admin or superuser"""
    return user.is_staff or user.is_superuser

def is_teacher(user):
    """Check if user is a teacher"""
    return user.user_type == 'teacher'

def is_teacher_or_admin(user):
    """Check if user is either teacher or admin/superuser"""
    return user.user_type == 'teacher' or user.is_staff or user.is_superuser

def is_student(user):
    """Check if user is a student"""
    return user.user_type == 'student'

def is_active_user(user):
    """Basic check to ensure user is authenticated and active"""
    return user.is_authenticated and user.is_active

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

@login_required
def student_course_dashboard(request, slug):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    course = get_object_or_404(Course, slug=slug, is_active=True)
    
    # Verify the student is enrolled in this course
    payment = get_object_or_404(PaymentProof, user=request.user, course=course, status='approved')
    
    # Get or create course progress
    progress, created = CourseProgress.objects.get_or_create(
        user=request.user,
        course=course
    )
    
    # Get the last login time to determine new content
    # If not available, use 7 days ago as default
    last_login = request.user.last_login or (timezone.now() - timedelta(days=2))
    
    # Get course materials with "new" flag
    all_materials = course.materials.all().order_by('order')
    materials_count = all_materials.count()
    
    # Get viewed content
    viewed_material_ids = ContentView.objects.filter(
        user=request.user,
        course=course,
        content_type='material'
    ).values_list('content_id', flat=True)
    
    # Mark materials as new if created after last login and not viewed
    for material in all_materials:
        material.is_new = (
            material.created_at > last_login and 
            material.id not in viewed_material_ids
        )
    
    # Count new materials
    new_materials_count = sum(1 for m in all_materials if getattr(m, 'is_new', False))
    
    # Get assignments with "new" flag
    all_assignments = course.assignments.all().order_by('-due_date')
    assignments_count = all_assignments.count()
    
    # Get viewed assignments
    viewed_assignment_ids = ContentView.objects.filter(
        user=request.user,
        course=course,
        content_type='assignment'
    ).values_list('content_id', flat=True)
    
    # Mark assignments as new
    for assignment in all_assignments:
        assignment.is_new = (
            assignment.created_at > last_login and 
            assignment.id not in viewed_assignment_ids
        )
    
    # Count new assignments
    new_assignments_count = sum(1 for a in all_assignments if getattr(a, 'is_new', False))
    
    # Get assignment submissions for this user
    assignment_submissions = AssignmentSubmission.objects.filter(
        student=request.user,
        assignment__course=course
    ).select_related('assignment')
    
    # Create a dictionary that maps assignment IDs to their submissions
    submissions_dict = {}
    for submission in assignment_submissions:
        submissions_dict[submission.assignment_id] = submission
    
    # Get quizzes related to this course with "new" flag
    all_quizzes = Quiz.objects.filter(course=course).order_by('-created_at')
    quizzes_count = all_quizzes.count()
    
    # Get viewed quizzes
    viewed_quiz_ids = ContentView.objects.filter(
        user=request.user,
        course=course,
        content_type='quiz'
    ).values_list('content_id', flat=True)
    
    # Mark quizzes as new
    for quiz in all_quizzes:
        quiz.is_new = (
            quiz.created_at > last_login and 
            quiz.id not in viewed_quiz_ids
        )
    
    # Count new quizzes
    new_quizzes_count = sum(1 for q in all_quizzes if getattr(q, 'is_new', False))
    
    # Get quiz attempts and organize them by quiz ID
    quiz_attempts = QuizAttempt.objects.filter(
        user=request.user,
        quiz__in=all_quizzes
    ).select_related('quiz')
    
    attempts_dict = {}
    for attempt in quiz_attempts:
        attempts_dict[attempt.quiz_id] = attempt
    
    # Pagination for materials
    materials_paginator = Paginator(all_materials, 5)
    materials_page = request.GET.get('materials_page', 1)
    
    try:
        materials = materials_paginator.page(materials_page)
    except PageNotAnInteger:
        materials = materials_paginator.page(1)
    except EmptyPage:
        materials = materials_paginator.page(materials_paginator.num_pages)
    
    # Pagination for assignments
    assignments_paginator = Paginator(all_assignments, 5)
    assignments_page = request.GET.get('assignments_page', 1)
    
    try:
        assignments = assignments_paginator.page(assignments_page)
    except PageNotAnInteger:
        assignments = assignments_paginator.page(1)
    except EmptyPage:
        assignments = assignments_paginator.page(assignments_paginator.num_pages)
    
    # Pagination for quizzes
    quizzes_paginator = Paginator(all_quizzes, 5)
    quizzes_page = request.GET.get('quizzes_page', 1)
    
    try:
        quizzes = quizzes_paginator.page(quizzes_page)
    except PageNotAnInteger:
        quizzes = quizzes_paginator.page(1)
    except EmptyPage:
        quizzes = quizzes_paginator.page(quizzes_paginator.num_pages)
    
    # Calculate overall progress
    total_items = materials_count + assignments_count + quizzes_count
    completed_items = 0
    
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
        'materials_paginator': materials_paginator,
        'materials_count': materials_count,
        'new_materials_count': new_materials_count,
        'assignments': assignments,
        'assignments_paginator': assignments_paginator,
        'assignments_count': assignments_count,
        'new_assignments_count': new_assignments_count,
        'submissions_dict': submissions_dict,
        'quizzes': quizzes,
        'quizzes_paginator': quizzes_paginator,
        'quizzes_count': quizzes_count,
        'new_quizzes_count': new_quizzes_count,
        'attempts_dict': attempts_dict
    }

    
    return render(request, 'courses/student_course_dashboard.html', context)

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

# Course Materials Management Views
@login_required
@user_passes_test(is_teacher_or_admin)
def material_list(request, course_id=None):
    """View for listing course materials, can be filtered by course_id"""
    
    if course_id:
        course = get_object_or_404(Course, id=course_id)
        materials = CourseMaterial.objects.filter(course=course).order_by('order', 'title')
        title = f"Materials for {course.title}"
    else:
        # For admin/teachers, show materials for courses they can access
        if request.user.is_staff or request.user.is_superuser:
            # Admins can see all materials
            materials = CourseMaterial.objects.all().order_by('course__title', 'order', 'title')
        else:
            # Teachers can see materials for courses with their assigned students
            student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
            student_ids = student_profiles.values_list('user_id', flat=True)
            
            # Get courses that have students assigned to this teacher
            course_ids = set()
            for student_id in student_ids:
                student_payments = PaymentProof.objects.filter(
                    user_id=student_id, 
                    status='approved'
                )
                course_ids.update(student_payments.values_list('course_id', flat=True))
            
            materials = CourseMaterial.objects.filter(course_id__in=course_ids).order_by('course__title', 'order', 'title')
        
        title = "All Course Materials"
        course = None
    
    context = {
        'materials': materials,
        'title': title,
        'course': course
    }
    
    return render(request, 'courses/material_list.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def material_create(request, course_id=None):
    """View for creating a new course material"""
    
    # If course_id is provided, pre-select that course
    initial_data = {}
    if course_id:
        course = get_object_or_404(Course, id=course_id)
        initial_data = {'course': course}
    
    if request.method == 'POST':
        form = CourseMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save()
            messages.success(request, "Learning material created successfully!")
            
            # Redirect back to course management if we came from there
            if course_id:
                return redirect('teacher_course_management', slug=material.course.slug)
            else:
                return redirect('material_list')
    else:
        form = CourseMaterialForm(initial=initial_data)
    
    # Filter course choices for teachers
    if not (request.user.is_staff or request.user.is_superuser):
        # Get courses where the teacher has assigned students
        student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = student_profiles.values_list('user_id', flat=True)
        
        course_ids = set()
        for student_id in student_ids:
            student_payments = PaymentProof.objects.filter(
                user_id=student_id, 
                status='approved'
            )
            course_ids.update(student_payments.values_list('course_id', flat=True))
        
        form.fields['course'].queryset = Course.objects.filter(id__in=course_ids)
    
    context = {
        'form': form,
        'title': 'Add Learning Material',
        'course_id': course_id
    }
    
    return render(request, 'courses/material_form.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def material_update(request, material_id):
    """View for updating an existing course material"""
    material = get_object_or_404(CourseMaterial, id=material_id)
    
    # For teachers, check if they have access to this course
    if not (request.user.is_staff or request.user.is_superuser):
        student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = student_profiles.values_list('user_id', flat=True)
        
        student_has_course = PaymentProof.objects.filter(
            user_id__in=student_ids,
            course=material.course,
            status='approved'
        ).exists()
        
        if not student_has_course:
            messages.error(request, "You don't have permission to edit this material.")
            return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        form = CourseMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Learning material updated successfully!")
            return redirect('material_list', course_id=material.course.id)
    else:
        form = CourseMaterialForm(instance=material)
    
    # Filter course choices for teachers
    if not (request.user.is_staff or request.user.is_superuser):
        student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = student_profiles.values_list('user_id', flat=True)
        
        course_ids = set()
        for student_id in student_ids:
            student_payments = PaymentProof.objects.filter(
                user_id=student_id, 
                status='approved'
            )
            course_ids.update(student_payments.values_list('course_id', flat=True))
        
        form.fields['course'].queryset = Course.objects.filter(id__in=course_ids)
    
    context = {
        'form': form,
        'material': material,
        'title': 'Update Learning Material'
    }
    
    return render(request, 'courses/material_form.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def material_delete(request, material_id):
    """View for deleting a course material"""
    material = get_object_or_404(CourseMaterial, id=material_id)
    course = material.course
    
    # For teachers, check if they have access to this course
    if not (request.user.is_staff or request.user.is_superuser):
        student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = student_profiles.values_list('user_id', flat=True)
        
        student_has_course = PaymentProof.objects.filter(
            user_id__in=student_ids,
            course=course,
            status='approved'
        ).exists()
        
        if not student_has_course:
            messages.error(request, "You don't have permission to delete this material.")
            return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        material.delete()
        messages.success(request, "Learning material deleted successfully!")
        
        # Redirect to course management if we have a slug
        if 'course_slug' in request.POST:
            return redirect('teacher_course_management', slug=request.POST['course_slug'])
        else:
            return redirect('material_list', course_id=course.id)
    
    context = {
        'material': material,
        'course': course
    }
    
    return render(request, 'courses/material_confirm_delete.html', context)

# Teacher views for assignments
@login_required
@user_passes_test(is_teacher_or_admin)  # Changed from is_teacher to is_teacher_or_admin
def assignment_list(request):
    """View for teachers and admins to see all assignments they can manage"""
    # For admins, show all assignments
    if request.user.is_staff or request.user.is_superuser:
        assignments = Assignment.objects.all().order_by('-created_at')
    else:
        # For teachers, show only assignments for their courses
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
@user_passes_test(is_teacher_or_admin)  # Changed from is_teacher to is_teacher_or_admin
def assignment_create(request):
    """View for teachers and admins to create a new assignment"""
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment created successfully!")
            return redirect('assignment_list')
    else:
        form = AssignmentForm()
    
    # For teachers, limit course choices to courses they teach
    if not (request.user.is_staff or request.user.is_superuser):
        teacher_students = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = teacher_students.values_list('user_id', flat=True)
        
        course_ids = set()
        for student_id in student_ids:
            student_payments = PaymentProof.objects.filter(
                user_id=student_id, 
                status='approved'
            )
            course_ids.update(student_payments.values_list('course_id', flat=True))
        
        form.fields['course'].queryset = Course.objects.filter(id__in=course_ids)
    
    return render(request, 'courses/assignment_form.html', {
        'form': form,
        'title': 'Create Assignment'
    })


@login_required
@user_passes_test(is_teacher_or_admin)  # Changed from is_teacher to is_teacher_or_admin
def assignment_update(request, assignment_id):
    """View for teachers and admins to update an existing assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check permissions for teachers (admins can access any assignment)
    if not (request.user.is_staff or request.user.is_superuser):
        # For teachers, check if they have any students enrolled in this course
        student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = student_profiles.values_list('user_id', flat=True)
        
        student_has_course = PaymentProof.objects.filter(
            user_id__in=student_ids,
            course=assignment.course,
            status='approved'
        ).exists()
        
        if not student_has_course:
            messages.error(request, "You don't have permission to edit this assignment.")
            return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated successfully!")
            
            # Redirect based on user type
            if request.user.is_staff or request.user.is_superuser:
                return redirect('assignment_list')
            else:
                return redirect('assignment_list')
    else:
        form = AssignmentForm(instance=assignment)
    
    # For teachers, limit course choices to courses they teach
    if not (request.user.is_staff or request.user.is_superuser):
        teacher_students = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = teacher_students.values_list('user_id', flat=True)
        
        course_ids = set()
        for student_id in student_ids:
            student_payments = PaymentProof.objects.filter(
                user_id=student_id, 
                status='approved'
            )
            course_ids.update(student_payments.values_list('course_id', flat=True))
        
        form.fields['course'].queryset = Course.objects.filter(id__in=course_ids)
    
    return render(request, 'courses/assignment_form.html', {
        'form': form,
        'assignment': assignment,
        'title': 'Update Assignment'
    })

@login_required
@user_passes_test(is_teacher_or_admin)  # Changed from is_teacher to is_teacher_or_admin
def assignment_submissions(request, assignment_id):
    """View for teachers and admins to see all submissions for an assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check permissions for teachers (admins can access any assignment)
    if not (request.user.is_staff or request.user.is_superuser):
        # For teachers, check if they have any students enrolled in this course
        student_profiles = StudentProfile.objects.filter(assigned_teacher=request.user)
        student_ids = student_profiles.values_list('user_id', flat=True)
        
        student_has_course = PaymentProof.objects.filter(
            user_id__in=student_ids,
            course=assignment.course,
            status='approved'
        ).exists()
        
        if not student_has_course:
            messages.error(request, "You don't have permission to view submissions for this assignment.")
            return redirect('teacher_dashboard')
    
    # Get all submissions or filter by teacher's students for teachers
    if request.user.is_staff or request.user.is_superuser:
        submissions = assignment.submissions.all().select_related('student')
    else:
        # Get submissions from students assigned to this teacher
        student_ids = StudentProfile.objects.filter(assigned_teacher=request.user).values_list('user_id', flat=True)
        submissions = assignment.submissions.filter(student_id__in=student_ids).select_related('student')
    
    return render(request, 'courses/assignment_submissions.html', {
        'assignment': assignment,
        'submissions': submissions
    })

@login_required
@user_passes_test(is_teacher_or_admin)  # Changed from is_teacher to is_teacher_or_admin
def grade_submission(request, submission_id):
    """View for teachers and admins to grade a specific submission"""
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)
    assignment = submission.assignment
    
    # Check permissions (admins can grade any submission)
    if not (request.user.is_staff or request.user.is_superuser):
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

@login_required
def mark_content_viewed(request):
    """
    AJAX endpoint to mark content as viewed by the student
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        content_type = request.POST.get('content_type')
        content_id = request.POST.get('content_id')
        course_id = request.POST.get('course_id')
        
        if not all([content_type, content_id, course_id]):
            return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)
        
        try:
            course = Course.objects.get(id=course_id)
            content_view, created = ContentView.objects.get_or_create(
                user=request.user,
                course=course,
                content_type=content_type,
                content_id=content_id
            )
            
            if not created:
                # Update the timestamp if it already exists
                content_view.viewed_at = timezone.now()
                content_view.save()
                
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)





