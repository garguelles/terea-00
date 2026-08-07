"""Ride API input and output serializers."""

import math

from rest_framework import serializers

from apps.rides.models import Ride, RideEvent
from apps.users.models import User


class RideSerializer(serializers.ModelSerializer):
    id_ride = serializers.IntegerField(source="id", read_only=True)
    id_rider = serializers.PrimaryKeyRelatedField(
        source="rider",
        queryset=User.objects.filter(role=User.Role.RIDER),
    )
    id_driver = serializers.PrimaryKeyRelatedField(
        source="driver",
        queryset=User.objects.filter(role=User.Role.DRIVER),
    )
    pickup_latitude = serializers.FloatField(min_value=-90, max_value=90)
    pickup_longitude = serializers.FloatField(min_value=-180, max_value=180)
    dropoff_latitude = serializers.FloatField(min_value=-90, max_value=90)
    dropoff_longitude = serializers.FloatField(min_value=-180, max_value=180)

    class Meta:
        model = Ride
        fields = [
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        coordinate_fields = (
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
        )
        errors = {
            field: "Coordinate must be finite."
            for field in coordinate_fields
            if field in attrs and not math.isfinite(attrs[field])
        }
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class RideEventSerializer(serializers.ModelSerializer):
    id_ride_event = serializers.IntegerField(source="id", read_only=True)
    id_ride = serializers.PrimaryKeyRelatedField(
        source="ride",
        queryset=Ride.objects.all(),
    )

    class Meta:
        model = RideEvent
        fields = [
            "id_ride_event",
            "id_ride",
            "description",
            "created_at",
        ]
        read_only_fields = ["created_at"]
