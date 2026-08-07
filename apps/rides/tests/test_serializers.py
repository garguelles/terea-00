import math

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.rides.api.serializers import (
    RideEventSerializer,
    RideListQuerySerializer,
    RideListSerializer,
    RideSerializer,
)
from apps.rides.models import Ride, RideEvent


User = get_user_model()


class RideListQuerySerializerTests(TestCase):
    def test_accepts_and_normalizes_valid_query_parameters(self):
        serializer = RideListQuerySerializer(
            data={
                "status": Ride.Status.PICKUP,
                "rider_email": "RIDER@EXAMPLE.COM",
                "sort_by": "pickup_time",
                "sort_order": "desc",
                "page": "2",
                "page_size": "100",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["rider_email"],
            "rider@example.com",
        )
        self.assertEqual(serializer.validated_data["page"], 2)
        self.assertEqual(serializer.validated_data["page_size"], 100)

    def test_rejects_invalid_query_parameter_values(self):
        cases = {
            "status": {"status": "unknown"},
            "rider_email": {"rider_email": "not-an-email"},
            "sort_by": {"sort_by": "id", "sort_order": "asc"},
            "sort_order": {"sort_by": "pickup_time", "sort_order": "sideways"},
            "page": {"page": "0"},
            "page_size": {"page_size": "101"},
        }

        for field, data in cases.items():
            with self.subTest(field=field):
                serializer = RideListQuerySerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_requires_sort_field_and_direction_together(self):
        for data in ({"sort_by": "pickup_time"}, {"sort_order": "desc"}):
            with self.subTest(data=data):
                serializer = RideListQuerySerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn("non_field_errors", serializer.errors)


class RideSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rider = cls.create_user("rider@example.com", User.Role.RIDER)
        cls.driver = cls.create_user("driver@example.com", User.Role.DRIVER)

    @classmethod
    def create_user(cls, email, role):
        return User.objects.create_user(
            email=email,
            password="Strong-passphrase-917!",
            first_name="Test",
            last_name="User",
            phone_number="+15550000000",
            role=role,
        )

    def ride_data(self, **overrides):
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

    def test_ride_serializer_maps_assessment_fields(self):
        serializer = RideSerializer(data=self.ride_data())

        self.assertTrue(serializer.is_valid(), serializer.errors)
        ride = serializer.save()

        self.assertEqual(serializer.data["id_ride"], ride.pk)
        self.assertEqual(serializer.data["id_rider"], self.rider.pk)
        self.assertEqual(serializer.data["id_driver"], self.driver.pk)
        self.assertNotIn("ride_events", serializer.data)

    def test_ride_serializer_validates_choices_relationships_and_coordinates(self):
        serializer = RideSerializer(
            data=self.ride_data(
                status="unknown",
                id_rider=999999,
                pickup_latitude=91,
                dropoff_longitude=-181,
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            set(serializer.errors),
            {"status", "id_rider", "pickup_latitude", "dropoff_longitude"},
        )

    def test_ride_serializer_rejects_users_with_incompatible_roles(self):
        serializer = RideSerializer(
            data=self.ride_data(
                id_rider=self.driver.pk,
                id_driver=self.rider.pk,
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"id_rider", "id_driver"})

    def test_ride_serializer_rejects_non_finite_coordinates(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                serializer = RideSerializer(
                    data=self.ride_data(pickup_latitude=value)
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("pickup_latitude", serializer.errors)

    def test_ride_list_serializer_uses_prefetched_recent_events(self):
        serializer = RideSerializer(data=self.ride_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ride = serializer.save()
        event = RideEvent.objects.create(ride=ride, description="Recent")
        ride.todays_ride_events = [event]

        with self.assertNumQueries(0):
            data = RideListSerializer(ride).data

        self.assertEqual(data["id_rider"], self.rider.pk)
        self.assertEqual(data["id_driver"], self.driver.pk)
        self.assertEqual(
            data["todays_ride_events"],
            [
                {
                    "id_ride_event": event.pk,
                    "id_ride": ride.pk,
                    "description": "Recent",
                    "created_at": event.created_at.isoformat().replace(
                        "+00:00", "Z"
                    ),
                }
            ],
        )

    def test_ride_event_serializer_controls_timestamp(self):
        ride_serializer = RideSerializer(data=self.ride_data())
        self.assertTrue(ride_serializer.is_valid(), ride_serializer.errors)
        ride = ride_serializer.save()
        submitted_time = timezone.now().isoformat()

        serializer = RideEventSerializer(
            data={
                "id_ride": ride.pk,
                "description": "Status changed to pickup",
                "created_at": submitted_time,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()
        self.assertEqual(serializer.data["id_ride_event"], event.pk)
        self.assertEqual(serializer.data["id_ride"], ride.pk)
        self.assertIn("created_at", serializer.data)

    def test_ride_event_serializer_validates_ride_and_description(self):
        serializer = RideEventSerializer(
            data={"id_ride": 999999, "description": ""}
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"id_ride", "description"})
