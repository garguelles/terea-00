"""User queries and read use cases."""

from apps.users.models import User


def users_queryset():
    return User.objects.order_by("id")
