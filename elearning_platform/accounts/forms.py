from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from courses.models import Course
from .models import CoursePeriod, Organization, User, PaymentProof, StudentProfile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add form-control class to all fields
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
            'number_of_trainees': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
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

# Add to accounts/forms.py

class StudentProfileUpdateForm(forms.ModelForm):
    """Form for students to update their basic profile information"""
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields not required, so they can be selectively updated
        for field_name in self.fields:
            self.fields[field_name].required = False
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        # If username field is left blank, return the current username
        if not username:
            return self.instance.username
            
        # Only check for duplicates if the username is different from the current one
        if username != self.instance.username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # If email field is left blank, return the current email
        if not email:
            return self.instance.email
            
        # Only check for duplicates if the email is different from the current one
        if email != self.instance.email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email
        
    def clean(self):
        cleaned_data = super().clean()
        # Ensure that at least username and email are provided (either from form or from instance)
        if not cleaned_data.get('username') and not self.instance.username:
            self.add_error('username', "Username is required.")
        if not cleaned_data.get('email') and not self.instance.email:
            self.add_error('email', "Email is required.")
        return cleaned_data
        
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Only update the fields that were provided in the form
        if 'username' in self.changed_data:
            user.username = self.cleaned_data.get('username')
        if 'email' in self.changed_data:
            user.email = self.cleaned_data.get('email')
        if 'first_name' in self.changed_data:
            user.first_name = self.cleaned_data.get('first_name')
        if 'last_name' in self.changed_data:
            user.last_name = self.cleaned_data.get('last_name')
        if 'phone_number' in self.changed_data:
            user.phone_number = self.cleaned_data.get('phone_number')
        
        if commit:
            user.save()
        return user

class PasswordChangeForm(forms.Form):
    """Form for students to change their password"""
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        help_text="Your password must contain at least 8 characters and can't be entirely numeric."
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if self.user and not self.user.check_password(current_password):
            raise forms.ValidationError("Your current password is incorrect.")
        return current_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                self.add_error('new_password2', "The two password fields didn't match.")
            
            # Simple password validation
            if len(new_password1) < 8:
                self.add_error('new_password1', "This password is too short. It must contain at least 8 characters.")
            
            if new_password1.isdigit():
                self.add_error('new_password1', "This password is entirely numeric.")
        
        return cleaned_data
    
    def save(self, commit=True):
        if self.user and commit:
            self.user.set_password(self.cleaned_data.get('new_password1'))
            self.user.save()
        return self.user
    
class TeacherProfileUpdateForm(forms.ModelForm):
    """Form for teachers to update their basic profile information"""
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields not required, so they can be selectively updated
        for field_name in self.fields:
            self.fields[field_name].required = False
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        # If username field is left blank, return the current username
        if not username:
            return self.instance.username
            
        # Only check for duplicates if the username is different from the current one
        if username != self.instance.username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # If email field is left blank, return the current email
        if not email:
            return self.instance.email
            
        # Only check for duplicates if the email is different from the current one
        if email != self.instance.email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email
        
    def clean(self):
        cleaned_data = super().clean()
        # Ensure that at least username and email are provided (either from form or from instance)
        if not cleaned_data.get('username') and not self.instance.username:
            self.add_error('username', "Username is required.")
        if not cleaned_data.get('email') and not self.instance.email:
            self.add_error('email', "Email is required.")
        return cleaned_data
        
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Only update the fields that were provided in the form
        if 'username' in self.changed_data:
            user.username = self.cleaned_data.get('username')
        if 'email' in self.changed_data:
            user.email = self.cleaned_data.get('email')
        if 'first_name' in self.changed_data:
            user.first_name = self.cleaned_data.get('first_name')
        if 'last_name' in self.changed_data:
            user.last_name = self.cleaned_data.get('last_name')
        if 'phone_number' in self.changed_data:
            user.phone_number = self.cleaned_data.get('phone_number')
        
        if commit:
            user.save()
        return user
    

class CoursePeriodForm(forms.ModelForm):
    """Form for setting course periods for students"""
    class Meta:
        model = CoursePeriod
        fields = ['course', 'start_date', 'end_date']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        }
    
    def __init__(self, student=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If student is provided, get their approved courses
        if student:
            approved_courses = Course.objects.filter(
                paymentproof__user=student,
                paymentproof__status='approved'
            ).distinct()
            
            self.fields['course'].queryset = approved_courses
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be before start date.")
            
            # Ensure the period is at least 1 day long
            if (end_date - start_date).days < 1:
                raise forms.ValidationError("Course period must be at least 1 day long.")
        
        return cleaned_data
    
# accounts/forms.py

class OrganizationForm(forms.ModelForm):
    """Form for creating and updating organizations"""
    class Meta:
        model = Organization
        fields = [
            'name', 'contact_person', 'contact_email', 
            'contact_phone', 'contact_position',
            'start_date', 'end_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_position': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

# accounts/forms.py

class StudentCreationForm(forms.ModelForm):
    """Form for creating student accounts by admin"""
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="No Organization (Individual Student)"
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'organization']