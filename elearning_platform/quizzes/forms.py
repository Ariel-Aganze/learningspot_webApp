# Path: elearning_platform/quizzes/forms.py

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import Quiz, Question, Choice, QuizAnswer, TextAnswer, FileAnswer, VoiceRecording

class QuizForm(forms.ModelForm):
    """Form for creating and editing quizzes"""
    
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'course', 'is_active', 'is_placement_test', 'max_points']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'max_points': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_placement_test': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class QuestionForm(forms.ModelForm):
    """Form for creating and editing questions"""
    
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'image', 'audio', 'time_limit', 'points', 'order']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'audio': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class BaseQuestionFormSet(BaseInlineFormSet):
    """Base formset for questions with validation"""
    
    def clean(self):
        """Validate the formset as a whole"""
        super().clean()
        
        # Check if at least one question is added
        if any(self.errors):
            return
            
        if not any(cleaned_data and not cleaned_data.get('DELETE', False)
                  for cleaned_data in self.cleaned_data):
            raise ValidationError("At least one question is required.")
        
        # Check if total points match the quiz's max_points
        if self.instance.pk:  # Only check for existing quizzes
            total_points = sum(form.cleaned_data.get('points', 0) 
                              for form in self.forms 
                              if form.cleaned_data and not form.cleaned_data.get('DELETE', False))
            
            if total_points != self.instance.max_points:
                raise ValidationError(
                    f"Total question points ({total_points}) must equal the quiz's maximum points ({self.instance.max_points})."
                )

# Create a formset for questions within a quiz
QuestionFormSet = inlineformset_factory(
    Quiz, 
    Question, 
    form=QuestionForm,
    formset=BaseQuestionFormSet,
    extra=1,  # Show at least one empty form
    can_delete=True,
    min_num=1,  # Require at least one question
    validate_min=True
)

class ChoiceForm(forms.ModelForm):
    """Form for creating and editing choices"""
    
    class Meta:
        model = Choice
        fields = ['text', 'image', 'match_text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'match_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class BaseChoiceFormSet(BaseInlineFormSet):
    """Base formset for choices with validation"""
    
    def clean(self):
        """Validate the formset as a whole"""
        super().clean()
        
        if any(self.errors):
            return
            
        # Get the question type
        question = self.instance
        
        # Make sure there's at least one choice for choice-based questions
        if question.question_type in ['multiple_choice', 'multi_select', 'dropdown', 
                                      'true_false', 'image_choice']:
            if not any(cleaned_data and not cleaned_data.get('DELETE', False)
                      for cleaned_data in self.cleaned_data):
                raise ValidationError("At least one choice is required for this question type.")
            
            # For single-select questions, ensure exactly one choice is marked correct
            if question.question_type in ['multiple_choice', 'true_false', 'dropdown']:
                correct_choices = sum(1 for cleaned_data in self.cleaned_data 
                                     if cleaned_data and not cleaned_data.get('DELETE', False) 
                                     and cleaned_data.get('is_correct'))
                
                if correct_choices != 1:
                    raise ValidationError("Exactly one choice must be marked as correct.")

# Create a formset for choices within a question
ChoiceFormSet = inlineformset_factory(
    Question, 
    Choice, 
    form=ChoiceForm,
    formset=BaseChoiceFormSet,
    extra=4,  # Show four empty forms by default
    can_delete=True
)

class QuizAnswerForm(forms.ModelForm):
    """Form for students to answer questions"""
    
    class Meta:
        model = QuizAnswer
        fields = ['selected_choice', 'text_answer']
    
    def __init__(self, *args, **kwargs):
        question = kwargs.pop('question', None)
        super().__init__(*args, **kwargs)
        
        if question:
            # Customize the form based on question type
            if question.question_type in ['multiple_choice', 'true_false', 'dropdown']:
                self.fields['selected_choice'].queryset = question.choices.all()
                self.fields['selected_choice'].widget = forms.RadioSelect()
                self.fields['text_answer'].widget = forms.HiddenInput()
                
            elif question.question_type in ['short_answer', 'long_answer']:
                self.fields['selected_choice'].widget = forms.HiddenInput()
                rows = 3 if question.question_type == 'short_answer' else 6
                self.fields['text_answer'].widget = forms.Textarea(attrs={'rows': rows, 'class': 'form-control'})
                
            else:
                # Handle other question types as needed
                pass

class TextAnswerForm(forms.ModelForm):
    """Form for text-based answers"""
    
    class Meta:
        model = TextAnswer
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class FileAnswerForm(forms.ModelForm):
    """Form for file upload answers"""
    
    class Meta:
        model = FileAnswer
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

class VoiceRecordingForm(forms.ModelForm):
    """Form for voice recording answers"""
    
    class Meta:
        model = VoiceRecording
        fields = ['recording']
        widgets = {
            'recording': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
        }