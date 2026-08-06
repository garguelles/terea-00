"""User API authorization policies."""

from rest_framework.permissions import BasePermission

from apps.users.models import User


class IsActiveAdminRole(BasePermission):
    """Allow API access only to active users with the application admin role."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and user.role == User.Role.ADMIN
        )
