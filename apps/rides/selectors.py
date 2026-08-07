"""Ride queries and optimized read use cases."""

from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from apps.rides.models import Ride, RideEvent


def rides_queryset():
    return Ride.objects.order_by("id")


def ride_list_queryset():
    now = timezone.now()
    recent_events = RideEvent.objects.filter(
        created_at__gte=now - timedelta(hours=24),
        created_at__lte=now,
    ).order_by("-created_at", "-id")

    return (
        Ride.objects.select_related("rider", "driver")
        .prefetch_related(
            Prefetch(
                "ride_events",
                queryset=recent_events,
                to_attr="todays_ride_events",
            )
        )
        .order_by("id")
    )


def ride_events_queryset():
    return RideEvent.objects.order_by("-created_at", "-id")
