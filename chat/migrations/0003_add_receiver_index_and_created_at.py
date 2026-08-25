"""Add index on receiver_id and created_at field to Message model

Generated manually.
"""
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_user_is_guest_user_joined'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='receiver_id',
            field=models.UUIDField(db_index=True),
        ),
    ]
