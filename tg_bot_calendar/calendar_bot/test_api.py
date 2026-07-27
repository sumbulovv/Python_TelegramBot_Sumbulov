from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from calendar_bot.models import Appointment, Event, TelegramUser


class ApiCriticalPathTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = TelegramUser.objects.create(telegram_id=1001, name="Owner")
        self.other_user = TelegramUser.objects.create(telegram_id=2002, name="Other")

    def test_user_api_filters_by_telegram_id(self):
        response = self.client.get("/api/users/", {"telegram_id": self.owner.telegram_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["telegram_id"], self.owner.telegram_id)

    def test_event_api_create_sets_legacy_user_id_from_owner(self):
        response = self.client.post(
            "/api/events/",
            {
                "name": "API planning",
                "date": "2026-08-06",
                "time": "09:00:00",
                "details": "Created through API",
                "is_public": True,
                "owner": self.owner.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        event = Event.objects.get(id=response.data["id"])
        self.assertEqual(event.owner, self.owner)
        self.assertEqual(event.user_id, self.owner.telegram_id)

    def test_event_api_filters_by_owner_date_and_public_flag(self):
        matching_event = Event.objects.create(
            name="Public owner event",
            date=date(2026, 8, 6),
            time=time(9, 0),
            details="Visible",
            is_public=True,
            user_id=self.owner.telegram_id,
            owner=self.owner,
        )
        Event.objects.create(
            name="Private owner event",
            date=date(2026, 8, 6),
            time=time(10, 0),
            details="Hidden",
            is_public=False,
            user_id=self.owner.telegram_id,
            owner=self.owner,
        )
        Event.objects.create(
            name="Other event",
            date=date(2026, 8, 6),
            time=time(11, 0),
            details="Other",
            is_public=True,
            user_id=self.other_user.telegram_id,
            owner=self.other_user,
        )

        response = self.client.get(
            "/api/events/",
            {
                "owner_telegram_id": self.owner.telegram_id,
                "date": "2026-08-06",
                "is_public": "true",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [matching_event.id])

    def test_appointment_api_filters_by_user_status_and_date(self):
        event = Event.objects.create(
            name="Planning",
            date=date(2026, 8, 7),
            time=time(9, 0),
            details="Sprint planning",
            user_id=self.owner.telegram_id,
            owner=self.owner,
        )
        matching_appointment = Appointment.objects.create(
            event=event,
            user_id=self.other_user.telegram_id,
            appointment_date=date(2026, 8, 7),
            appointment_time=time(9, 0),
            duration_minutes=60,
            details="Accepted",
            status=Appointment.Status.CONFIRMED,
        )
        Appointment.objects.create(
            event=event,
            user_id=self.other_user.telegram_id,
            appointment_date=date(2026, 8, 8),
            appointment_time=time(9, 0),
            duration_minutes=60,
            details="Pending",
            status=Appointment.Status.PENDING,
        )

        response = self.client.get(
            "/api/appointments/",
            {
                "user_id": self.other_user.telegram_id,
                "status": Appointment.Status.CONFIRMED,
                "date": "2026-08-07",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [matching_appointment.id])
        self.assertEqual(response.data[0]["event_name"], "Planning")
        self.assertEqual(response.data[0]["organizer_user_id"], self.owner.telegram_id)
