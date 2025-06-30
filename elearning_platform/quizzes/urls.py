from django.urls import path
from . import views

urlpatterns = [
    path('course/<int:course_id>/placement-test/', views.take_placement_test, name='take_placement_test'),
    
    # Teacher/Admin Quiz Management
    path('list/', views.quiz_list, name='quiz_list'),
    path('create/', views.create_quiz, name='create_quiz'),
    path('<int:quiz_id>/edit/', views.edit_quiz, name='edit_quiz'),
    path('<int:quiz_id>/questions/edit/', views.edit_quiz_questions, name='edit_quiz_questions'),
    path('question/<int:question_id>/choices/edit/', views.edit_question_choices, name='edit_question_choices'),
    path('<int:quiz_id>/detail/', views.quiz_detail, name='quiz_detail'),
    path('<int:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),
    path('<int:quiz_id>/analytics/', views.quiz_analytics, name='quiz_analytics'),
    path('<int:quiz_id>/grade-submissions/', views.grade_submissions, name='grade_submissions'),
    
    # Student Quiz Taking
    path('student/list/', views.student_quiz_list, name='student_quiz_list'),
    path('<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:attempt_id>/take/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/results/', views.quiz_results, name='quiz_results'),
    path('attempt/<int:attempt_id>/review/', views.quiz_review, name='quiz_review'),
    
    # AJAX endpoints
    path('update-question-order/', views.update_question_order, name='update_question_order'),
    path('attempt/<int:attempt_id>/update-timer/', views.update_timer, name='update_timer'),
    path('attempt/<int:attempt_id>/get-timer/', views.get_timer, name='get_timer'),
]