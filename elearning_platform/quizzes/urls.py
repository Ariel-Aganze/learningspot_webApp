from django.urls import path
from . import views

urlpatterns = [
    # Student views
    path('take-placement-test/<int:course_id>/', views.take_placement_test, name='take_placement_test'),
    path('start/<int:quiz_id>/', views.start_quiz, name='start_quiz'),
    path('take/<int:attempt_id>/', views.take_quiz, name='take_quiz'),
    path('results/<int:attempt_id>/', views.quiz_results, name='quiz_results'),
    path('timer-update/<int:attempt_id>/', views.quiz_timer_update, name='quiz_timer_update'),
    
    # Admin views
    path('questions/', views.question_list, name='question_list'),
    path('questions/create/', views.question_create, name='question_create'),
    path('questions/update/<int:question_id>/', views.question_update, name='question_update'),
    path('', views.quiz_list, name='quiz_list'),
    path('create/', views.quiz_create, name='quiz_create'),
    path('update/<int:quiz_id>/', views.quiz_update, name='quiz_update'),
    path('questions/<int:quiz_id>/', views.quiz_questions, name='quiz_questions'),
    path('results/<int:quiz_id>/', views.quiz_results_admin, name='quiz_results_admin'),
    
    # Toggle placement test status
    path('toggle-placement-test/<int:quiz_id>/', views.toggle_placement_test, name='toggle_placement_test'),
    
    # Teacher grading views
    path('grade/<int:quiz_id>/', views.grade_submissions, name='grade_submissions'),
    path('grade/answer/<int:answer_id>/', views.grade_answer, name='grade_answer'),
    path('grade-submissions/all/', views.grade_submissions_all, name='grade_submissions_all'),
    path('results/all/', views.quiz_results_all, name='quiz_results_all'),
]