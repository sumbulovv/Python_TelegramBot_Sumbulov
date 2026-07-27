from datetime import date, datetime, time

from django.test import TestCase

from calendartgbot import CalendarTgBot
from calendar_bot.models import Event, TelegramUser


class CalendarTgBotTests(TestCase):
    def test_register_user_creates_user_and_refreshes_name_on_relogin(self):
        calendar = CalendarTgBot()

        created = calendar.register_user(1001, "first_name")
        created_again = calendar.login_user(1001, "updated_name")

        user = TelegramUser.objects.get(telegram_id=1001)
        self.assertIs(created, True)
        self.assertIs(created_again, False)
        self.assertEqual(user.name, "updated_name")
        self.assertIs(calendar.is_user_registered(1001), True)

    def test_create_get_list_update_and_delete_event_flow_is_scoped_to_owner(self):
        calendar = CalendarTgBot()
        owner_id = 1001
        other_user_id = 2002
        calendar.register_user(owner_id, "Owner")
        calendar.register_user(other_user_id, "Other")

        event_id = calendar.create_event(
            "Planning",
            "1 августа 2026",
            "10:30",
            "Sprint planning",
            owner_id,
        )

        owner = TelegramUser.objects.get(telegram_id=owner_id)
        event = Event.objects.get(id=event_id)
        self.assertEqual(event.owner, owner)
        self.assertEqual(event.user_id, owner_id)
        self.assertEqual(event.date, date(2026, 8, 1))
        self.assertEqual(event.time, time(10, 30))
        self.assertEqual(owner.events_created, 1)
        self.assertIsNone(calendar.get_event(event_id, other_user_id))

        listed_events = calendar.list_events(owner_id)
        self.assertEqual([item["id"] for item in listed_events], [event_id])

        updated = calendar.update_event(
            event_id,
            owner_id,
            name="Updated planning",
            date="2026-08-02",
            time="11:00",
            details="Updated details",
        )
        event.refresh_from_db()
        owner.refresh_from_db()
        self.assertIs(updated, True)
        self.assertEqual(event.name, "Updated planning")
        self.assertEqual(event.date, date(2026, 8, 2))
        self.assertEqual(event.time, time(11, 0))
        self.assertEqual(owner.events_edited, 1)

        self.assertIs(calendar.delete_event(event_id, other_user_id), False)
        self.assertIs(calendar.delete_event(event_id, owner_id), True)
        owner.refresh_from_db()
        self.assertEqual(owner.events_cancelled, 1)
        self.assertFalse(Event.objects.filter(id=event_id).exists())

    def test_share_unshare_and_toggle_public_event_are_owner_only(self):
        calendar = CalendarTgBot()
        owner_id = 1001
        other_user_id = 2002
        calendar.register_user(owner_id, "Owner")
        calendar.register_user(other_user_id, "Other")
        event_id = calendar.create_event("Demo", "2026-08-03", "12:00", "", owner_id)

        self.assertIsNone(calendar.share_event(event_id, other_user_id))
        self.assertTrue(calendar.share_event(event_id, owner_id)["is_public"])
        self.assertEqual(calendar.list_public_events_by_telegram_id(owner_id)[0]["id"], event_id)
        self.assertFalse(calendar.toggle_event_public(event_id, owner_id)["is_public"])
        self.assertFalse(calendar.unshare_event(event_id, owner_id)["is_public"])


class CalendarParsingTests(TestCase):
    def test_parse_date_accepts_bot_supported_formats(self):
        examples = [
            ("2026-08-01", date(2026, 8, 1)),
            ("01.08.2026", date(2026, 8, 1)),
            ("1 августа 2026", date(2026, 8, 1)),
            ("20260801", date(2026, 8, 1)),
            (date(2026, 8, 1), date(2026, 8, 1)),
            (datetime(2026, 8, 1, 9, 30), date(2026, 8, 1)),
        ]

        for raw_value, expected in examples:
            with self.subTest(raw_value=raw_value):
                self.assertEqual(CalendarTgBot._parse_date(raw_value), expected)

    def test_parse_time_accepts_bot_supported_formats(self):
        examples = [
            ("09:30", time(9, 30)),
            ("09:30:15", time(9, 30, 15)),
            (time(9, 30), time(9, 30)),
            (datetime(2026, 8, 1, 9, 30), time(9, 30)),
        ]

        for raw_value, expected in examples:
            with self.subTest(raw_value=raw_value):
                self.assertEqual(CalendarTgBot._parse_time(raw_value), expected)
