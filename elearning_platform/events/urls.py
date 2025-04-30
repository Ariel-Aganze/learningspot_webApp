from django.urls import path
from . import views

urlpatterns = [
    # Teacher URLs
    path('timesheet/send/<int:student_id>/', views.send_timesheet, name='send_timesheet'),
    path('event/create/', views.create_event, name='create_event'),
    path('event/create-from-timesheet/', views.create_event_from_timesheet, name='create_event_from_timesheet'),
    path('event/update/<int:event_id>/', views.update_event, name='update_event'),
    
    # Student URLs
    path('timesheets/', views.view_timesheets, name='view_timesheets'),
    path('timesheet/select/<int:timesheet_id>/', views.select_time_options, name='select_time_options'),
    
    # Common URLs
    path('events/', views.view_events, name='view_events'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
]