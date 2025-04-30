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
    
    QUESTION_TYPE_CHOICES = (
        # Multiple choice questions
        ('multiple_choice', 'Multiple Choice (Single Select)'),
        ('multi_select', 'Multiple Choice (Multi Select)'),
        ('true_false', 'True/False'),
        ('dropdown', 'Dropdown'),
        ('star_rating', 'Star Rating'),
        ('likert_scale', 'Likert Scale'),
        ('matrix', 'Matrix Questions'),
        ('image_choice', 'Image Choice'),
        ('image_rating', 'Image Rating'),
        
        # Text questions
        ('short_answer', 'Short Answer'),
        ('long_answer', 'Long Answer'),
        
        # Media questions
        ('file_upload', 'File Upload'),
        ('voice_record', 'Voice Recording'),
        
        # Matching questions
        ('matching', 'Matching'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='multiple_choice')
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES)
    time_limit = models.PositiveIntegerField(default=60, help_text="Time limit in seconds")
    is_active = models.BooleanField(default=True)
    
    # Media fields for questions
    image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    audio = models.FileField(upload_to='question_audio/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.text[:50]}..."
    
    def is_multiple_choice_type(self):
        """Check if the question is a multiple choice type that requires choices"""
        return self.question_type in [
            'multiple_choice', 'multi_select', 'true_false', 'dropdown',
            'star_rating', 'likert_scale', 'matrix', 'image_choice', 
            'image_rating', 'matching'
        ]
    
    def is_text_answer_type(self):
        """Check if the question requires a text answer"""
        return self.question_type in ['short_answer', 'long_answer']
    
    def is_file_upload_type(self):
        """Check if the question requires a file upload"""
        return self.question_type in ['file_upload', 'voice_record']

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    
    # For matching questions
    match_text = models.CharField(max_length=255, blank=True, null=True)
    
    # For image choice
    image = models.ImageField(upload_to='choice_images/', blank=True, null=True)
    
    def __str__(self):
        return self.text

class TextAnswer(models.Model):
    """Model for storing text-based answers to short_answer and long_answer questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='text_answers')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['question', 'student']
    
    def __str__(self):
        return f"Answer by {self.student.username} for {self.question}"

class FileAnswer(models.Model):
    """Model for storing file upload answers"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='file_answers')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='student_uploads/')
    file_type = models.CharField(max_length=50, blank=True)  # Stores the MIME type
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['question', 'student']
    
    def __str__(self):
        return f"File upload by {self.student.username} for {self.question}"

class VoiceRecording(models.Model):
    """Model for storing voice recording answers"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='voice_recordings')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to='voice_recordings/')
    duration = models.PositiveIntegerField(help_text="Duration in seconds", default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['question', 'student']
    
    def __str__(self):
        return f"Voice recording by {self.student.username} for {self.question}"

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
        total_questions = self.quiz.quiz_questions.count()
        if total_questions == 0:
            return 0
    
    # Count correctly answered questions
        correct_answers = self.answers.filter(is_correct=True).count()
    
    # Get the number of unanswered questions
        answered_questions = self.answers.count()
        unanswered_questions = total_questions - answered_questions
    
    # Consider unanswered questions as incorrect (score of 0)
        self.score = int((correct_answers / total_questions) * 100)
        return self.score
    
    def determine_level(self):
        if self.score < self.quiz.passing_score:
            self.result = 'failed'
        else:
        # Count answers by difficulty
            beginner_questions = self.answers.filter(question__question__difficulty='beginner').count()
            intermediate_questions = self.answers.filter(question__question__difficulty='intermediate').count()
            advanced_questions = self.answers.filter(question__question__difficulty='advanced').count()
        
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
        
        # Fix: Avoid division by zero
            advanced_percentage = 0
            if advanced_questions > 0:
                advanced_percentage = advanced_correct / advanced_questions
            
            intermediate_percentage = 0
            if intermediate_questions > 0:
                intermediate_percentage = intermediate_correct / intermediate_questions
            
            beginner_percentage = 0
            if beginner_questions > 0:
                beginner_percentage = beginner_correct / beginner_questions
        
        # Determine level based on performance
            if advanced_questions > 0 and advanced_percentage >= 0.7:
                self.result = 'advanced'
            elif intermediate_questions > 0 and intermediate_percentage >= 0.7:
                self.result = 'intermediate'
            else:
                self.result = 'beginner'
    
        return self.result

class QuizAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    time_taken = models.PositiveIntegerField(default=0, help_text="Time taken in seconds")
    
    # References to other answer types
    text_answer = models.OneToOneField(TextAnswer, on_delete=models.SET_NULL, null=True, blank=True)
    file_answer = models.OneToOneField(FileAnswer, on_delete=models.SET_NULL, null=True, blank=True)
    voice_recording = models.OneToOneField(VoiceRecording, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"Answer by {self.attempt.user.username} for {self.question}"
    
    def save(self, *args, **kwargs):
        # For multiple choice questions
        if self.selected_choice:
            self.is_correct = self.selected_choice.is_correct
        
        # For other question types, correctness must be determined manually
        # This would typically be done by a teacher or an automated system
        
        super().save(*args, **kwargs)