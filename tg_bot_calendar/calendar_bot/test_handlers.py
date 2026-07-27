from datetime import date
from urllib.parse import parse_qs, urlparse

from django.test import SimpleTestCase, override_settings

from tg_handlers import (
    _build_event_export_url,
    _format_appointment_details,
    _format_event_line,
    _format_shared_events,
    _format_user_calendar,
    _parse_create_event_args,
    _parse_update_event_args,
)


class HandlerParsingAndFormattingTests(SimpleTestCase):
    def test_parse_create_event_args_extracts_multiword_date_time_and_details(self):
        name, event_date, event_time, details = _parse_create_event_args(
            ["Planning", "1", "августа", "2026", "10:00", "Sprint", "planning"]
        )

        self.assertEqual(name, "Planning")
        self.assertEqual(event_date, "1 августа 2026")
        self.assertEqual(event_time, "10:00")
        self.assertEqual(details, "Sprint planning")

    def test_parse_update_event_args_supports_partial_update_with_date_time_and_details(self):
        event_id, name, event_date, event_time, details = _parse_update_event_args(
            ["42", "Review", "2026-08-08", "11:30", "Design", "review"]
        )

        self.assertEqual(event_id, 42)
        self.assertEqual(name, "Review")
        self.assertEqual(event_date, "2026-08-08")
        self.assertEqual(event_time, "11:30")
        self.assertEqual(details, "Design review")

    def test_event_formatting_marks_public_and_private_events(self):
        public_event = {
            "id": 1,
            "name": "Demo",
            "date": date(2026, 8, 9),
            "time": "12:00",
            "details": "",
            "is_public": True,
        }
        private_event = {**public_event, "id": 2, "is_public": False}

        self.assertIn("публичное", _format_event_line(public_event))
        self.assertIn("личное", _format_event_line(private_event))
        self.assertIn("Ваш календарь:", _format_user_calendar([public_event]))
        self.assertIn("События не найдены.", _format_shared_events([], 1001))

    def test_appointment_details_format_includes_role_and_status(self):
        appointment = {
            "appointment_id": 7,
            "event_id": 3,
            "event_name": "Planning",
            "date": date(2026, 8, 10),
            "time": "09:00",
            "duration_minutes": 45,
            "status_display": "Подтверждено",
            "organizer_user_id": 1001,
            "participant_user_id": 2002,
            "details": "Sprint planning",
        }

        organizer_text = _format_appointment_details(appointment, 1001)
        participant_text = _format_appointment_details(appointment, 2002)

        self.assertIn("Ваша роль: организатор", organizer_text)
        self.assertIn("Ваша роль: участник", participant_text)
        self.assertIn("Подтверждено", organizer_text)

    @override_settings(SECRET_KEY="test-secret-key")
    def test_build_event_export_url_contains_signed_token_and_requested_format(self):
        url = _build_event_export_url(1001, "csv")
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.path, "/events/export/")
        self.assertEqual(query["format"], ["csv"])
        self.assertIn("token", query)
