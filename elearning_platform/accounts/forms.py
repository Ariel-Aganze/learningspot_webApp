from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, PaymentProof, StudentProfile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    is_organization = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input',
        'id': 'is_organization'
    }))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_organization']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['company_name', 'contact_person', 'phone_number', 'number_of_trainees']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'number_of_trainees': forms.NumberInput(attrs={'class': 'form-control'})
        }

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ['proof_image']
        widgets = {
            'proof_image': forms.FileInput(attrs={'class': 'form-control'})
        }

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['proficiency_level']
        widgets = {
            'proficiency_level': forms.Select(attrs={'class': 'form-control'})
        }

class TeacherAssignmentForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['assigned_teacher']
        widgets = {
            'assigned_teacher': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_teacher'].queryset = User.objects.filter(user_type='teacher')

class TeacherCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'phone_number']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'teacher'
        if commit:
            user.save()
        return user