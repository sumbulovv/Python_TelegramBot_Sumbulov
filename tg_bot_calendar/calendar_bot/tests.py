from datetime import date, time

from django.test import TestCase

from .models import Appointment, Event, TelegramUser
from .services import (
    AppointmentPermissionError,
    ParticipantBusyError,
    get_user_appointment_details,
    get_user_busy_intervals,
    invite_user_to_event,
    list_public_events_by_telegram_id,
    list_user_appointments,
    respond_to_appointment,
    set_event_public,
)


class AppointmentServiceTests(TestCase):
    def setUp(self):
        self.organizer_user_id = 1001
        self.participant_user_id = 2002
        self.organizer = TelegramUser.objects.create(
            telegram_id=self.organizer_user_id,
            name="Organizer",
        )
        self.participant = TelegramUser.objects.create(
            telegram_id=self.participant_user_id,
            name="Participant",
        )
        self.event = Event.objects.create(
            name="Planning",
            date=date(2026, 7, 14),
            time=time(10, 0),
            details="Sprint planning",
            user_id=self.organizer_user_id,
            owner=self.organizer,
        )

    def test_invite_user_creates_pending_appointment_when_participant_is_free(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer_user_id,
            self.participant_user_id,
        )

        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(appointment.user_id, self.participant_user_id)

    def test_busy_intervals_include_pending_and_confirmed_appointments(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer_user_id,
            self.participant_user_id,
        )

        busy_intervals = get_user_busy_intervals(self.participant_user_id)

        self.assertEqual(len(busy_intervals), 1)
        self.assertEqual(busy_intervals[0]["appointment_id"], appointment.id)

    def test_invite_user_raises_when_participant_has_overlapping_appointment(self):
        invite_user_to_event(
            self.event.id,
            self.organizer_user_id,
            self.participant_user_id,
        )
        overlapping_event = Event.objects.create(
            name="Review",
            date=date(2026, 7, 14),
            time=time(10, 30),
            details="Design review",
            user_id=self.organizer_user_id,
            owner=self.organizer,
        )

        with self.assertRaises(ParticipantBusyError):
            invite_user_to_event(
                overlapping_event.id,
                self.organizer_user_id,
                self.participant_user_id,
            )

    def test_participant_can_confirm_appointment(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer_user_id,
            self.participant_user_id,
        )

        respond_to_appointment(
            appointment.id,
            self.participant_user_id,
            Appointment.Status.CONFIRMED,
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)

    def test_user_can_list_related_appointments(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer_user_id,
            self.participant_user_id,
        )

        participant_appointments = list_user_appointments(self.participant_user_id)
        organizer_appointments = list_user_appointments(self.organizer_user_id)

        self.assertEqual(participant_appointments[0]["appointment_id"], appointment.id)
        self.assertEqual(organizer_appointments[0]["appointment_id"], appointment.id)

    def test_user_cannot_get_unrelated_appointment_details(self):
        appointment = invite_user_to_event(
            self.event.id,
            self.organizer_user_id,
            self.participant_user_id,
        )

        with self.assertRaises(AppointmentPermissionError):
            get_user_appointment_details(appointment.id, user_id=3003)


class PublicEventTests(TestCase):
    def setUp(self):
        self.owner_user_id = 1001
        self.viewer_user_id = 2002
        self.owner = TelegramUser.objects.create(
            telegram_id=self.owner_user_id,
            name="Owner",
        )
        self.viewer = TelegramUser.objects.create(
            telegram_id=self.viewer_user_id,
            name="Viewer",
        )
        self.public_event = Event.objects.create(
            name="Open demo",
            date=date(2026, 7, 27),
            time=time(12, 0),
            details="Public event",
            is_public=True,
            user_id=self.owner_user_id,
            owner=self.owner,
        )
        self.private_event = Event.objects.create(
            name="Private planning",
            date=date(2026, 7, 28),
            time=time(14, 0),
            details="Private event",
            user_id=self.owner_user_id,
            owner=self.owner,
        )

    def test_public_flag_is_saved_on_event(self):
        self.assertTrue(self.public_event.is_public)
        self.assertFalse(self.private_event.is_public)

    def test_public_events_can_be_loaded_by_owner_telegram_id(self):
        public_events = list_public_events_by_telegram_id(self.owner_user_id)

        self.assertEqual(len(public_events), 1)
        self.assertEqual(public_events[0]["id"], self.public_event.id)

    def test_owner_can_publish_private_event(self):
        event = set_event_public(self.private_event.id, self.owner_user_id, True)

        self.private_event.refresh_from_db()
        self.assertIsNotNone(event)
        self.assertTrue(self.private_event.is_public)

    def test_other_user_cannot_publish_event(self):
        event = set_event_public(self.private_event.id, self.viewer_user_id, True)

        self.private_event.refresh_from_db()
        self.assertIsNone(event)
        self.assertFalse(self.private_event.is_public)
