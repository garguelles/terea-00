"""User admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import User


@admin.register(User)
class UserModelAdmin(UserAdmin):
    ordering = ["email"]
    list_display = [
        "id",
        "email",
        "role",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
    ]
    list_filter = ["role", "is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        (
            "Personal information",
            {"fields": ["role", "first_name", "last_name", "phone_number"]},
        ),
        (
            "Permissions",
            {
                "fields": [
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ],
            },
        ),
        ("Important dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": [
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ],
            },
        ),
    ]
