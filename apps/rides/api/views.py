"""Ride HTTP adapters."""

from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.rides import selectors
from apps.rides.api.serializers import RideEventSerializer, RideSerializer
from apps.users.api.permissions import IsActiveAdminRole


class RideViewSet(viewsets.ModelViewSet):
    serializer_class = RideSerializer
    permission_classes = [IsActiveAdminRole]

    def get_queryset(self):
        return selectors.rides_queryset()

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
