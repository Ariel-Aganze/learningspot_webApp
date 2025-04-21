from django.db import models
from django.utils.text import slugify
from django.urls import reverse

from accounts.models import User
class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    overview = models.TextField(blank=True, null=True)
    placement_test_price = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('course_detail', args=[self.slug])
    
class CourseLevel(models.Model):
    LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='levels')
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    
    class Meta:
        unique_together = ('course', 'level')
    
    def __str__(self):
        return f"{self.course.title} - {self.get_level_display()}"

# courses/models.py
class CourseProgress(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progresses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_progresses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    progress_percentage = models.PositiveIntegerField(default=0)  # 0-100
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'course']
        
    def __str__(self):
        return f"{self.user.username}'s progress in {self.course.title}"
    
# courses/models.py
class CourseMaterial(models.Model):
    MATERIAL_TYPES = (
        ('document', 'Document'),
        ('video', 'Video'),
        ('image', 'Image'),
        ('link', 'External Link'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)
    file = models.FileField(upload_to='course_materials/', null=True, blank=True)
    external_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title

class Assignment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    points = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_file = models.FileField(upload_to='assignment_submissions/')
    status = models.CharField(max_length=20, choices=Assignment.STATUS_CHOICES, default='submitted')
    grade = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['assignment', 'student']
    
    def __str__(self):
        return f"{self.student.username}'s submission for {self.assignment.title}"