from datetime import datetime, timedelta

from django.db import models


class Event(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    details = models.TextField(blank=True, null=True)
    user_id = models.IntegerField()

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
    user_id = models.IntegerField()
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
            models.Index(fields=["user_id", "appointment_date", "status"]),
        ]

    @property
    def starts_at(self):
        return datetime.combine(self.appointment_date, self.appointment_time)

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.duration_minutes)

    def __str__(self):
        return f"Appointment for {self.event.name} at {self.appointment_date}:{self.appointment_time} by User {self.user_id}"
