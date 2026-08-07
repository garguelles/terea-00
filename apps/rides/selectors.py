"""Ride queries and optimized read use cases."""

from apps.rides.models import Ride, RideEvent


def rides_queryset():
    return Ride.objects.order_by("id")


def ride_events_queryset():
    return RideEvent.objects.order_by("-created_at", "-id")
