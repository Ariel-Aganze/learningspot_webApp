from django import forms
from django.forms import inlineformset_factory, modelformset_factory

from .models import (
    Question, Choice, Quiz, QuizQuestion, QuizAnswer,
    TextAnswer, FileAnswer, VoiceRecording
)

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'course', 'text', 'question_type', 'difficulty', 
            'time_limit', 'is_active', 'image', 'audio'
        ]
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'audio': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct', 'match_text', 'image']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'match_text': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }

# Create a formset for managing multiple choices for a question
ChoiceFormSet = inlineformset_factory(
    Question, 
    Choice,
    form=ChoiceForm,
    extra=4,
    can_delete=True,
    min_num=2,
    validate_min=True
)

class TextAnswerForm(forms.ModelForm):
    class Meta:
        model = TextAnswer
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

class FileAnswerForm(forms.ModelForm):
    class Meta:
        model = FileAnswer
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }

class VoiceRecordingForm(forms.ModelForm):
    class Meta:
        model = VoiceRecording
        fields = ['audio_file']
        widgets = {
            'audio_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'audio/*'})
        }

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['course', 'title', 'description', 'time_limit', 'passing_score', 'is_active']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = ['question', 'order']
        widgets = {
            'question': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'})
        }

# Create a formset for managing quiz questions
QuizQuestionFormSet = inlineformset_factory(
    Quiz,
    QuizQuestion,
    form=QuizQuestionForm,
    extra=5,
    can_delete=True
)

class QuizAnswerForm(forms.Form):
    """Base form for quiz answers - will be dynamically modified based on question type"""
    selected_choice = forms.IntegerField(widget=forms.RadioSelect, required=False)
    selected_choices = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)
    text_answer = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    file_answer = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}), required=False)
    time_taken = forms.IntegerField(widget=forms.HiddenInput())
    
    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        self.question_type = question.question.question_type
        
        # Configure form based on question type
        if self.question_type in ['multiple_choice', 'true_false', 'dropdown', 'star_rating', 'image_choice', 'image_rating']:
            # Single select questions
            choices = [(choice.id, choice.text) for choice in question.question.choices.all()]
            self.fields['selected_choice'].choices = choices
            # Hide other fields
            self.fields['selected_choices'].widget = forms.HiddenInput()
            self.fields['text_answer'].widget = forms.HiddenInput()
            self.fields['file_answer'].widget = forms.HiddenInput()
            
        elif self.question_type in ['multi_select', 'likert_scale', 'matrix']:
            # Multi-select questions
            choices = [(choice.id, choice.text) for choice in question.question.choices.all()]
            self.fields['selected_choices'].choices = choices
            # Hide other fields
            self.fields['selected_choice'].widget = forms.HiddenInput()
            self.fields['text_answer'].widget = forms.HiddenInput()
            self.fields['file_answer'].widget = forms.HiddenInput()
            
        elif self.question_type in ['matching']:
            # For matching questions, we'll need a custom widget
            # This is more complex and would require additional JavaScript
            pass
            
        elif self.question_type in ['short_answer', 'long_answer']:
            # Text answer questions
            if self.question_type == 'short_answer':
                self.fields['text_answer'].widget = forms.TextInput(attrs={'class': 'form-control'})
            # Hide other fields
            self.fields['selected_choice'].widget = forms.HiddenInput()
            self.fields['selected_choices'].widget = forms.HiddenInput()
            self.fields['file_answer'].widget = forms.HiddenInput()
            
        elif self.question_type in ['file_upload', 'voice_record']:
            # File upload questions
            if self.question_type == 'voice_record':
                self.fields['file_answer'].widget = forms.ClearableFileInput(
                    attrs={'class': 'form-control', 'accept': 'audio/*'}
                )
            # Hide other fields
            self.fields['selected_choice'].widget = forms.HiddenInput()
            self.fields['selected_choices'].widget = forms.HiddenInput()
            self.fields['text_answer'].widget = forms.HiddenInput()