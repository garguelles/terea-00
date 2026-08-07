"""Ride queries and optimized read use cases."""

from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from apps.rides.models import Ride, RideEvent


def rides_queryset():
    return Ride.objects.order_by("id")


def ride_list_queryset(
    *,
    status=None,
    rider_email=None,
    sort_by=None,
    sort_order=None,
):
    now = timezone.now()
    recent_events = RideEvent.objects.filter(
        created_at__gte=now - timedelta(hours=24),
        created_at__lte=now,
    ).order_by("-created_at", "-id")

    queryset = (
        Ride.objects.select_related("rider", "driver")
        .prefetch_related(
            Prefetch(
                "ride_events",
                queryset=recent_events,
                to_attr="todays_ride_events",
            )
        )
    )

    if status is not None:
        queryset = queryset.filter(status=status)
    if rider_email is not None:
        queryset = queryset.filter(rider__email=rider_email)

    if sort_by == "pickup_time":
        prefix = "-" if sort_order == "desc" else ""
        return queryset.order_by(f"{prefix}pickup_time", f"{prefix}id")

    return queryset.order_by("id")


def ride_events_queryset():
    return RideEvent.objects.order_by("-created_at", "-id")
