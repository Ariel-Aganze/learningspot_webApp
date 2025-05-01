from django import forms
from .models import Course, CourseLevel, Assignment, AssignmentSubmission, CourseMaterial

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

# New form for course materials
class CourseMaterialForm(forms.ModelForm):
    """Form for teachers to add and edit course learning materials"""
    
    class Meta:
        model = CourseMaterial
        fields = ['course', 'title', 'description', 'material_type', 'file', 'external_url', 'order']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'material_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_material_type'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'id': 'id_file'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control', 'id': 'id_external_url'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get('material_type')
        file = cleaned_data.get('file')
        external_url = cleaned_data.get('external_url')
        
        # Validate based on material type
        if material_type in ['document', 'video', 'image']:
            if not file:
                self.add_error('file', f"A file is required for {material_type} materials.")
        elif material_type == 'link':
            if not external_url:
                self.add_error('external_url', "A URL is required for link materials.")
        
        return cleaned_data