from django.db import models

# Create your models here.
class Feedback(models.Model):
    project_name = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.project_name} - {self.user_name}"