from django.contrib import admin
from .models import Quiz, Question, Choice, QuizQuestion

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'is_active', 'is_placement_test')
    list_filter = ('is_active', 'is_placement_test', 'course')
    search_fields = ('title',)
    
    # Optional: Add actions to bulk set/unset placement test status
    actions = ['mark_as_placement_test', 'unmark_as_placement_test']
    
    def mark_as_placement_test(self, request, queryset):
        # First, unmark any existing placement tests for the same courses
        for quiz in queryset:
            Quiz.objects.filter(course=quiz.course, is_placement_test=True).update(is_placement_test=False)
        
        # Then mark selected quizzes as placement tests
        queryset.update(is_placement_test=True)
        self.message_user(request, f"{queryset.count()} quizzes marked as placement tests.")
    
    def unmark_as_placement_test(self, request, queryset):
        queryset.update(is_placement_test=False)
        self.message_user(request, f"{queryset.count()} quizzes unmarked as placement tests.")
    
    mark_as_placement_test.short_description = "Mark selected quizzes as placement tests"
    unmark_as_placement_test.short_description = "Unmark selected quizzes as placement tests"

admin.site.register(Quiz, QuizAdmin)
