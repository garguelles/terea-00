"""Ride admin configuration."""

from django.contrib import admin

from apps.rides.models import Ride, RideEvent


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "rider", "driver", "pickup_time"]
    list_filter = ["status", "pickup_time"]
    search_fields = ["rider__email", "driver__email"]
    autocomplete_fields = ["rider", "driver"]
    list_select_related = ["rider", "driver"]
    ordering = ["-pickup_time", "-id"]


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ["id", "ride", "description", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["description", "ride__rider__email", "ride__driver__email"]
    autocomplete_fields = ["ride"]
    list_select_related = ["ride"]
    ordering = ["-created_at", "-id"]
