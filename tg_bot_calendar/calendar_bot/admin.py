from django.contrib import admin
from .models import Appointment, BotStatistics, Event

# Register your models here.


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "date", "time", "user_id")
    list_filter = ("date",)
    search_fields = ("name", "details", "=user_id")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event",
        "user_id",
        "appointment_date",
        "appointment_time",
        "duration_minutes",
        "status",
    )
    list_filter = ("status", "appointment_date")
    search_fields = ("event__name", "details", "=user_id")
    autocomplete_fields = ("event",)


@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ("date", "user_count", "event_count", "edited_events", "cancelled_events")
