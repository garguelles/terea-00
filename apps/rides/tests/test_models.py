from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.rides.models import Ride, RideEvent


User = get_user_model()


class RideTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.rider = User.objects.create_user(
            email="rider@example.com",
            password="test-password",
            first_name="Rita",
            last_name="Rider",
            phone_number="+15550000011",
            role=User.Role.RIDER,
        )
        cls.driver = User.objects.create_user(
            email="driver@example.com",
            password="test-password",
            first_name="Drew",
            last_name="Driver",
            phone_number="+15550000012",
            role=User.Role.DRIVER,
        )

    def create_ride(self, **overrides):
        values = {
            "rider": self.rider,
            "driver": self.driver,
            "pickup_latitude": 37.7749,
            "pickup_longitude": -122.4194,
            "dropoff_latitude": 37.6213,
            "dropoff_longitude": -122.3790,
            "pickup_time": timezone.now(),
        }
        values.update(overrides)
        return Ride.objects.create(**values)


class RideModelTests(RideTestDataMixin, TestCase):

    def test_ride_defaults_relationships_and_reverse_names(self):
        ride = self.create_ride()

        self.assertEqual(ride.status, Ride.Status.EN_ROUTE)
        self.assertEqual(ride.rider, self.rider)
        self.assertEqual(ride.driver, self.driver)
        self.assertEqual(list(self.rider.rides_as_rider.all()), [ride])
        self.assertEqual(list(self.driver.rides_as_driver.all()), [ride])
        self.assertEqual(str(ride), f"Ride {ride.pk} (en-route)")

    def test_assessment_database_column_names(self):
        self.assertEqual(Ride._meta.pk.column, "id_ride")
        self.assertEqual(Ride._meta.get_field("rider").column, "id_rider")
        self.assertEqual(Ride._meta.get_field("driver").column, "id_driver")
        self.assertEqual(RideEvent._meta.pk.column, "id_ride_event")
        self.assertEqual(RideEvent._meta.get_field("ride").column, "id_ride")

    def test_status_choices_and_database_constraint(self):
        self.assertEqual(
            set(Ride.Status.values),
            {"en-route", "pickup", "dropoff"},
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_ride(status="unknown")

    def test_coordinate_boundaries_are_accepted(self):
        ride = self.create_ride(
            pickup_latitude=-90,
            pickup_longitude=-180,
            dropoff_latitude=90,
            dropoff_longitude=180,
        )

        self.assertIsNotNone(ride.pk)

    def test_database_rejects_out_of_range_coordinates(self):
        invalid_coordinates = [
            ("pickup_latitude", -90.1),
            ("pickup_latitude", 90.1),
            ("pickup_longitude", -180.1),
            ("pickup_longitude", 180.1),
            ("dropoff_latitude", -90.1),
            ("dropoff_latitude", 90.1),
            ("dropoff_longitude", -180.1),
            ("dropoff_longitude", 180.1),
            ("pickup_latitude", float("nan")),
            ("pickup_longitude", float("inf")),
            ("dropoff_latitude", float("-inf")),
        ]

        for field, value in invalid_coordinates:
            with self.subTest(field=field, value=value):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.create_ride(**{field: value})

    def test_user_deletion_is_protected_when_referenced_by_a_ride(self):
        self.create_ride()

        with self.assertRaises(ProtectedError):
            self.rider.delete()
        with self.assertRaises(ProtectedError):
            self.driver.delete()

    def test_ride_indexes_support_list_query_patterns(self):
        indexes = {index.name: index.fields for index in Ride._meta.indexes}

        self.assertEqual(
            indexes["ride_pickup_time_id_idx"],
            ["pickup_time", "id"],
        )
        self.assertEqual(
            indexes["ride_status_pickup_idx"],
            ["status", "pickup_time", "id"],
        )


class RideEventModelTests(RideTestDataMixin, TestCase):
    def test_event_records_timestamp_and_reverse_relationship(self):
        ride = self.create_ride()
        event = RideEvent.objects.create(
            ride=ride,
            description="Status changed to pickup",
        )

        self.assertIsNotNone(event.created_at)
        self.assertEqual(list(ride.ride_events.all()), [event])
        self.assertEqual(str(event), f"Ride {ride.pk}: Status changed to pickup")

    def test_ride_deletion_is_protected_when_events_exist(self):
        ride = self.create_ride()
        RideEvent.objects.create(
            ride=ride,
            description="Status changed to pickup",
        )

        with self.assertRaises(ProtectedError):
            ride.delete()

    def test_event_index_supports_recent_events_by_ride(self):
        indexes = {index.name: index.fields for index in RideEvent._meta.indexes}

        self.assertEqual(
            indexes["event_ride_created_idx"],
            ["ride", "-created_at", "-id"],
        )
