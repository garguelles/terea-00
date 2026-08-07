from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.rides.models import Ride, RideEvent
from apps.rides.selectors import ride_list_queryset


User = get_user_model()


class RideListSelectorTests(TestCase):
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

    def create_ride(self):
        return Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_latitude=37.7749,
            pickup_longitude=-122.4194,
            dropoff_latitude=37.6213,
            dropoff_longitude=-122.3790,
            pickup_time=timezone.now(),
        )

    def create_event(self, *, ride, description, created_at):
        event = RideEvent.objects.create(ride=ride, description=description)
        RideEvent.objects.filter(pk=event.pk).update(created_at=created_at)
        event.refresh_from_db()
        return event

    def test_list_query_joins_users_and_prefetches_only_recent_events(self):
        now = timezone.now()
        ride = self.create_ride()
        inside = self.create_event(
            ride=ride,
            description="Inside window",
            created_at=now - timedelta(hours=24) + timedelta(seconds=1),
        )
        boundary = self.create_event(
            ride=ride,
            description="At boundary",
            created_at=now - timedelta(hours=24),
        )
        self.create_event(
            ride=ride,
            description="Outside window",
            created_at=now - timedelta(hours=24) - timedelta(seconds=1),
        )
        self.create_event(
            ride=ride,
            description="Future event",
            created_at=now + timedelta(seconds=1),
        )

        with patch("apps.rides.selectors.timezone.now", return_value=now):
            with CaptureQueriesContext(connection) as queries:
                rides = list(ride_list_queryset())

        self.assertEqual(len(queries), 2)
        self.assertEqual(rides, [ride])
        selected_ride = rides[0]
        self.assertEqual(
            [event.pk for event in selected_ride.todays_ride_events],
            [inside.pk, boundary.pk],
        )
        self.assertNotIn(
            "ride_events",
            selected_ride._prefetched_objects_cache,
        )

        with self.assertNumQueries(0):
            self.assertEqual(selected_ride.rider, self.rider)
            self.assertEqual(selected_ride.driver, self.driver)
            list(selected_ride.todays_ride_events)

    def test_recent_events_use_id_as_a_deterministic_time_tiebreaker(self):
        now = timezone.now()
        ride = self.create_ride()
        first = self.create_event(
            ride=ride,
            description="First",
            created_at=now - timedelta(hours=1),
        )
        second = self.create_event(
            ride=ride,
            description="Second",
            created_at=now - timedelta(hours=1),
        )

        with patch("apps.rides.selectors.timezone.now", return_value=now):
            selected_ride = ride_list_queryset().get()

        self.assertEqual(
            [event.pk for event in selected_ride.todays_ride_events],
            [second.pk, first.pk],
        )
