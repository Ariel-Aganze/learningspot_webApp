from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Timesheet(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    )
    
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_timesheets',
        limit_choices_to={'user_type': 'teacher'}
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_timesheets',
        limit_choices_to={'user_type': 'student'}
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Timesheet from {self.teacher.username} to {self.student.username}"

class TimeOption(models.Model):
    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name='time_options')
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_selected = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.day_of_week}: {self.start_time} - {self.end_time}"

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_events',
        limit_choices_to={'user_type': 'teacher'}
    )
    students = models.ManyToManyField(
        User,
        related_name='enrolled_events',
        limit_choices_to={'user_type': 'student'}
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    meeting_link = models.URLField()
    additional_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title