from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import Timesheet, TimeOption, Event
from .forms import (
    TimesheetForm, 
    TimeOptionForm, 
    TimeOptionFormSet,
    TimeOptionModelFormSet,
    TimeOptionSelectionForm,
    EventForm
)
from accounts.models import User, StudentProfile

def is_teacher(user):
    return user.user_type == 'teacher'

def is_student(user):
    return user.user_type == 'student'

@login_required
@user_passes_test(is_teacher)
def send_timesheet(request, student_id):
    student = get_object_or_404(User, id=student_id, user_type='student')
    
    # Verify that the student is assigned to this teacher
    if not StudentProfile.objects.filter(user=student, assigned_teacher=request.user).exists():
        messages.error(request, "This student is not assigned to you.")
        return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        form = TimesheetForm(request.POST)
        formset = TimeOptionFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            timesheet = form.save(commit=False)
            timesheet.teacher = request.user
            timesheet.student = student
            timesheet.save()
            
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    time_option = form.save(commit=False)
                    time_option.timesheet = timesheet
                    time_option.save()
            
            messages.success(request, f"Timesheet sent to {student.get_full_name() or student.username}.")
            return redirect('teacher_dashboard')
    else:
        form = TimesheetForm()
        formset = TimeOptionFormSet()
    
    return render(request, 'events/send_timesheet.html', {
        'form': form,
        'formset': formset,
        'student': student
    })

@login_required
@user_passes_test(is_student)
def view_timesheets(request):
    timesheets = Timesheet.objects.filter(student=request.user).order_by('-created_at')
    
    return render(request, 'events/view_timesheets.html', {
        'timesheets': timesheets
    })

@login_required
@user_passes_test(is_student)
def select_time_options(request, timesheet_id):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id, student=request.user)
    
    if timesheet.status != 'pending':
        messages.info(request, "This timesheet has already been processed.")
        return redirect('view_timesheets')
    
    time_options = timesheet.time_options.all()
    
    if request.method == 'POST':
        # Get the selected time option IDs
        selected_ids = request.POST.getlist('selected_options')
        
        if not selected_ids:
            messages.error(request, "Please select at least one time option.")
            return redirect('select_time_options', timesheet_id=timesheet.id)
        
        # Update the time options
        for option in time_options:
            option.is_selected = str(option.id) in selected_ids
            option.save()
        
        # Update the timesheet status
        timesheet.status = 'confirmed'
        timesheet.save()
        
        messages.success(request, "Time preferences saved successfully.")
        return redirect('view_timesheets')
    
    return render(request, 'events/select_time_options.html', {
        'timesheet': timesheet,
        'time_options': time_options
    })

@login_required
@user_passes_test(is_teacher)
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.user, request.POST)
        
        if form.is_valid():
            event = form.save(commit=False)
            event.teacher = request.user
            event.save()
            
            # Save students
            form.save_m2m()
            
            messages.success(request, "Event created successfully.")
            return redirect('teacher_dashboard')
    else:
        form = EventForm(request.user)
    
    return render(request, 'events/event_form.html', {
        'form': form,
        'title': 'Create New Event'
    })

@login_required
@user_passes_test(is_teacher)
def update_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, teacher=request.user)
    
    if request.method == 'POST':
        form = EventForm(request.user, request.POST, instance=event)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully.")
            return redirect('view_events')
    else:
        form = EventForm(request.user, instance=event)
    
    return render(request, 'events/event_form.html', {
        'form': form,
        'event': event,
        'title': 'Update Event'
    })

@login_required
def view_events(request):
    today = timezone.now()
    
    if request.user.user_type == 'teacher':
        # For teachers, show events they created
        events = Event.objects.filter(teacher=request.user, end_datetime__gte=today).order_by('start_datetime')
    elif request.user.user_type == 'student':
        # For students, show events they are enrolled in
        events = Event.objects.filter(students=request.user, end_datetime__gte=today).order_by('start_datetime')
    else:
        events = []
    
    return render(request, 'events/view_events.html', {
        'events': events
    })

@login_required
def event_detail(request, event_id):
    if request.user.user_type == 'teacher':
        event = get_object_or_404(Event, id=event_id, teacher=request.user)
    elif request.user.user_type == 'student':
        event = get_object_or_404(Event, id=event_id, students=request.user)
    else:
        messages.error(request, "You don't have permission to view this event.")
        return redirect('home')
    
    return render(request, 'events/event_detail.html', {
        'event': event
    })