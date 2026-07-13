from datetime import datetime, timedelta

from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    events_created = models.PositiveIntegerField(default=0)
    events_edited = models.PositiveIntegerField(default=0)
    events_cancelled = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["telegram_id"]

    def __str__(self):
        return f"{self.name or 'Telegram user'} ({self.telegram_id})"


class Event(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    details = models.TextField(blank=True, null=True)
    user_id = models.BigIntegerField()
    owner = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="events",
    )

    class Meta:
        ordering = ["date", "time", "id"]
        indexes = [
            models.Index(fields=["user_id", "date"], name="calendar_bo_user_id_9c57b4_idx"),
            models.Index(fields=["owner", "date"], name="calendar_bo_owner_i_ef3c11_idx"),
        ]

    def __str__(self):
        return f"{self.name} on {self.date} at {self.time}"


class BotStatistics(models.Model):
    date = models.DateField(unique=True)
    user_count = models.PositiveIntegerField(default=0)
    event_count = models.PositiveIntegerField(default=0)
    edited_events = models.PositiveIntegerField(default=0)
    cancelled_events = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Total Users: {self.user_count}, Total Events: {self.event_count}, Edited Events: {self.edited_events}, Cancelled Events: {self.cancelled_events} on {self.date}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидание"
        CONFIRMED = "confirmed", "Подтверждено"
        CANCELLED = "cancelled", "Отменено"

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user_id = models.BigIntegerField()
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    details = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        ordering = ["appointment_date", "appointment_time"]
        indexes = [
            models.Index(
                fields=["user_id", "appointment_date", "status"],
                name="calendar_bo_user_id_3d85cf_idx",
            ),
        ]

    @property
    def starts_at(self):
        return datetime.combine(self.appointment_date, self.appointment_time)

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.duration_minutes)

    def __str__(self):
        return f"Appointment for {self.event.name} at {self.appointment_date}:{self.appointment_time} by User {self.user_id}"
