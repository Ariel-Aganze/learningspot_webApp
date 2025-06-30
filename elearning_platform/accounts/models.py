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
    
    # Student ID field for identification
    student_id = models.CharField(max_length=5, blank=True, null=True, unique=True)
    
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
    
class CoursePeriod(models.Model):
    """Model to store the start and end dates for a student's access to a course"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_periods')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='student_periods')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'course']
        
    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.start_date} to {self.end_date})"
    
    def is_active(self):
        """Check if the course period is currently active"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    def is_ending_soon(self, days=3):
        """Check if the course period is ending within the specified number of days"""
        today = timezone.now().date()
        days_remaining = (self.end_date - today).days
        return 0 <= days_remaining <= days
    
    def is_expired(self):
        """Check if the course period has expired"""
        today = timezone.now().date()
        return today > self.end_date
    
    def days_remaining(self):
        """Get the number of days remaining in the course period"""
        today = timezone.now().date()
        return max(0, (self.end_date - today).days)


class Organization(models.Model):
    """Model for organizations purchasing courses for their employees"""
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    contact_position = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for period management
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    @property
    def is_subscription_active(self):
        """Check if the organization's subscription is active"""
        if not self.start_date or not self.end_date:
            return False
    
        from django.utils import timezone
        today = timezone.now().date()
    
        # A subscription is active if today is between start_date and end_date (inclusive)
        return self.is_active and self.start_date <= today <= self.end_date
    
    

class StudentProfile(models.Model):
    """
    Extended profile model for student users
    Stores additional information about students beyond the base User model
    """
    PROFICIENCY_LEVELS = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='student_profile'
    )
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students'
    )
    proficiency_level = models.CharField(
        max_length=20,
        choices=PROFICIENCY_LEVELS,
        blank=True, 
        null=True
    )
    assigned_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_students',
        limit_choices_to={'user_type': 'teacher'}
    )
    student_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        unique=True
    )
    
    def __str__(self):
        """String representation of the student profile"""
        return f"{self.user.get_full_name()}'s Profile"
    
    class Meta:
        """Meta options for the StudentProfile model"""
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ['user__first_name', 'user__last_name']
    
    def get_full_name(self):
        """Returns the student's full name"""
        return self.user.get_full_name()
    
    def get_courses(self):
        """Returns a queryset of courses this student is enrolled in"""
        return self.user.course_periods.all().values_list('course', flat=True)
    

class CourseApproval(models.Model):
    """Model for course and placement test approvals"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_approvals')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    is_placement_test_paid = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approvals_given')
    approval_date = models.DateTimeField(auto_now_add=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        if self.course:
            return f"{self.student} - {self.course}"
        else:
            return f"{self.student} - Placement Test"
            
    class Meta:
        verbose_name = "Course Approval"
        verbose_name_plural = "Course Approvals"

class TeacherCourse(models.Model):
    """Model to track which courses a teacher can teach"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_courses',
                              limit_choices_to={'user_type': 'teacher'})
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='teachers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['teacher', 'course']
        verbose_name = "Teacher Course"
        verbose_name_plural = "Teacher Courses"
        
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.course.title}"