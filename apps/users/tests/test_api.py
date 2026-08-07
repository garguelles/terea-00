from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.rides.models import Ride


User = get_user_model()


class UserApiTests(TestCase):
    password = "Admin-passphrase-917!"

    @classmethod
    def setUpTestData(cls):
        cls.admin = cls.create_user("admin@example.com", User.Role.ADMIN)
        cls.rider = cls.create_user("rider@example.com", User.Role.RIDER)

    @classmethod
    def create_user(cls, email, role=User.Role.RIDER, **overrides):
        fields = {
            "password": cls.password,
            "first_name": "API",
            "last_name": "User",
            "phone_number": "+15550000000",
            "role": role,
        }
        fields.update(overrides)
        return User.objects.create_user(email=email, **fields)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def user_payload(self, **overrides):
        data = {
            "role": User.Role.DRIVER,
            "first_name": "New",
            "last_name": "Driver",
            "email": "new-driver@example.com",
            "phone_number": "+15550000009",
            "password": "Driver-passphrase-917!",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_retrieve_update_and_delete_a_user(self):
        create_response = self.client.post(
            reverse("user-list"), self.user_payload(), format="json"
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertNotIn("password", create_response.json())
        user = User.objects.get(pk=create_response.json()["id_user"])
        self.assertTrue(user.check_password("Driver-passphrase-917!"))

        detail_url = reverse("user-detail", args=[user.pk])
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        update = self.user_payload(first_name="Put Updated")
        update.pop("password")
        put_response = self.client.put(detail_url, update, format="json")
        self.assertEqual(put_response.status_code, 200)

        patch_response = self.client.patch(
            detail_url, {"last_name": "Patched"}, format="json"
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["last_name"], "Patched")

        self.assertEqual(self.client.delete(detail_url).status_code, 204)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_list_is_paginated_and_deterministically_ordered(self):
        for index in range(20):
            self.create_user(f"user-{index}@example.com")

        response = self.client.get(reverse("user-list"), {"page_size": 5})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 22)
        self.assertEqual(len(body["results"]), 5)
        ids = [item["id_user"] for item in body["results"]]
        self.assertEqual(ids, sorted(ids))
        self.assertTrue(all("password" not in item for item in body["results"]))

    def test_invalid_input_and_missing_users_return_controlled_errors(self):
        invalid = self.client.post(
            reverse("user-list"),
            self.user_payload(role="unknown", email="invalid"),
            format="json",
        )
        missing = self.client.get(reverse("user-detail", args=[999999]))

        self.assertEqual(invalid.status_code, 400)
        self.assertIn("role", invalid.json())
        self.assertIn("email", invalid.json())
        self.assertEqual(missing.status_code, 404)

    def test_deleting_a_user_assigned_to_a_ride_returns_conflict(self):
        Ride.objects.create(
            rider=self.rider,
            driver=self.admin,
            pickup_latitude=10,
            pickup_longitude=20,
            dropoff_latitude=30,
            dropoff_longitude=40,
            pickup_time=timezone.now(),
        )

        response = self.client.delete(reverse("user-detail", args=[self.rider.pk]))

        self.assertEqual(response.status_code, 409)
        self.assertTrue(User.objects.filter(pk=self.rider.pk).exists())
        self.assertEqual(
            response.json(),
            {"detail": "This user is assigned to one or more rides."},
        )

    def test_endpoint_requires_an_active_admin_role(self):
        self.client.force_authenticate(user=None)
        anonymous = self.client.get(reverse("user-list"))
        self.client.force_authenticate(self.rider)
        rider = self.client.get(reverse("user-list"))

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(rider.status_code, 403)
