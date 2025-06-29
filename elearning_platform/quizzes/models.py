from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings
from courses.models import Course

class Quiz(models.Model):
    """Model representing a quiz or assessment"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    is_active = models.BooleanField(default=True)
    is_placement_test = models.BooleanField(default=False)
    max_points = models.PositiveIntegerField(default=100, help_text="Maximum points for the quiz")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_total_points(self):
        """Calculate the total points from all questions in this quiz"""
        return self.questions.aggregate(total=models.Sum('points'))['total'] or 0
    
    def get_question_count(self):
        """Get the number of questions in the quiz"""
        return self.questions.count()
    
    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"
        ordering = ['-created_at']

class Question(models.Model):
    """Model representing a question in a quiz"""
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice (Single Select)'),
        ('multi_select', 'Multiple Choice (Multi Select)'),
        ('true_false', 'True/False'),
        ('dropdown', 'Dropdown'),
        ('star_rating', 'Star Rating'),
        ('likert_scale', 'Likert Scale'),
        ('matrix', 'Matrix Questions'),
        ('image_choice', 'Image Choice'),
        ('image_rating', 'Image Rating'),
        ('short_answer', 'Short Answer'),
        ('long_answer', 'Long Answer'),
        ('file_upload', 'File Upload'),
        ('voice_record', 'Voice Recording'),
        ('matching', 'Matching')
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    image = models.ImageField(upload_to='question_images/', null=True, blank=True)
    audio = models.FileField(upload_to='question_audio/', null=True, blank=True)
    time_limit = models.PositiveIntegerField(default=60, help_text='Time limit in seconds')
    points = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)], 
                                       help_text="Points for this question")
    order = models.PositiveIntegerField(default=0, help_text="Order in the quiz")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.text[:50]}..."
    
    class Meta:
        ordering = ['order', 'created_at']

class Choice(models.Model):
    """Model representing a choice for a multiple-choice question"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    image = models.ImageField(upload_to='choice_images/', null=True, blank=True)
    match_text = models.CharField(max_length=255, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.text

class QuizAttempt(models.Model):
    """Model representing a student's attempt at a quiz"""
    RESULT_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('failed', 'Failed'),
        ('passed', 'Passed'),
    ]
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0)
    result = models.CharField(max_length=15, choices=RESULT_CHOICES, null=True, blank=True)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"
    
    def calculate_score(self):
        """Calculate the score for this attempt"""
        # Get total possible points
        total_possible = self.quiz.get_total_points()
        if total_possible == 0:
            return 0
        
        # Calculate points earned
        points_earned = 0
        for answer in self.answers.all():
            if answer.is_correct:
                points_earned += answer.question.points
        
        # Calculate percentage score
        self.score = (points_earned / total_possible) * 100
        return self.score
    
    def complete(self):
        """Mark the attempt as completed"""
        self.end_time = timezone.now()
        self.completed = True
        self.calculate_score()
        
        # Determine result based on score (for placement tests)
        if self.quiz.is_placement_test:
            if self.score >= 80:
                self.result = 'advanced'
            elif self.score >= 50:
                self.result = 'intermediate'
            else:
                self.result = 'beginner'
        else:
            # Regular quiz
            if self.score >= 70:
                self.result = 'passed'
            else:
                self.result = 'failed'
                
        self.save()
    
    class Meta:
        ordering = ['-start_time']

class QuizAnswer(models.Model):
    """Model representing a student's answer to a question in a quiz attempt"""
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    selected_choices = models.ManyToManyField(Choice, related_name='multi_select_answers', blank=True)
    text_answer = models.TextField(null=True, blank=True)
    file_answer = models.OneToOneField('FileAnswer', on_delete=models.SET_NULL, null=True, blank=True)
    voice_answer = models.OneToOneField('VoiceRecording', on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    points_earned = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Answer to {self.question}"
    
    def evaluate(self):
        """Evaluate if the answer is correct and assign points"""
        # For auto-gradable question types
        if self.question.question_type in ['multiple_choice', 'true_false', 'dropdown']:
            if self.selected_choice and self.selected_choice.is_correct:
                self.is_correct = True
                self.points_earned = self.question.points
        
        # For multi-select questions
        elif self.question.question_type == 'multi_select':
            selected_choices = self.selected_choices.all()
            
            # Check if all selected choices are correct
            all_correct = all(choice.is_correct for choice in selected_choices)
            
            # Check if all correct choices were selected
            all_correct_selected = selected_choices.filter(is_correct=True).count() == self.question.choices.filter(is_correct=True).count()
            
            # A multi-select question is correct only if all correct choices are selected and no incorrect choices are selected
            if all_correct and all_correct_selected:
                self.is_correct = True
                self.points_earned = self.question.points
        
        # Text, file, and voice answers need manual grading
        self.save()

class TextAnswer(models.Model):
    """Model for storing text answers to open-ended questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='text_answers')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('question', 'student')

class FileAnswer(models.Model):
    """Model for storing file upload answers"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='file_answers')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='student_uploads/')
    file_type = models.CharField(max_length=50, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('question', 'student')

class VoiceRecording(models.Model):
    """Model for storing voice recording answers"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='voice_answers')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recording = models.FileField(upload_to='voice_recordings/')
    duration = models.PositiveIntegerField(help_text='Duration in seconds', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('question', 'student')