"""Ride API input and output serializers."""

import math

from rest_framework import serializers

from apps.rides.models import Ride, RideEvent
from apps.users.models import User
from common.pagination import DefaultPagination


class RideListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Ride.Status.choices,
        required=False,
    )
    rider_email = serializers.EmailField(required=False)
    sort_by = serializers.ChoiceField(
        choices=["pickup_time", "distance"],
        required=False,
    )
    sort_order = serializers.ChoiceField(
        choices=["asc", "desc"],
        required=False,
    )
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=DefaultPagination.max_page_size,
        required=False,
    )
    pickup_latitude = serializers.FloatField(
        min_value=-90,
        max_value=90,
        required=False,
    )
    pickup_longitude = serializers.FloatField(
        min_value=-180,
        max_value=180,
        required=False,
    )

    def validate_rider_email(self, value):
        return value.lower()

    def validate_pickup_latitude(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Coordinate must be finite.")
        return value

    def validate_pickup_longitude(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Coordinate must be finite.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if ("sort_by" in attrs) != ("sort_order" in attrs):
            raise serializers.ValidationError(
                "sort_by and sort_order must be provided together."
            )

        has_latitude = "pickup_latitude" in attrs
        has_longitude = "pickup_longitude" in attrs
        if has_latitude != has_longitude:
            raise serializers.ValidationError(
                "pickup_latitude and pickup_longitude must be provided together."
            )

        if attrs.get("sort_by") == "distance" and not has_latitude:
            raise serializers.ValidationError(
                "Distance sorting requires pickup_latitude and pickup_longitude."
            )

        if has_latitude and attrs.get("sort_by") != "distance":
            raise serializers.ValidationError(
                "Pickup coordinates may only be used with distance sorting."
            )
        return attrs


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


class RideListEventSerializer(serializers.ModelSerializer):
    id_ride_event = serializers.IntegerField(source="id", read_only=True)
    id_ride = serializers.IntegerField(source="ride_id", read_only=True)

    class Meta:
        model = RideEvent
        fields = [
            "id_ride_event",
            "id_ride",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class RideListSerializer(serializers.ModelSerializer):
    id_ride = serializers.IntegerField(source="id", read_only=True)
    id_rider = serializers.IntegerField(source="rider_id", read_only=True)
    id_driver = serializers.IntegerField(source="driver_id", read_only=True)
    todays_ride_events = RideListEventSerializer(many=True, read_only=True)

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
            "todays_ride_events",
        ]
        read_only_fields = fields
