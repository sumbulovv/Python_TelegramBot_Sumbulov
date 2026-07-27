import json
from datetime import date, time

from django.core import signing
from django.test import TestCase

from calendar_bot.models import Appointment, Event, TelegramUser
from calendar_bot.services import (
    AppointmentPermissionError,
    ParticipantBusyError,
    create_event_export_token,
    export_user_events,
    invite_user_to_event,
    is_user_available,
    normalize_appointment_status,
    parse_event_export_token,
    respond_to_appointment,
)


class ServiceCriticalPathTests(TestCase):
    def setUp(self):
        self.organizer = TelegramUser.objects.create(
            telegram_id=1001,
            name="Organizer",
        )
        self.participant = TelegramUser.objects.create(
            telegram_id=2002,
            name="Participant",
        )
        self.event = Event.objects.create(
            name="Planning",
            date=date(2026, 8, 4),
            time=time(10, 0),
            details="Sprint planning",
            user_id=self.organizer.telegram_id,
            owner=self.organizer,
        )

    def test_invite_user_to_event_creates_or_updates_single_pending_appointment(self):
        first_appointment = invite_user_to_event(
            self.event.id,
            self.organizer.telegram_id,
            self.participant.telegram_id,
            duration_minutes=30,
        )
        second_appointment = invite_user_to_event(
            self.event.id,
            self.organizer.telegram_id,
            self.participant.telegram_id,
            duration_minutes=45,
        )

        first_appointment.refresh_from_db()
        self.assertEqual(first_appointment.id, second_appointment.id)
        self.assertEqual(first_appointment.status, Appointment.Status.PENDING)
        self.assertEqual(first_appointment.duration_minutes, 45)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_invite_user_to_event_blocks_overlapping_busy_participant(self):
        invite_user_to_event(
            self.event.id,
            self.organizer.telegram_id,
            self.participant.telegram_id,
        )
        overlapping_event = Event.objects.create(
            name="Review",
            date=date(2026, 8, 4),
            time=time(10, 30),
            details="Design review",
            user_id=self.organizer.telegram_id,
            owner=self.organizer,
        )

        with self.assertRaises(ParticipantBusyError) as context:
            invite_user_to_event(
                overlapping_event.id,
                self.organizer.telegram_id,
                self.participant.telegram_id,
            )

        self.assertEqual(context.exception.busy_intervals[0]["event_id"], self.event.id)

    def test_cancelled_appointment_does_not_make_participant_busy(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer.telegram_id,
            self.participant.telegram_id,
        )
        respond_to_appointment(
            appointment.id,
            self.participant.telegram_id,
            Appointment.Status.CANCELLED,
        )

        available, busy_intervals = is_user_available(
            self.participant.telegram_id,
            appointment.starts_at,
            appointment.ends_at,
        )

        self.assertIs(available, True)
        self.assertEqual(busy_intervals, [])

    def test_only_invited_participant_can_respond_to_appointment(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer.telegram_id,
            self.participant.telegram_id,
        )

        with self.assertRaises(AppointmentPermissionError):
            respond_to_appointment(
                appointment.id,
                self.organizer.telegram_id,
                Appointment.Status.CONFIRMED,
            )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)

    def test_normalize_appointment_status_accepts_bot_aliases(self):
        examples = [
            ("pending", Appointment.Status.PENDING),
            ("ожидание", Appointment.Status.PENDING),
            ("подтверждено", Appointment.Status.CONFIRMED),
            ("cancel", Appointment.Status.CANCELLED),
            ("отменено", Appointment.Status.CANCELLED),
        ]

        for raw_status, expected in examples:
            with self.subTest(raw_status=raw_status):
                self.assertEqual(normalize_appointment_status(raw_status), expected)

    def test_event_export_token_roundtrip_and_invalid_token_rejection(self):
        token = create_event_export_token(1001)

        self.assertEqual(parse_event_export_token(token), 1001)
        with self.assertRaises(signing.BadSignature):
            parse_event_export_token("not-a-valid-token")

    def test_export_user_events_supports_json_and_csv(self):
        other_event = Event.objects.create(
            name="Other",
            date=date(2026, 8, 5),
            time=time(12, 0),
            details="Other user event",
            user_id=self.participant.telegram_id,
            owner=self.participant,
        )

        json_export = export_user_events(self.organizer.telegram_id, "json")
        csv_export = export_user_events(self.organizer.telegram_id, "csv")
        json_payload = json.loads(json_export["content"])

        self.assertEqual(json_export["content_type"], "application/json; charset=utf-8")
        self.assertEqual([event["id"] for event in json_payload["events"]], [self.event.id])
        self.assertNotIn(other_event.id, [event["id"] for event in json_payload["events"]])
        self.assertEqual(csv_export["filename"], f"events_{self.organizer.telegram_id}.csv")
        self.assertIn("Planning", csv_export["content"])
        self.assertNotIn("Other", csv_export["content"])

        with self.assertRaises(ValueError):
            export_user_events(self.organizer.telegram_id, "xml")
