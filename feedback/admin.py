from django.contrib import admin
from .models import Feedback

# Register your models here.
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    search_fields = ('message', 'project_name')
    list_filter = ('created_at', 'project_name', 'subscribed')
