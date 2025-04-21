from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    
    # Admin routes - these must come BEFORE the detail view pattern
    path('create/', views.course_create, name='course_create'),
    path('update/<int:course_id>/', views.course_update, name='course_update'),
    path('level/create/<int:course_id>/', views.course_level_create, name='course_level_create'),
    path('level/update/<int:level_id>/', views.course_level_update, name='course_level_update'),
    
    # Student routes
    path('enroll/<int:course_id>/', views.course_enroll, name='course_enroll'),
    path('payment/<int:course_id>/', views.course_payment, name='course_payment'),
    path('payment/pending/<int:course_id>/', views.payment_pending, name='payment_pending'),
    
    path('dashboard/<slug:slug>/', views.student_course_dashboard, name='student_course_dashboard'),

    # This must come LAST because it will match anything that looks like a slug
    path('<slug:slug>/', views.course_detail, name='course_detail'),
]