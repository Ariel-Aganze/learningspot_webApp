from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()

class Question(models.Model):
    DIFFICULTY_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES)
    time_limit = models.PositiveIntegerField(default=60, help_text="Time limit in seconds")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.text[:50]}..."

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.text

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    time_limit = models.PositiveIntegerField(default=30, help_text="Time limit in minutes")
    passing_score = models.PositiveIntegerField(default=60, help_text="Passing score in percentage")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='quiz_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['quiz', 'question']
    
    def __str__(self):
        return f"{self.quiz.title} - Question {self.order+1}"

class QuizAttempt(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('timed_out', 'Timed Out'),
    )
    
    RESULT_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    score = models.PositiveIntegerField(default=0)
    result = models.CharField(max_length=15, choices=RESULT_CHOICES, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"
    
    def calculate_score(self):
        total_questions = self.answers.count()
        if total_questions == 0:
            return 0
        
        correct_answers = self.answers.filter(is_correct=True).count()
        self.score = int((correct_answers / total_questions) * 100)
        return self.score
    
    def determine_level(self):
        if self.score < self.quiz.passing_score:
            self.result = 'failed'
        else:
            # Count answers by difficulty
            beginner_correct = self.answers.filter(
                question__question__difficulty='beginner', 
                is_correct=True
            ).count()
            
            intermediate_correct = self.answers.filter(
                question__question__difficulty='intermediate', 
                is_correct=True
            ).count()
            
            advanced_correct = self.answers.filter(
                question__question__difficulty='advanced', 
                is_correct=True
            ).count()
            
            # Determine level based on performance
            if advanced_correct >= (self.answers.filter(question__question__difficulty='advanced').count() * 0.7):
                self.result = 'advanced'
            elif intermediate_correct >= (self.answers.filter(question__question__difficulty='intermediate').count() * 0.7):
                self.result = 'intermediate'
            else:
                self.result = 'beginner'
        
        return self.result

class QuizAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    time_taken = models.PositiveIntegerField(default=0, help_text="Time taken in seconds")
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"Answer by {self.attempt.user.username} for {self.question}"
    
    def save(self, *args, **kwargs):
        self.is_correct = self.selected_choice.is_correct
        super().save(*args, **kwargs)