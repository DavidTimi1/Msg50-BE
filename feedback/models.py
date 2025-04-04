from django.db import models

# Create your models here.
class Feedback(models.Model):
    project_name = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255, default='Anonymous')
    email = models.EmailField(null=True, blank=True, help_text="Optional. Only if you want a response.")
    message = models.TextField()
    subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    extraData = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.project_name} - {self.user_name}"