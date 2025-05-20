from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Dashboards
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Admin actions
    path('payment/approval/<int:payment_id>/', views.payment_approval, name='payment_approval'),
    path('assign/teacher/<int:student_id>/', views.assign_teacher, name='assign_teacher'),
    path('toggle/status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('create/teacher/', views.create_teacher, name='create_teacher'),
    path('set/student/dates/<int:student_id>/', views.set_student_dates, name='set_student_dates'),

    # URL pattern for assigning student IDs
    path('assign/student-id/<int:student_id>/', views.assign_student_id, name='assign_student_id'),

    path('profile/update/', views.update_profile, name='update_profile'),

    path('profile/teacher/update/', views.teacher_update_profile, name='teacher_update_profile'),

    path('course-periods/<int:student_id>/', views.set_course_periods, name='set_course_periods'),

]