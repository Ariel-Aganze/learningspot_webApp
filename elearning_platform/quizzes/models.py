from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q, Sum
from courses.models import Course

class Quiz(models.Model):
    """Model representing a quiz or assessment"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    time_limit = models.PositiveIntegerField(default=30, help_text='Time limit in minutes')
    passing_score = models.PositiveIntegerField(default=60, help_text='Passing score in percentage')
    is_active = models.BooleanField(default=True)
    is_placement_test = models.BooleanField(default=False)
    max_points = models.PositiveIntegerField(default=100, help_text="Maximum points for the quiz")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_total_points(self):
        """Calculate the total points from all questions in this quiz"""
        # Check both direct questions and through quiz_questions
        direct_sum = self.questions.aggregate(total=Sum('points'))['total'] or 0
        through_sum = 0
        if hasattr(self, 'quiz_questions'):
            through_sum = Question.objects.filter(
                quizquestion__quiz=self
            ).aggregate(total=Sum('points'))['total'] or 0
        return max(direct_sum, through_sum)
    
    def get_question_count(self):
        """Get the number of questions in the quiz"""
        # Check both direct questions and through quiz_questions
        direct_count = self.questions.count()
        through_count = 0
        if hasattr(self, 'quiz_questions'):
            through_count = self.quiz_questions.count()
        return max(direct_count, through_count)
    
    def get_questions(self):
        """Get all questions for this quiz, checking both relationship patterns"""
        # First try direct relationship
        direct_questions = self.questions.all().order_by('order')
        
        # If no direct questions, try through QuizQuestion
        if not direct_questions.exists():
            return Question.objects.filter(
                quizquestion__quiz=self
            ).order_by('quizquestion__order')
        
        return direct_questions
    
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
    
    # Keep this as nullable for compatibility with QuizQuestion model
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
    
    def get_choices(self):
        """Get all choices for this question"""
        return self.choices.all()
    
    class Meta:
        ordering = ['order', 'created_at']

class QuizQuestion(models.Model):
    """Model representing the relationship between Quiz and Question"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='quiz_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        unique_together = ('quiz', 'question')
        
    def __str__(self):
        return f"Quiz: {self.quiz.title} - Question: {self.question.text[:30]}..."

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
    
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('timed_out', 'Timed Out')
    ]
    
    # Support both field names for backward compatibility
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                              related_name='quiz_attempts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                           related_name='quiz_attempts_as_user', null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    score = models.FloatField(default=0)  # Standardize on FloatField for precision
    result = models.CharField(max_length=15, choices=RESULT_CHOICES, blank=True, null=True)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        student_name = self.student.username if self.student else "Unknown"
        return f"{student_name}'s attempt at {self.quiz.title}"
    
    def calculate_score(self):
        """Calculate the score for this attempt"""
        total_points = self.quiz.get_total_points()
        if total_points == 0:
            return 0
        
        # Try both field patterns
        try:
            earned_points = self.answers.aggregate(earned=Sum('points_earned'))['earned'] or 0
        except:
            try:
                earned_points = QuizAnswer.objects.filter(
                    attempt=self
                ).aggregate(earned=Sum('points_earned'))['earned'] or 0
            except:
                earned_points = 0
        
        return (earned_points / total_points) * 100
    
    def determine_result(self):
        """Determine the result based on score"""
        if self.quiz.is_placement_test:
            if self.score < 40:
                return 'beginner'
            elif self.score < 75:
                return 'intermediate'
            else:
                return 'advanced'
        else:
            if self.score >= self.quiz.passing_score:
                return 'passed'
            else:
                return 'failed'
    
    def complete(self):
        """Mark the attempt as completed"""
        self.end_time = timezone.now()
        self.score = self.calculate_score()
        self.result = self.determine_result()
        self.status = 'completed'
        self.completed = True
        self.save()
    
    def get_answers(self):
        """Get all answers for this attempt, checking both field patterns"""
        # Try both relationship patterns
        try:
            direct_answers = self.answers.all()
            if direct_answers.exists():
                return direct_answers
        except:
            pass
            
        try:
            return QuizAnswer.objects.filter(attempt=self)
        except:
            return QuizAnswer.objects.none()
    
    def save(self, *args, **kwargs):
        # Ensure user field is synced with student field for compatibility
        if self.student and not self.user:
            self.user = self.student
        elif self.user and not self.student:
            self.student = self.user
            
        # Ensure status and completed are in sync
        if self.status == 'completed' and not self.completed:
            self.completed = True
        elif self.completed and self.status != 'completed':
            self.status = 'completed'
            
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['student', 'completed']),
            models.Index(fields=['quiz', 'completed']),
        ]

