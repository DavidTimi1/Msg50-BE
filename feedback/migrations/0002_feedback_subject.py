# Generated by Django 5.1.4 on 2025-05-13 22:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='subject',
            field=models.CharField(default='Comment', max_length=255),
        ),
    ]
