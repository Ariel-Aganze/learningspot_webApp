# Generated by Django 5.1.7 on 2025-05-20 22:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quizzes', '0003_quiz_is_placement_test'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quizattempt',
            name='result',
            field=models.CharField(blank=True, choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced'), ('failed', 'Failed'), ('passed', 'Passed')], max_length=15, null=True),
        ),
    ]
