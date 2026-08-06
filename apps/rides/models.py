"""Ride persistence models and entity-local behavior."""

from django.conf import settings
from django.db import models


class Ride(models.Model):
    class Status(models.TextChoices):
        EN_ROUTE = "en-route", "En route"
        PICKUP = "pickup", "Pickup"
        DROPOFF = "dropoff", "Dropoff"

    id = models.AutoField(primary_key=True, db_column="id_ride")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EN_ROUTE,
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rides_as_rider",
        db_column="id_rider",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rides_as_driver",
        db_column="id_driver",
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["en-route", "pickup", "dropoff"]),
                name="ride_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    pickup_latitude__gte=-90,
                    pickup_latitude__lte=90,
                ),
                name="ride_pickup_lat_range",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    pickup_longitude__gte=-180,
                    pickup_longitude__lte=180,
                ),
                name="ride_pickup_lon_range",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    dropoff_latitude__gte=-90,
                    dropoff_latitude__lte=90,
                ),
                name="ride_dropoff_lat_range",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    dropoff_longitude__gte=-180,
                    dropoff_longitude__lte=180,
                ),
                name="ride_dropoff_lon_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["pickup_time", "id"],
                name="ride_pickup_time_id_idx",
            ),
            models.Index(
                fields=["status", "pickup_time", "id"],
                name="ride_status_pickup_idx",
            ),
        ]

    def __str__(self):
        return f"Ride {self.pk} ({self.status})"


class RideEvent(models.Model):
    id = models.AutoField(primary_key=True, db_column="id_ride_event")
    ride = models.ForeignKey(
        Ride,
        on_delete=models.PROTECT,
        related_name="ride_events",
        db_column="id_ride",
        db_index=False,
    )
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["ride", "-created_at", "-id"],
                name="event_ride_created_idx",
            ),
        ]

    def __str__(self):
        return f"Ride {self.ride_id}: {self.description}"
