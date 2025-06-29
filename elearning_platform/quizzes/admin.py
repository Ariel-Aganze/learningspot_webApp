from django.contrib import admin
from .models import Quiz, Question, Choice, QuizAttempt, QuizAnswer, TextAnswer, FileAnswer, VoiceRecording, QuizQuestion

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'question_type', 'points', 'order')
    list_filter = ('quiz', 'question_type')
    search_fields = ('text',)
    inlines = [ChoiceInline]

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True

class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    show_change_link = True

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'is_active', 'is_placement_test', 'max_points', 'get_question_count')
    list_filter = ('course', 'is_active', 'is_placement_test')
    search_fields = ('title', 'description')
    inlines = [QuestionInline, QuizQuestionInline]
    
    def get_question_count(self, obj):
        return obj.get_question_count()
    get_question_count.short_description = 'Questions'

class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ('question', 'selected_choice', 'text_answer', 'file_answer', 'voice_answer', 'is_correct', 'points_earned')
    can_delete = False
    # Specify which foreign key to use
    fk_name = 'quiz_attempt'

class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'result', 'start_time', 'end_time', 'completed')
    list_filter = ('quiz', 'completed', 'result')
    search_fields = ('student__username', 'student__email', 'quiz__title')
    readonly_fields = ('student', 'user', 'quiz', 'start_time', 'end_time', 'score', 'result', 'completed', 'status')
    inlines = [QuizAnswerInline]

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(QuizQuestion)
admin.site.register(QuizAttempt, QuizAttemptAdmin)
admin.site.register(TextAnswer)
admin.site.register(FileAnswer)
admin.site.register(VoiceRecording)