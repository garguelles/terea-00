from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.rides.models import Ride, RideEvent


User = get_user_model()


class RideApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = cls.create_user("admin@example.com", User.Role.ADMIN)
        cls.rider = cls.create_user("rider@example.com", User.Role.RIDER)
        cls.driver = cls.create_user("driver@example.com", User.Role.DRIVER)

    @classmethod
    def create_user(cls, email, role):
        return User.objects.create_user(
            email=email,
            password="Strong-passphrase-917!",
            first_name="API",
            last_name="User",
            phone_number="+15550000000",
            role=role,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def ride_payload(self, **overrides):
        data = {
            "status": Ride.Status.EN_ROUTE,
            "id_rider": self.rider.pk,
            "id_driver": self.driver.pk,
            "pickup_latitude": 10.5,
            "pickup_longitude": 20.5,
            "dropoff_latitude": 30.5,
            "dropoff_longitude": 40.5,
            "pickup_time": timezone.now().isoformat(),
        }
        data.update(overrides)
        return data

    def create_ride(self, **overrides):
        data = {
            "rider": self.rider,
            "driver": self.driver,
            "pickup_latitude": 10.5,
            "pickup_longitude": 20.5,
            "dropoff_latitude": 30.5,
            "dropoff_longitude": 40.5,
            "pickup_time": timezone.now(),
        }
        data.update(overrides)
        return Ride.objects.create(**data)

    def test_admin_can_create_retrieve_update_and_delete_a_ride(self):
        created = self.client.post(
            reverse("ride-list"), self.ride_payload(), format="json"
        )
        self.assertEqual(created.status_code, 201)
        self.assertNotIn("ride_events", created.json())

        ride_id = created.json()["id_ride"]
        detail_url = reverse("ride-detail", args=[ride_id])
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        updated_data = self.ride_payload(status=Ride.Status.PICKUP)
        put_response = self.client.put(detail_url, updated_data, format="json")
        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json()["status"], Ride.Status.PICKUP)

        patch_response = self.client.patch(
            detail_url,
            {"status": Ride.Status.DROPOFF},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["status"], Ride.Status.DROPOFF)

        self.assertEqual(self.client.delete(detail_url).status_code, 204)
        self.assertFalse(Ride.objects.filter(pk=ride_id).exists())

    def test_admin_can_crud_ride_events(self):
        ride = self.create_ride()
        created = self.client.post(
            reverse("ride-event-list"),
            {"id_ride": ride.pk, "description": "Created"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertIn("created_at", created.json())

        event_id = created.json()["id_ride_event"]
        detail_url = reverse("ride-event-detail", args=[event_id])
        self.assertEqual(self.client.get(detail_url).status_code, 200)

        put_response = self.client.put(
            detail_url,
            {"id_ride": ride.pk, "description": "Updated"},
            format="json",
        )
        self.assertEqual(put_response.status_code, 200)

        patch_response = self.client.patch(
            detail_url, {"description": "Patched"}, format="json"
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["description"], "Patched")

        self.assertEqual(self.client.delete(detail_url).status_code, 204)
        self.assertFalse(RideEvent.objects.filter(pk=event_id).exists())

    def test_lists_are_paginated_and_missing_resources_return_not_found(self):
        for _ in range(3):
            self.create_ride()

        rides = self.client.get(reverse("ride-list"), {"page_size": 2})
        missing = self.client.get(reverse("ride-detail", args=[999999]))

        self.assertEqual(rides.status_code, 200)
        self.assertEqual(rides.json()["count"], 3)
        self.assertEqual(len(rides.json()["results"]), 2)
        ids = [item["id_ride"] for item in rides.json()["results"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(missing.status_code, 404)

    def test_ride_list_returns_only_events_from_the_last_24_hours(self):
        now = timezone.now()
        ride = self.create_ride()
        recent = RideEvent.objects.create(ride=ride, description="Recent")
        old = RideEvent.objects.create(ride=ride, description="Old")
        future = RideEvent.objects.create(ride=ride, description="Future")
        RideEvent.objects.filter(pk=recent.pk).update(
            created_at=now - timedelta(hours=24) + timedelta(seconds=1)
        )
        RideEvent.objects.filter(pk=old.pk).update(
            created_at=now - timedelta(hours=24) - timedelta(seconds=1)
        )
        RideEvent.objects.filter(pk=future.pk).update(
            created_at=now + timedelta(seconds=1)
        )

        with patch("apps.rides.selectors.timezone.now", return_value=now):
            response = self.client.get(reverse("ride-list"))

        self.assertEqual(response.status_code, 200)
        listed_ride = response.json()["results"][0]
        self.assertEqual(listed_ride["id_rider"], self.rider.pk)
        self.assertEqual(listed_ride["id_driver"], self.driver.pk)
        self.assertEqual(
            [event["id_ride_event"] for event in listed_ride["todays_ride_events"]],
            [recent.pk],
        )

    def test_paginated_ride_list_uses_three_queries(self):
        now = timezone.now()
        for index in range(4):
            ride = self.create_ride()
            recent = RideEvent.objects.create(
                ride=ride,
                description=f"Recent {index}",
            )
            old = RideEvent.objects.create(ride=ride, description=f"Old {index}")
            RideEvent.objects.filter(pk=recent.pk).update(
                created_at=now - timedelta(hours=1)
            )
            RideEvent.objects.filter(pk=old.pk).update(
                created_at=now - timedelta(days=2)
            )

        with patch("apps.rides.selectors.timezone.now", return_value=now):
            with self.assertNumQueries(3):
                response = self.client.get(
                    reverse("ride-list"),
                    {"page_size": 2},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 4)
        self.assertEqual(len(response.json()["results"]), 2)
        self.assertTrue(
            all(
                len(ride["todays_ride_events"]) == 1
                for ride in response.json()["results"]
            )
        )

    def test_ride_list_filters_by_status_and_rider_email(self):
        other_rider = self.create_user("other-rider@example.com", User.Role.RIDER)
        matching = self.create_ride(status=Ride.Status.PICKUP)
        self.create_ride(status=Ride.Status.DROPOFF)
        self.create_ride(rider=other_rider, status=Ride.Status.PICKUP)

        response = self.client.get(
            reverse("ride-list"),
            {
                "status": Ride.Status.PICKUP,
                "rider_email": "RIDER@EXAMPLE.COM",
            },
        )
        no_matches = self.client.get(
            reverse("ride-list"),
            {"rider_email": "missing@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id_ride"], matching.pk)
        self.assertEqual(no_matches.status_code, 200)
        self.assertEqual(no_matches.json()["count"], 0)
        self.assertEqual(no_matches.json()["results"], [])

    def test_pickup_time_sorting_is_stable_across_pages(self):
        now = timezone.now()
        earlier = self.create_ride(pickup_time=now - timedelta(hours=1))
        tied_first = self.create_ride(pickup_time=now)
        tied_second = self.create_ride(pickup_time=now)

        ascending = self.client.get(
            reverse("ride-list"),
            {
                "sort_by": "pickup_time",
                "sort_order": "asc",
                "page_size": 2,
            },
        )
        descending_page_one = self.client.get(
            reverse("ride-list"),
            {
                "sort_by": "pickup_time",
                "sort_order": "desc",
                "page_size": 2,
            },
        )
        descending_page_two = self.client.get(
            reverse("ride-list"),
            {
                "sort_by": "pickup_time",
                "sort_order": "desc",
                "page_size": 2,
                "page": 2,
            },
        )

        self.assertEqual(
            [ride["id_ride"] for ride in ascending.json()["results"]],
            [earlier.pk, tied_first.pk],
        )
        self.assertEqual(
            [ride["id_ride"] for ride in descending_page_one.json()["results"]],
            [tied_second.pk, tied_first.pk],
        )
        self.assertEqual(
            [ride["id_ride"] for ride in descending_page_two.json()["results"]],
            [earlier.pk],
        )
        self.assertEqual(descending_page_one.json()["count"], 3)
        self.assertIsNotNone(descending_page_one.json()["next"])
        self.assertIsNotNone(descending_page_two.json()["previous"])

    def test_ride_list_allows_page_size_up_to_one_hundred(self):
        Ride.objects.bulk_create(
            [
                Ride(
                    rider=self.rider,
                    driver=self.driver,
                    pickup_latitude=10.5,
                    pickup_longitude=20.5,
                    dropoff_latitude=30.5,
                    dropoff_longitude=40.5,
                    pickup_time=timezone.now(),
                )
                for _ in range(101)
            ]
        )

        response = self.client.get(reverse("ride-list"), {"page_size": 100})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 101)
        self.assertEqual(len(response.json()["results"]), 100)
        self.assertIsNotNone(response.json()["next"])

    def test_ride_list_rejects_invalid_query_parameters(self):
        cases = (
            {"status": "unknown"},
            {"rider_email": "not-an-email"},
            {"sort_by": "id", "sort_order": "asc"},
            {"sort_by": "pickup_time", "sort_order": "sideways"},
            {"sort_by": "pickup_time"},
            {"sort_order": "desc"},
            {"page": 0},
            {"page_size": 101},
        )

        for params in cases:
            with self.subTest(params=params):
                response = self.client.get(reverse("ride-list"), params)
                self.assertEqual(response.status_code, 400)

    def test_filtered_and_sorted_ride_page_still_uses_three_queries(self):
        now = timezone.now()
        for index in range(3):
            ride = self.create_ride(
                status=Ride.Status.PICKUP,
                pickup_time=now + timedelta(minutes=index),
            )
            RideEvent.objects.create(ride=ride, description=f"Recent {index}")

        with patch("apps.rides.selectors.timezone.now", return_value=now):
            with self.assertNumQueries(3):
                response = self.client.get(
                    reverse("ride-list"),
                    {
                        "status": Ride.Status.PICKUP,
                        "rider_email": self.rider.email,
                        "sort_by": "pickup_time",
                        "sort_order": "desc",
                        "page_size": 2,
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(len(response.json()["results"]), 2)

    def test_invalid_ride_and_event_inputs_return_bad_request(self):
        invalid_ride = self.client.post(
            reverse("ride-list"),
            self.ride_payload(status="unknown", id_driver=999999),
            format="json",
        )
        invalid_event = self.client.post(
            reverse("ride-event-list"),
            {"id_ride": 999999, "description": ""},
            format="json",
        )

        self.assertEqual(invalid_ride.status_code, 400)
        self.assertIn("status", invalid_ride.json())
        self.assertIn("id_driver", invalid_ride.json())
        self.assertEqual(invalid_event.status_code, 400)

    def test_ride_assignments_require_matching_user_roles(self):
        response = self.client.post(
            reverse("ride-list"),
            self.ride_payload(
                id_rider=self.driver.pk,
                id_driver=self.rider.pk,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"id_rider", "id_driver"})

    def test_deleting_a_ride_with_events_returns_conflict(self):
        ride = self.create_ride()
        RideEvent.objects.create(ride=ride, description="Created")

        response = self.client.delete(reverse("ride-detail", args=[ride.pk]))

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Ride.objects.filter(pk=ride.pk).exists())
        self.assertEqual(
            response.json(),
            {"detail": "This ride has one or more ride events."},
        )

    def test_ride_endpoints_require_an_active_admin_role(self):
        for route in ("ride-list", "ride-event-list"):
            with self.subTest(route=route):
                self.client.force_authenticate(user=None)
                anonymous = self.client.get(reverse(route))
                self.client.force_authenticate(self.rider)
                rider = self.client.get(reverse(route))

                self.assertEqual(anonymous.status_code, 401)
                self.assertEqual(rider.status_code, 403)
