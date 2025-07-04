# Generated by Django 5.1.7 on 2025-04-19 13:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('meeting_link', models.URLField()),
                ('additional_info', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('students', models.ManyToManyField(limit_choices_to={'user_type': 'student'}, related_name='enrolled_events', to=settings.AUTH_USER_MODEL)),
                ('teacher', models.ForeignKey(limit_choices_to={'user_type': 'teacher'}, on_delete=django.db.models.deletion.CASCADE, related_name='created_events', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Timesheet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(limit_choices_to={'user_type': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='received_timesheets', to=settings.AUTH_USER_MODEL)),
                ('teacher', models.ForeignKey(limit_choices_to={'user_type': 'teacher'}, on_delete=django.db.models.deletion.CASCADE, related_name='sent_timesheets', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TimeOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.CharField(max_length=10)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_selected', models.BooleanField(default=False)),
                ('timesheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='time_options', to='events.timesheet')),
            ],
        ),
    ]
