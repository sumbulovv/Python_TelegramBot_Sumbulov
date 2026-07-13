from django.contrib import admin
from django.db.models import Count

from .models import Appointment, BotStatistics, Event, TelegramUser

# Register your models here.


class EventInline(admin.TabularInline):
    model = Event
    fields = ("id", "name", "date", "time", "details")
    readonly_fields = ("id",)
    extra = 0


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "name",
        "event_total",
        "events_created",
        "events_edited",
        "events_cancelled",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("name", "=telegram_id")
    readonly_fields = (
        "events_created",
        "events_edited",
        "events_cancelled",
        "created_at",
        "updated_at",
    )
    inlines = (EventInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(event_total_count=Count("events"))

    @admin.display(description="Events")
    def event_total(self, obj):
        return obj.event_total_count

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Event):
                instance.owner = form.instance
                instance.user_id = form.instance.telegram_id
            instance.save()

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        formset.save_m2m()


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "date", "time", "owner", "user_id")
    list_filter = ("date", "owner")
    search_fields = ("name", "details", "=user_id", "owner__name", "=owner__telegram_id")
    autocomplete_fields = ("owner",)

    def save_model(self, request, obj, form, change):
        obj.user_id = obj.owner.telegram_id
        super().save_model(request, obj, form, change)


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
    search_fields = ("event__name", "details", "=user_id", "event__owner__name")
    autocomplete_fields = ("event",)


@admin.register(BotStatistics)
class BotStatisticsAdmin(admin.ModelAdmin):
    list_display = ("date", "user_count", "event_count", "edited_events", "cancelled_events")
