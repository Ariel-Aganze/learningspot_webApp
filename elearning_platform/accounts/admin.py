from django.contrib import admin
from .models import User, StudentProfile, PaymentProof, CoursePeriod, TeacherCourse

@admin.register(TeacherCourse)
class TeacherCourseAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'course', 'created_at')
    list_filter = ('teacher', 'course')
    search_fields = ('teacher__username', 'teacher__email', 'course__title')
    date_hierarchy = 'created_at'