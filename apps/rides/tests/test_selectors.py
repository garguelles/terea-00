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

    def create_ride(self, **overrides):
        data = {
            "rider": self.rider,
            "driver": self.driver,
            "pickup_latitude": 37.7749,
            "pickup_longitude": -122.4194,
            "dropoff_latitude": 37.6213,
            "dropoff_longitude": -122.3790,
            "pickup_time": timezone.now(),
        }
        data.update(overrides)
        return Ride.objects.create(**data)

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

    def test_query_count_is_constant_and_prefetch_sql_filters_old_events(self):
        now = timezone.now()
        rides = [self.create_ride() for _ in range(12)]
        for index, ride in enumerate(rides):
            self.create_event(
                ride=ride,
                description=f"Recent {index}",
                created_at=now - timedelta(hours=1),
            )
            self.create_event(
                ride=ride,
                description=f"Old {index}",
                created_at=now - timedelta(days=2),
            )

        with patch("apps.rides.selectors.timezone.now", return_value=now):
            with CaptureQueriesContext(connection) as queries:
                selected_rides = list(ride_list_queryset())

        self.assertEqual(len(queries), 2)
        self.assertEqual(len(selected_rides), len(rides))
        self.assertTrue(
            all(
                [event.description for event in ride.todays_ride_events]
                == [f"Recent {index}"]
                for index, ride in enumerate(selected_rides)
            )
        )
        self.assertTrue(
            all(
                "ride_events" not in ride._prefetched_objects_cache
                for ride in selected_rides
            )
        )

        event_query = queries[1]["sql"].upper()
        self.assertIn('"RIDES_RIDEEVENT"."CREATED_AT" >=', event_query)
        self.assertIn('"RIDES_RIDEEVENT"."CREATED_AT" <=', event_query)
        self.assertIn('"RIDES_RIDEEVENT"."ID_RIDE" IN', event_query)

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

    def test_filters_by_status_and_rider_email_independently_and_together(self):
        other_rider = User.objects.create_user(
            email="other-rider@example.com",
            password="test-password",
            first_name="Other",
            last_name="Rider",
            phone_number="+15550000013",
            role=User.Role.RIDER,
        )
        matching = self.create_ride(status=Ride.Status.PICKUP)
        self.create_ride(status=Ride.Status.DROPOFF)
        self.create_ride(rider=other_rider, status=Ride.Status.PICKUP)

        self.assertEqual(
            list(ride_list_queryset(status=Ride.Status.DROPOFF)),
            list(Ride.objects.filter(status=Ride.Status.DROPOFF)),
        )
        self.assertEqual(
            list(ride_list_queryset(rider_email=self.rider.email)),
            list(Ride.objects.filter(rider=self.rider).order_by("id")),
        )
        self.assertEqual(
            list(
                ride_list_queryset(
                    status=Ride.Status.PICKUP,
                    rider_email=self.rider.email,
                )
            ),
            [matching],
        )
        self.assertFalse(
            ride_list_queryset(rider_email="missing@example.com").exists()
        )

    def test_pickup_time_sorting_uses_id_as_a_stable_tiebreaker(self):
        now = timezone.now()
        earlier = self.create_ride(pickup_time=now - timedelta(hours=1))
        tied_first = self.create_ride(pickup_time=now)
        tied_second = self.create_ride(pickup_time=now)

        ascending = list(
            ride_list_queryset(sort_by="pickup_time", sort_order="asc")
        )
        descending = list(
            ride_list_queryset(sort_by="pickup_time", sort_order="desc")
        )

        self.assertEqual(ascending, [earlier, tied_first, tied_second])
        self.assertEqual(descending, [tied_second, tied_first, earlier])

    def test_distance_sorting_is_calculated_by_postgresql(self):
        nearest = self.create_ride(
            pickup_latitude=0,
            pickup_longitude=0,
        )
        middle = self.create_ride(
            pickup_latitude=0,
            pickup_longitude=1,
        )
        farthest = self.create_ride(
            pickup_latitude=0,
            pickup_longitude=2,
        )

        queryset = ride_list_queryset(
            sort_by="distance",
            sort_order="asc",
            pickup_latitude=0,
            pickup_longitude=0,
        )
        rides = list(queryset)
        sql = str(queryset.query).upper()

        self.assertEqual(rides, [nearest, middle, farthest])
        self.assertAlmostEqual(rides[0].pickup_distance_km, 0, places=5)
        self.assertAlmostEqual(rides[1].pickup_distance_km, 111.195, places=3)
        self.assertIn("ACOS", sql)
        self.assertIn("ORDER BY", sql)

    def test_distance_sorting_supports_descending_and_stable_ties(self):
        tied_first = self.create_ride(
            pickup_latitude=0,
            pickup_longitude=1,
        )
        tied_second = self.create_ride(
            pickup_latitude=0,
            pickup_longitude=-1,
        )
        nearest = self.create_ride(
            pickup_latitude=0,
            pickup_longitude=0,
        )

        ascending = list(
            ride_list_queryset(
                sort_by="distance",
                sort_order="asc",
                pickup_latitude=0,
                pickup_longitude=0,
            )
        )
        descending = list(
            ride_list_queryset(
                sort_by="distance",
                sort_order="desc",
                pickup_latitude=0,
                pickup_longitude=0,
            )
        )

        self.assertEqual(ascending, [nearest, tied_first, tied_second])
        self.assertEqual(descending, [tied_second, tied_first, nearest])

    def test_distance_sorting_combines_with_existing_filters(self):
        other_rider = User.objects.create_user(
            email="distance-rider@example.com",
            password="test-password",
            first_name="Distance",
            last_name="Rider",
            phone_number="+15550000014",
            role=User.Role.RIDER,
        )
        farthest_match = self.create_ride(
            status=Ride.Status.PICKUP,
            pickup_latitude=0,
            pickup_longitude=2,
        )
        nearest_match = self.create_ride(
            status=Ride.Status.PICKUP,
            pickup_latitude=0,
            pickup_longitude=1,
        )
        self.create_ride(
            status=Ride.Status.DROPOFF,
            pickup_latitude=0,
            pickup_longitude=0,
        )
        self.create_ride(
            rider=other_rider,
            status=Ride.Status.PICKUP,
            pickup_latitude=0,
            pickup_longitude=0,
        )

        rides = list(
            ride_list_queryset(
                status=Ride.Status.PICKUP,
                rider_email=self.rider.email,
                sort_by="distance",
                sort_order="asc",
                pickup_latitude=0,
                pickup_longitude=0,
            )
        )

        self.assertEqual(rides, [nearest_match, farthest_match])
