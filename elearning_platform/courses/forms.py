from django import forms
from .models import Course, CourseLevel
from django import forms
from .models import Assignment, AssignmentSubmission

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

# Add to courses/forms.py



class AssignmentForm(forms.ModelForm):
    """Form for teachers to create and edit assignments"""
    
    class Meta:
        model = Assignment
        fields = ['course', 'title', 'description', 'instructions', 'due_date', 'points', 'status']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class AssignmentSubmissionForm(forms.ModelForm):
    """Form for students to submit assignments"""
    
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_text', 'submission_file']
        widgets = {
            'submission_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter your response here (if applicable)'}),
            'submission_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        submission_text = cleaned_data.get('submission_text')
        submission_file = cleaned_data.get('submission_file')
        
        # Require at least one of text or file
        if not submission_text and not submission_file:
            raise forms.ValidationError(
                "Please provide either a text response or upload a file."
            )
        
        return cleaned_data

class GradeSubmissionForm(forms.ModelForm):
    """Form for teachers to grade student submissions"""
    
    class Meta:
        model = AssignmentSubmission
        fields = ['grade', 'feedback', 'status']
        widgets = {
            'grade': forms.NumberInput(attrs={'class': 'form-control'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_grade(self):
        grade = self.cleaned_data.get('grade')
        assignment = self.instance.assignment
        
        if grade is not None and grade > assignment.points:
            raise forms.ValidationError(
                f"Grade cannot exceed the maximum points ({assignment.points}) for this assignment."
            )
        
        return grade