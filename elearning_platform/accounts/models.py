from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For organization users
    is_organization = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    number_of_trainees = models.PositiveIntegerField(default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    
    def is_teacher(self):
        return self.user_type == 'teacher'
    
    def is_student(self):
        return self.user_type == 'student'
    
    def save(self, *args, **kwargs):
        # Check if end date has passed
        if self.end_date and self.end_date < timezone.now().date():
            self.is_active = False
        super().save(*args, **kwargs)

class StudentProfile(models.Model):
    PROFICIENCY_LEVELS = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    proficiency_level = models.CharField(max_length=15, choices=PROFICIENCY_LEVELS, blank=True, null=True)
    assigned_teacher = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_students',
        limit_choices_to={'user_type': 'teacher'}
    )
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class PaymentProof(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_proofs')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    proof_image = models.ImageField(upload_to='payment_proofs/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Payment proof by {self.user.username} for {self.course.title}"