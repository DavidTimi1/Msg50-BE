
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Deletes guest users older than a week.'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        one_week_ago = timezone.now() - timedelta(weeks=1)

        User.objects.filter(is_guest__isnull=True, username__startswith="guest_").update(is_guest=True)

        old_guests = User.objects.filter(is_guest=True, joined__lt=one_week_ago)

        count = old_guests.count()

        if count > 0:
            old_guests.delete()
            
            self.stdout.write(self.style.SUCCESS('All old guests deleted!.'))

        else:
            self.stdout.write(self.style.SUCCESS('No guest users found!.'))