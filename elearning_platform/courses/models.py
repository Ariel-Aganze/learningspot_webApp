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
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Brief overview of the assignment")
    instructions = models.TextField(help_text="Detailed instructions for completing the assignment")
    due_date = models.DateTimeField()
    points = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def is_past_due(self):
        """Check if the assignment's due date has passed"""
        from django.utils import timezone
        return timezone.now() > self.due_date
    
    def get_submission_status(self, student):
        """Get the submission status for a specific student"""
        submission = self.submissions.filter(student=student).first()
        if submission:
            return submission.status
        return None

class AssignmentSubmission(models.Model):
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('late', 'Late Submission'),
        ('resubmit', 'Needs Resubmission'),
    )
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_text = models.TextField(blank=True, null=True, help_text="Student's text response (if applicable)")
    submission_file = models.FileField(upload_to='assignment_submissions/', blank=True, null=True)
    submission_file_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='submitted')
    grade = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ['assignment', 'student']
        
    def __str__(self):
        return f"{self.student.username}'s submission for {self.assignment.title}"
        
    def is_late(self):
        """Check if the submission was late"""
        return self.submitted_at > self.assignment.due_date
    
    def get_grade_percentage(self):
        """Calculate the grade as a percentage"""
        if self.grade is not None and self.assignment.points > 0:
            return (self.grade / self.assignment.points) * 100
        return 0


class ContentView(models.Model):
    """
    Tracks when a student has viewed specific course content (material, assignment, quiz)
    """
    CONTENT_TYPES = (
        ('material', 'Learning Material'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_views')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='content_views')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.PositiveIntegerField()  # ID of the material, assignment, or quiz
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'content_type', 'content_id']
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"{self.user.username} viewed {self.content_type} {self.content_id}"
    