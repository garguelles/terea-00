from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.api.serializers import UserSerializer


User = get_user_model()


class UserSerializerTests(TestCase):
    def user_data(self, **overrides):
        data = {
            "role": User.Role.RIDER,
            "first_name": "Test",
            "last_name": "Rider",
            "email": "Rider@Example.COM",
            "phone_number": "+15550000001",
            "password": "Strong-passphrase-917!",
        }
        data.update(overrides)
        return data

    def test_create_hashes_password_and_never_serializes_it(self):
        serializer = UserSerializer(data=self.user_data())

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.email, "rider@example.com")
        self.assertTrue(user.check_password("Strong-passphrase-917!"))
        self.assertNotIn("password", serializer.data)
        self.assertEqual(serializer.data["id_user"], user.pk)

    def test_create_requires_a_valid_password(self):
        missing = self.user_data()
        missing.pop("password")

        missing_serializer = UserSerializer(data=missing)
        weak_serializer = UserSerializer(
            data=self.user_data(email="other@example.com", password="password")
        )

        self.assertFalse(missing_serializer.is_valid())
        self.assertIn("password", missing_serializer.errors)
        self.assertFalse(weak_serializer.is_valid())
        self.assertIn("password", weak_serializer.errors)

    def test_email_uniqueness_is_case_insensitive(self):
        User.objects.create_user(
            email="rider@example.com",
            password="Existing-passphrase-317!",
            first_name="Existing",
            last_name="Rider",
            phone_number="+15550000002",
        )

        serializer = UserSerializer(data=self.user_data(email="RIDER@example.com"))

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_update_preserves_or_rehashes_password_as_requested(self):
        user = User.objects.create_user(
            email="rider@example.com",
            password="Original-passphrase-317!",
            first_name="Original",
            last_name="Rider",
            phone_number="+15550000003",
        )

        serializer = UserSerializer(
            user,
            data={"first_name": "Updated"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("Original-passphrase-317!"))

        serializer = UserSerializer(
            user,
            data={"password": "Changed-passphrase-846!"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("Changed-passphrase-846!"))
        self.assertNotIn("password", serializer.data)
