import base64

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.users.api.permissions import IsActiveAdminRole


User = get_user_model()


class ProtectedView(APIView):
    def get(self, request):
        return Response({"detail": "allowed"})


urlpatterns = [path("protected/", ProtectedView.as_view())]


@override_settings(ROOT_URLCONF=__name__)
class AdminRolePermissionTests(TestCase):
    password = "test-password"

    @classmethod
    def setUpTestData(cls):
        cls.admin = cls.create_user(
            email="admin@example.com",
            role=User.Role.ADMIN,
        )
        cls.rider = cls.create_user(
            email="rider@example.com",
            role=User.Role.RIDER,
        )
        cls.staff_rider = cls.create_user(
            email="staff-rider@example.com",
            role=User.Role.RIDER,
            is_staff=True,
        )
        cls.inactive_admin = cls.create_user(
            email="inactive-admin@example.com",
            role=User.Role.ADMIN,
            is_active=False,
        )

    @classmethod
    def create_user(cls, *, email, role, **extra_fields):
        return User.objects.create_user(
            email=email,
            password=cls.password,
            first_name="API",
            last_name="User",
            phone_number="+15550000000",
            role=role,
            **extra_fields,
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate(self, *, email, password=None):
        credentials = f"{email}:{password or self.password}".encode()
        token = base64.b64encode(credentials).decode()
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {token}")

    def test_shared_drf_defaults_use_basic_authentication_and_admin_role(self):
        self.assertEqual(
            api_settings.DEFAULT_AUTHENTICATION_CLASSES,
            [BasicAuthentication],
        )
        self.assertEqual(
            api_settings.DEFAULT_PERMISSION_CLASSES,
            [IsActiveAdminRole],
        )
        self.assertTrue(issubclass(IsActiveAdminRole, BasePermission))

    def test_anonymous_request_returns_unauthorized(self):
        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["WWW-Authenticate"], 'Basic realm="api"')

    def test_invalid_credentials_return_unauthorized(self):
        self.authenticate(email=self.admin.email, password="incorrect-password")

        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 401)

    def test_inactive_admin_returns_unauthorized(self):
        self.authenticate(email=self.inactive_admin.email)

        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_non_admin_returns_forbidden(self):
        self.authenticate(email=self.rider.email)

        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 403)

    def test_django_staff_status_does_not_replace_admin_role(self):
        self.authenticate(email=self.staff_rider.email)

        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 403)

    def test_active_role_admin_is_allowed_without_staff_status(self):
        self.authenticate(email=self.admin.email)

        response = self.client.get("/protected/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"detail": "allowed"})
        self.assertFalse(self.admin.is_staff)
