from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.test import TestCase


User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_uses_email_identity_and_hashes_password(self):
        user = User.objects.create_user(
            email="Rider@Example.COM",
            password="test-password",
            first_name="Rita",
            last_name="Rider",
            phone_number="+15550000001",
        )

        self.assertEqual(user.email, "rider@example.com")
        self.assertEqual(user.role, User.Role.RIDER)
        self.assertNotEqual(user.password, "test-password")
        self.assertTrue(user.check_password("test-password"))
        self.assertEqual(str(user), "rider@example.com")

    def test_authentication_accepts_email_in_different_case(self):
        user = User.objects.create_user(
            email="admin@example.com",
            password="test-password",
            first_name="Ada",
            last_name="Admin",
            phone_number="+15550000002",
            role=User.Role.ADMIN,
        )
        User.objects.filter(pk=user.pk).update(email="Admin@Example.COM")

        authenticated_user = authenticate(
            email="admin@example.com",
            password="test-password",
        )

        self.assertEqual(authenticated_user, user)

    def test_direct_model_save_normalizes_email(self):
        user = User(
            email="Direct@Example.COM",
            first_name="Direct",
            last_name="Save",
            phone_number="+15550000008",
        )
        user.set_password("test-password")
        user.save()

        self.assertEqual(user.email, "direct@example.com")

    def test_create_superuser_sets_django_and_application_admin_flags(self):
        user = User.objects.create_superuser(
            email="root@example.com",
            password="test-password",
            first_name="Root",
            last_name="Admin",
            phone_number="+15550000003",
        )

        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_incompatible_values(self):
        invalid_values = [
            {"is_staff": False},
            {"is_superuser": False},
            {"role": User.Role.DRIVER},
        ]

        for values in invalid_values:
            with self.subTest(values=values), self.assertRaises(ValueError):
                User.objects.create_superuser(
                    email=f"{len(values)}-{next(iter(values))}@example.com",
                    password="test-password",
                    first_name="Invalid",
                    last_name="Admin",
                    phone_number="+15550000004",
                    **values,
                )

    def test_email_is_unique_case_insensitively_when_save_is_bypassed(self):
        User.objects.bulk_create(
            [
                User(
                    email="Unique@Example.COM",
                    first_name="First",
                    last_name="User",
                    phone_number="+15550000005",
                ),
            ]
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create(
                [
                    User(
                        email="unique@example.com",
                        first_name="Second",
                        last_name="User",
                        phone_number="+15550000006",
                    ),
                ]
            )

    def test_database_rejects_unknown_role(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="unknown-role@example.com",
                password="test-password",
                first_name="Unknown",
                last_name="Role",
                phone_number="+15550000007",
                role="unknown",
            )

    def test_assessment_primary_key_column_and_role_choices(self):
        self.assertEqual(User._meta.pk.column, "id_user")
        self.assertEqual(
            set(User.Role.values),
            {"admin", "rider", "driver"},
        )
        with self.assertRaises(FieldDoesNotExist):
            User._meta.get_field("username")
