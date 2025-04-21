from django import forms
from .models import Course, CourseLevel

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'overview', 'placement_test_price', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'overview': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'placement_test_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class CourseLevelForm(forms.ModelForm):
    class Meta:
        model = CourseLevel
        fields = ['level', 'description', 'price']
        widgets = {
            'level': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'})
        }