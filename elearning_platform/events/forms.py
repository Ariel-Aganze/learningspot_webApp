from django import forms
from django.forms import formset_factory, modelformset_factory
from .models import Timesheet, TimeOption, Event, User

class TimesheetForm(forms.ModelForm):
    class Meta:
        model = Timesheet
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

class TimeOptionForm(forms.ModelForm):
    DAYS_OF_WEEK = (
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    )
    
    day_of_week = forms.ChoiceField(choices=DAYS_OF_WEEK, widget=forms.Select(attrs={'class': 'form-control'}))
    
    class Meta:
        model = TimeOption
        fields = ['day_of_week', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
        }

# Create a formset for managing multiple time options
TimeOptionFormSet = formset_factory(
    TimeOptionForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True
)

# Create a formset for managing existing time options
TimeOptionModelFormSet = modelformset_factory(
    TimeOption,
    form=TimeOptionForm,
    extra=0,
    can_delete=True
)

class TimeOptionSelectionForm(forms.ModelForm):
    class Meta:
        model = TimeOption
        fields = ['is_selected']
        widgets = {
            'is_selected': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_datetime', 'end_datetime', 'meeting_link', 'additional_info', 'students']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control'}),
            'additional_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'students': forms.SelectMultiple(attrs={'class': 'form-control'})
        }
    
    def __init__(self, teacher=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if teacher:
            # Filter students to only show those assigned to this teacher
            self.fields['students'].queryset = User.objects.filter(
            student_profile__assigned_teacher=teacher,
            is_active=True)