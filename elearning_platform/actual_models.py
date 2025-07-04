# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AccountsCourseapproval(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_placement_test_paid = models.BooleanField()
    approval_date = models.DateTimeField()
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    approved_by = models.ForeignKey('AccountsUser', models.DO_NOTHING, blank=True, null=True)
    course = models.ForeignKey('CoursesCourse', models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey('AccountsUser', models.DO_NOTHING, related_name='accountscourseapproval_student_set')

    class Meta:
        managed = False
        db_table = 'accounts_courseapproval'


class AccountsCourseperiod(models.Model):
    id = models.BigAutoField(primary_key=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    course = models.ForeignKey('CoursesCourse', models.DO_NOTHING)
    student = models.ForeignKey('AccountsUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'accounts_courseperiod'
        unique_together = (('student', 'course'),)


class AccountsOrganization(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    contact_email = models.CharField(max_length=254)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    contact_position = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'accounts_organization'


class AccountsPaymentproof(models.Model):
    id = models.BigAutoField(primary_key=True)
    proof_image = models.CharField(max_length=100)
    status = models.CharField(max_length=10)
    submitted_at = models.DateTimeField()
    processed_at = models.DateTimeField(blank=True, null=True)
    course = models.ForeignKey('CoursesCourse', models.DO_NOTHING)
    user = models.ForeignKey('AccountsUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'accounts_paymentproof'


class AccountsStudentprofile(models.Model):
    id = models.BigAutoField(primary_key=True)
    proficiency_level = models.CharField(max_length=20, blank=True, null=True)
    assigned_teacher = models.ForeignKey('AccountsUser', models.DO_NOTHING, blank=True, null=True)
    user = models.OneToOneField('AccountsUser', models.DO_NOTHING, related_name='accountsstudentprofile_user_set')
    student_id = models.CharField(unique=True, max_length=20, blank=True, null=True)
    organization = models.ForeignKey(AccountsOrganization, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'accounts_studentprofile'


class AccountsUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    date_joined = models.DateTimeField()
    user_type = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_organization = models.BooleanField()
    company_name = models.CharField(max_length=255, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    number_of_trainees = models.IntegerField()
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    student_id = models.CharField(unique=True, max_length=5, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'accounts_user'


class AccountsUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AccountsUser, models.DO_NOTHING)
    group = models.ForeignKey('AuthGroup', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'accounts_user_groups'
        unique_together = (('user', 'group'),)


class AccountsUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AccountsUser, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'accounts_user_user_permissions'
        unique_together = (('user', 'permission'),)


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class CoursesAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    points = models.IntegerField()
    created_at = models.DateTimeField()
    course = models.ForeignKey('CoursesCourse', models.DO_NOTHING)
    instructions = models.TextField()
    status = models.CharField(max_length=10)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'courses_assignment'


class CoursesAssignmentsubmission(models.Model):
    id = models.BigAutoField(primary_key=True)
    submission_file = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10)
    grade = models.IntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField()
    graded_at = models.DateTimeField(blank=True, null=True)
    assignment = models.ForeignKey(CoursesAssignment, models.DO_NOTHING)
    student = models.ForeignKey(AccountsUser, models.DO_NOTHING)
    submission_file_name = models.CharField(max_length=255, blank=True, null=True)
    submission_text = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'courses_assignmentsubmission'
        unique_together = (('assignment', 'student'),)


class CoursesContentview(models.Model):
    id = models.BigAutoField(primary_key=True)
    content_type = models.CharField(max_length=20)
    content_id = models.IntegerField()
    viewed_at = models.DateTimeField()
    course = models.ForeignKey('CoursesCourse', models.DO_NOTHING)
    user = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'courses_contentview'
        unique_together = (('user', 'content_type', 'content_id'),)


class CoursesCourse(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200)
    slug = models.CharField(unique=True, max_length=200)
    description = models.TextField()
    overview = models.TextField(blank=True, null=True)
    placement_test_price = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'courses_course'


class CoursesCourselevel(models.Model):
    id = models.BigAutoField(primary_key=True)
    level = models.CharField(max_length=15)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    course = models.ForeignKey(CoursesCourse, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'courses_courselevel'
        unique_together = (('course', 'level'),)


class CoursesCoursematerial(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    material_type = models.CharField(max_length=20)
    file = models.CharField(max_length=100, blank=True, null=True)
    external_url = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField()
    order = models.IntegerField()
    course = models.ForeignKey(CoursesCourse, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'courses_coursematerial'


class CoursesCourseprogress(models.Model):
    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=20)
    progress_percentage = models.IntegerField()
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    course = models.ForeignKey(CoursesCourse, models.DO_NOTHING)
    user = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'courses_courseprogress'
        unique_together = (('user', 'course'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class EventsEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    meeting_link = models.CharField(max_length=200)
    additional_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    teacher = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'events_event'


class EventsEventStudents(models.Model):
    id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(EventsEvent, models.DO_NOTHING)
    user = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'events_event_students'
        unique_together = (('event', 'user'),)


class EventsTimeoption(models.Model):
    id = models.BigAutoField(primary_key=True)
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_selected = models.BooleanField()
    timesheet = models.ForeignKey('EventsTimesheet', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'events_timeoption'


class EventsTimesheet(models.Model):
    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=10)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    student = models.ForeignKey(AccountsUser, models.DO_NOTHING)
    teacher = models.ForeignKey(AccountsUser, models.DO_NOTHING, related_name='eventstimesheet_teacher_set')

    class Meta:
        managed = False
        db_table = 'events_timesheet'


class QuizzesChoice(models.Model):
    id = models.BigAutoField(primary_key=True)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField()
    question = models.ForeignKey('QuizzesQuestion', models.DO_NOTHING)
    image = models.CharField(max_length=100, blank=True, null=True)
    match_text = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'quizzes_choice'


class QuizzesFileanswer(models.Model):
    id = models.BigAutoField(primary_key=True)
    file = models.CharField(max_length=100)
    file_type = models.CharField(max_length=50)
    submitted_at = models.DateTimeField()
    question = models.ForeignKey('QuizzesQuestion', models.DO_NOTHING)
    student = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'quizzes_fileanswer'
        unique_together = (('question', 'student'),)


class QuizzesQuestion(models.Model):
    id = models.BigAutoField(primary_key=True)
    text = models.TextField()
    time_limit = models.IntegerField()
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    audio = models.CharField(max_length=100, blank=True, null=True)
    image = models.CharField(max_length=100, blank=True, null=True)
    question_type = models.CharField(max_length=20)
    order = models.IntegerField()
    points = models.IntegerField()
    quiz = models.ForeignKey('QuizzesQuiz', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'quizzes_question'


class QuizzesQuiz(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    course = models.ForeignKey(CoursesCourse, models.DO_NOTHING)
    is_placement_test = models.BooleanField()
    max_points = models.IntegerField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'quizzes_quiz'


class QuizzesQuizanswer(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_correct = models.BooleanField()
    selected_choice = models.ForeignKey(QuizzesChoice, models.DO_NOTHING, blank=True, null=True)
    quiz_attempt = models.ForeignKey('QuizzesQuizattempt', models.DO_NOTHING)
    question = models.ForeignKey(QuizzesQuestion, models.DO_NOTHING)
    file_answer = models.OneToOneField(QuizzesFileanswer, models.DO_NOTHING, blank=True, null=True)
    text_answer = models.TextField(blank=True, null=True)
    voice_answer = models.OneToOneField('QuizzesVoicerecording', models.DO_NOTHING, blank=True, null=True)
    points_earned = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'quizzes_quizanswer'


class QuizzesQuizattempt(models.Model):
    id = models.BigAutoField(primary_key=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    score = models.FloatField()
    result = models.CharField(max_length=15, blank=True, null=True)
    quiz = models.ForeignKey(QuizzesQuiz, models.DO_NOTHING)
    student = models.ForeignKey(AccountsUser, models.DO_NOTHING)
    completed = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'quizzes_quizattempt'


class QuizzesTextanswer(models.Model):
    id = models.BigAutoField(primary_key=True)
    text = models.TextField()
    submitted_at = models.DateTimeField()
    question = models.ForeignKey(QuizzesQuestion, models.DO_NOTHING)
    student = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'quizzes_textanswer'
        unique_together = (('question', 'student'),)


class QuizzesVoicerecording(models.Model):
    id = models.BigAutoField(primary_key=True)
    recording = models.CharField(max_length=100)
    duration = models.IntegerField(blank=True, null=True)
    submitted_at = models.DateTimeField()
    question = models.ForeignKey(QuizzesQuestion, models.DO_NOTHING)
    student = models.ForeignKey(AccountsUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'quizzes_voicerecording'
        unique_together = (('question', 'student'),)
