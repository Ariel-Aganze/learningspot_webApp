from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    
    # Admin routes - these must come BEFORE the detail view pattern
    path('create/', views.course_create, name='course_create'),
    path('update/<int:course_id>/', views.course_update, name='course_update'),
    path('level/create/<int:course_id>/', views.course_level_create, name='course_level_create'),
    path('level/update/<int:level_id>/', views.course_level_update, name='course_level_update'),
    
    # Course materials management
    path('materials/', views.material_list, name='material_list'),
    path('materials/<int:course_id>/', views.material_list, name='material_list_by_course'),
    path('materials/create/', views.material_create, name='material_create'),
    path('materials/create/<int:course_id>/', views.material_create, name='material_create_for_course'),
    path('materials/update/<int:material_id>/', views.material_update, name='material_update'),
    path('materials/delete/<int:material_id>/', views.material_delete, name='material_delete'),
    
    # Student routes
    path('enroll/<int:course_id>/', views.course_enroll, name='course_enroll'),
    path('payment/<int:course_id>/', views.course_payment, name='course_payment'),
    path('payment/pending/<int:course_id>/', views.payment_pending, name='payment_pending'),
    
    path('dashboard/<slug:slug>/', views.student_course_dashboard, name='student_course_dashboard'),
    path('manage/<slug:slug>/', views.teacher_course_management, name='teacher_course_management'),

    # Assignment URLs - Teacher
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/update/<int:assignment_id>/', views.assignment_update, name='assignment_update'),
    path('assignments/submissions/<int:assignment_id>/', views.assignment_submissions, name='assignment_submissions'),
    path('submissions/grade/<int:submission_id>/', views.grade_submission, name='grade_submission'),

    # Assignment URLs - Student
    path('assignments/<slug:course_slug>/', views.student_assignments, name='student_assignments'),
    path('assignment/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('submission/<int:submission_id>/', views.submission_detail, name='submission_detail'),

    # This must come LAST because it will match anything that looks like a slug
    path('<slug:slug>/', views.course_detail, name='course_detail'),
]