class QuizAnswer(models.Model):
    """Model representing a student's answer to a question in a quiz attempt"""
    # Support both field patterns for backward compatibility
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, 
                                    related_name='answers', null=True, blank=True)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE,
                               related_name='old_answers', null=True, blank=True)
    
    # Support both question reference patterns
    question = models.ForeignKey(Question, on_delete=models.CASCADE, 
                               related_name='answers', null=True, blank=True)
    quiz_question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE,
                                    null=True, blank=True)
    
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    selected_choices = models.ManyToManyField(Choice, related_name='multi_select_answers', blank=True)
    text_answer = models.TextField(null=True, blank=True)
    file_answer = models.OneToOneField('FileAnswer', on_delete=models.SET_NULL, null=True, blank=True)
    voice_answer = models.OneToOneField('VoiceRecording', on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    points_earned = models.PositiveIntegerField(default=0)
    time_taken = models.PositiveIntegerField(default=0, help_text='Time taken in seconds')
    
    def __str__(self):
        question_text = self.question.text[:30] if self.question else (
            self.quiz_question.question.text[:30] if self.quiz_question else "Unknown Question"
        )
        return f"Answer to {question_text}..."
    
    def get_question(self):
        """Get the actual question object regardless of relationship pattern"""
        if self.question:
            return self.question
        elif self.quiz_question:
            return self.quiz_question.question
        return None
    
    def evaluate(self):
        """Evaluate if the answer is correct and assign points"""
        # Get the actual question object
        actual_question = self.get_question()
        if not actual_question:
            return
            
        # For auto-gradable question types
        if actual_question.question_type in ['multiple_choice', 'true_false', 'dropdown']:
            if self.selected_choice and self.selected_choice.is_correct:
                self.is_correct = True
                self.points_earned = actual_question.points
        
        # For multi-select questions
        elif actual_question.question_type == 'multi_select':
            selected_choices = self.selected_choices.all()
            
            # Check if all selected choices are correct
            all_correct = all(choice.is_correct for choice in selected_choices)
            
            # Check if all correct choices were selected
            all_correct_selected = selected_choices.filter(is_correct=True).count() == actual_question.choices.filter(is_correct=True).count()
            
            # A multi-select question is correct only if all correct choices are selected and no incorrect choices are selected
            if all_correct and all_correct_selected:
                self.is_correct = True
                self.points_earned = actual_question.points
        
        # Text, file, and voice answers need manual grading
        self.save()
    
    def save(self, *args, **kwargs):
        # Ensure both quiz_attempt and attempt fields are set for compatibility
        if self.quiz_attempt and not self.attempt:
            self.attempt = self.quiz_attempt
        elif self.attempt and not self.quiz_attempt:
            self.quiz_attempt = self.attempt
            
        # If we have a quiz_question but no question, set question
        if not self.question and self.quiz_question:
            self.question = self.quiz_question.question
            
        super().save(*args, **kwargs)
    
    class Meta:
        # Use conditional unique_together constraint
        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'question'],
                condition=Q(attempt__isnull=False) & Q(question__isnull=False),
                name='unique_attempt_question'
            ),
            models.UniqueConstraint(
                fields=['quiz_attempt', 'question'],
                condition=Q(quiz_attempt__isnull=False) & Q(question__isnull=False),
                name='unique_quiz_attempt_question'
            ),
            models.UniqueConstraint(
                fields=['attempt', 'quiz_question'],
                condition=Q(attempt__isnull=False) & Q(quiz_question__isnull=False),
                name='unique_attempt_quiz_question'
            ),
            models.UniqueConstraint(
                fields=['quiz_attempt', 'quiz_question'],
                condition=Q(quiz_attempt__isnull=False) & Q(quiz_question__isnull=False),
                name='unique_quiz_attempt_quiz_question'
            ),
        ]
        indexes = [
            models.Index(fields=['quiz_attempt']),
            models.Index(fields=['attempt']),
            models.Index(fields=['question']),
            models.Index(fields=['quiz_question']),
        ]

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

# Signal to maintain both relationship patterns
@receiver(post_save, sender=Question)
def create_quiz_question_for_direct_relationship(sender, instance, created, **kwargs):
    """
    When a question is saved with a direct quiz relationship,
    ensure the QuizQuestion relationship is also created.
    """
    if instance.quiz:
        # Check if a QuizQuestion already exists
        if not QuizQuestion.objects.filter(quiz=instance.quiz, question=instance).exists():
            # Create new QuizQuestion
            QuizQuestion.objects.create(
                quiz=instance.quiz,
                question=instance,
                order=instance.order
            )