from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register the custom User model using UserAdmin for authentication fields
@admin.register(User)

class CustomUserAdmin(UserAdmin):
    # Add custom fields (if any) to the User admin
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('bio',),  # Example of a custom field
        }),
    )

    # Configure list display in the admin panel
    list_display = ('username', 'email', 'is_staff', 'is_active')

    # Allow filtering by these fields
    list_filter = ('is_staff', 'is_active', 'is_superuser')
