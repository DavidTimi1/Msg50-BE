from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
import threading
import uuid

# Create your models here.

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=100, unique=True)
    public_key = models.TextField()  # Store the public key here
    profile_data = models.JSONField(default=dict)  # Storing profile settings as JSON

    bio = models.TextField(blank=True, null=True)
    dp = models.TextField(blank=True, null=True) # url to user's profile pic

    # Resolve reverse accessor conflicts
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',  # Avoid conflict with 'auth.User.groups'
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_set',  # Avoid conflict with 'auth.User.user_permissions'
        blank=True
    )

    def __str__(self):
        return self.username + ", " + self.bio


class Message(models.Model):
    msg_id = models.TextField(null=True)
    receiver_id = models.UUIDField()
    encrypted_message = models.JSONField()
    status = models.BooleanField(default=False)

    # status can be [ "s"-sent, "d"-delivered, "r"-read, "x"- deleted ]

    def __str__(self):
        return f"Message to #{self.receiver_id}"


class Media(models.Model):
    file = models.FileField(upload_to="encrypted_media/")
    metadata = models.JSONField(default=dict)  # Metadata for media files
    access_ids = models.ManyToManyField(User, related_name="media_access")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Media {self.uuid}"


class PrefetchLink(models.Model):
    url = models.URLField()
    preview_data = models.JSONField()  # Storing OpenGraph or metadata

    def __str__(self):
        return self.url
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Add your custom logic here
        self.after_initialization()


@receiver(post_save, sender=PrefetchLink)
def delete_after_timeout(sender, instance, **kwargs):
    def delete_instance():
        instance.delete()
        print(f"PrefetchLink object with URL {instance.url} has been deleted after timeout.")

    # Set the timer for 1 hour (3600 seconds)
    timer = threading.Timer(3600, delete_instance)
    timer.start()
