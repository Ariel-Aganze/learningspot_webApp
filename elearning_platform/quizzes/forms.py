from django import forms
from django.forms import inlineformset_factory

from .models import Question, Choice, Quiz, QuizQuestion, QuizAnswer

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['course', 'text', 'difficulty', 'time_limit', 'is_active']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'})
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
    selected_choice = forms.IntegerField(widget=forms.RadioSelect)
    time_taken = forms.IntegerField(widget=forms.HiddenInput())
    
    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        choices = [(choice.id, choice.text) for choice in question.question.choices.all()]
        self.fields['selected_choice'].choices = choices