# Generated by Django 5.1.7 on 2025-04-23 11:57

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quizzes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='choice',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='choice_images/'),
        ),
        migrations.AddField(
            model_name='choice',
            name='match_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='question',
            name='audio',
            field=models.FileField(blank=True, null=True, upload_to='question_audio/'),
        ),
        migrations.AddField(
            model_name='question',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='question_images/'),
        ),
        migrations.AddField(
            model_name='question',
            name='question_type',
            field=models.CharField(choices=[('multiple_choice', 'Multiple Choice (Single Select)'), ('multi_select', 'Multiple Choice (Multi Select)'), ('true_false', 'True/False'), ('dropdown', 'Dropdown'), ('star_rating', 'Star Rating'), ('likert_scale', 'Likert Scale'), ('matrix', 'Matrix Questions'), ('image_choice', 'Image Choice'), ('image_rating', 'Image Rating'), ('short_answer', 'Short Answer'), ('long_answer', 'Long Answer'), ('file_upload', 'File Upload'), ('voice_record', 'Voice Recording'), ('matching', 'Matching')], default='multiple_choice', max_length=20),
        ),
        migrations.AlterField(
            model_name='quizanswer',
            name='selected_choice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='quizzes.choice'),
        ),
        migrations.CreateModel(
            name='FileAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='student_uploads/')),
                ('file_type', models.CharField(blank=True, max_length=50)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='file_answers', to='quizzes.question')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('question', 'student')},
            },
        ),
        migrations.AddField(
            model_name='quizanswer',
            name='file_answer',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='quizzes.fileanswer'),
        ),
        migrations.CreateModel(
            name='TextAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='text_answers', to='quizzes.question')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('question', 'student')},
            },
        ),
        migrations.AddField(
            model_name='quizanswer',
            name='text_answer',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='quizzes.textanswer'),
        ),
        migrations.CreateModel(
            name='VoiceRecording',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('audio_file', models.FileField(upload_to='voice_recordings/')),
                ('duration', models.PositiveIntegerField(default=0, help_text='Duration in seconds')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='voice_recordings', to='quizzes.question')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('question', 'student')},
            },
        ),
        migrations.AddField(
            model_name='quizanswer',
            name='voice_recording',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='quizzes.voicerecording'),
        ),
    ]
