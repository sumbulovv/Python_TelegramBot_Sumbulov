from django.db import models

# Create your models here.
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