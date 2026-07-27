from rest_framework import serializers

from .models import Appointment, BotStatistics, Event, TelegramUser


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = (
            "id",
            "telegram_id",
            "name",
            "events_created",
            "events_edited",
            "events_cancelled",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "events_created",
            "events_edited",
            "events_cancelled",
            "created_at",
            "updated_at",
        )


class EventSerializer(serializers.ModelSerializer):
    owner_telegram_id = serializers.IntegerField(
        source="owner.telegram_id",
        read_only=True,
    )
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = (
            "id",
            "name",
            "date",
            "time",
            "details",
            "is_public",
            "user_id",
            "owner",
            "owner_telegram_id",
            "owner_name",
        )
        read_only_fields = ("id", "user_id", "owner_telegram_id", "owner_name")

    def create(self, validated_data):
        owner = validated_data["owner"]
        validated_data["user_id"] = owner.telegram_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        owner = validated_data.get("owner", instance.owner)
        validated_data["user_id"] = owner.telegram_id
        return super().update(instance, validated_data)


class AppointmentSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)
    organizer_user_id = serializers.IntegerField(source="event.user_id", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "event",
            "event_name",
            "organizer_user_id",
            "user_id",
            "appointment_date",
            "appointment_time",
            "duration_minutes",
            "details",
            "status",
            "status_display",
        )
        read_only_fields = (
            "id",
            "event_name",
            "organizer_user_id",
            "status_display",
        )


class BotStatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotStatistics
        fields = (
            "id",
            "date",
            "user_count",
            "event_count",
            "edited_events",
            "cancelled_events",
        )
        read_only_fields = ("id",)
