from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from courses.models import CourseProgress

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
    assigned_students = StudentProfile.objects.filter(assigned_teacher=request.user)
    
    return render(request, 'accounts/teacher_dashboard.html', {
        'assigned_students': assigned_students
    })

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