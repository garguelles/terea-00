"""Ride HTTP adapters."""

from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.rides import selectors
from apps.rides.api.serializers import (
    RideEventSerializer,
    RideListQuerySerializer,
    RideListSerializer,
    RideSerializer,
)
from apps.users.api.permissions import IsActiveAdminRole


class RideViewSet(viewsets.ModelViewSet):
    serializer_class = RideSerializer
    permission_classes = [IsActiveAdminRole]

    def get_queryset(self):
        return selectors.rides_queryset()

    def get_serializer_class(self):
        if self.action == "list":
            return RideListSerializer
        return RideSerializer

    def list(self, request, *args, **kwargs):
        query_serializer = RideListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data
        queryset = selectors.ride_list_queryset(
            status=params.get("status"),
            rider_email=params.get("rider_email"),
            sort_by=params.get("sort_by"),
            sort_order=params.get("sort_order"),
            pickup_latitude=params.get("pickup_latitude"),
            pickup_longitude=params.get("pickup_longitude"),
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "This ride has one or more ride events."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RideEventViewSet(viewsets.ModelViewSet):
    serializer_class = RideEventSerializer
    permission_classes = [IsActiveAdminRole]

    def get_queryset(self):
        return selectors.ride_events_queryset()
