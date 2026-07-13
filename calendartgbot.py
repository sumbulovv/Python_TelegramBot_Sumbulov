import re
from datetime import date as date_cls
from datetime import datetime, time as time_cls, timedelta

from django.db.models import F

from calendar_bot.models import Event, TelegramUser


class CalendarTgBot:
    MONTHS = {
        "январь": 1,
        "января": 1,
        "янв": 1,
        "jan": 1,
        "january": 1,
        "февраль": 2,
        "февраля": 2,
        "фев": 2,
        "feb": 2,
        "february": 2,
        "март": 3,
        "марта": 3,
        "мар": 3,
        "mar": 3,
        "march": 3,
        "апрель": 4,
        "апреля": 4,
        "апр": 4,
        "apr": 4,
        "april": 4,
        "май": 5,
        "мая": 5,
        "may": 5,
        "июнь": 6,
        "июня": 6,
        "июн": 6,
        "jun": 6,
        "june": 6,
        "июль": 7,
        "июля": 7,
        "июл": 7,
        "jul": 7,
        "july": 7,
        "август": 8,
        "августа": 8,
        "авг": 8,
        "aug": 8,
        "august": 8,
        "сентябрь": 9,
        "сентября": 9,
        "сен": 9,
        "сент": 9,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "октябрь": 10,
        "октября": 10,
        "окт": 10,
        "oct": 10,
        "october": 10,
        "ноябрь": 11,
        "ноября": 11,
        "ноя": 11,
        "nov": 11,
        "november": 11,
        "декабрь": 12,
        "декабря": 12,
        "дек": 12,
        "dec": 12,
        "december": 12,
    }

    def __init__(self):
        pass

    def register_user(self, user_id, name):
        user, created = TelegramUser.objects.get_or_create(
            telegram_id=user_id,
            defaults={"name": name or ""},
        )
        if not created and name and user.name != name:
            user.name = name
            user.save(update_fields=["name", "updated_at"])

        return created

    def login_user(self, user_id, name):
        return self.register_user(user_id, name)

    def is_user_registered(self, user_id):
        return TelegramUser.objects.filter(telegram_id=user_id).exists()

    def create_event(self, name, date, time, details, user_id):
        owner = self._get_user(user_id)
        event = Event.objects.create(
            name=name,
            date=self._parse_date(date),
            time=self._parse_time(time),
            details=details,
            user_id=user_id,
            owner=owner,
        )
        self._increment_user_metric(owner.telegram_id, "events_created")
        return event.id

    def get_event(self, event_id, user_id):
        event = self._events_for_user(user_id).filter(id=event_id).first()
        return self._event_to_dict(event) if event else None

    def delete_event(self, event_id, user_id):
        event = self._events_for_user(user_id).filter(id=event_id).first()
        if not event:
            return False

        event.delete()
        self._increment_user_metric(user_id, "events_cancelled")
        return True

    def get_user_events_by_telegram_id(self, telegram_id):
        return [
            self._event_to_dict(event)
            for event in self._events_for_user(telegram_id).order_by("date", "time", "id")
        ]

    def get_user_calendar(self, telegram_id):
        return self.get_user_events_by_telegram_id(telegram_id)

    def list_events(self, user_id):
        return self.get_user_events_by_telegram_id(user_id)

    def update_event(self, event_id, user_id, name=None, date=None, time=None, details=None):
        if all(value is None for value in (name, date, time, details)):
            return False

        event = self._events_for_user(user_id).filter(id=event_id).first()
        if not event:
            return False

        if name is not None:
            event.name = name

        if date is not None:
            event.date = self._parse_date(date)

        if time is not None:
            event.time = self._parse_time(time)

        if details is not None:
            event.details = details

        event.save()
        self._increment_user_metric(user_id, "events_edited")
        return True

    @staticmethod
    def _get_user(user_id):
        user, _ = TelegramUser.objects.get_or_create(
            telegram_id=user_id,
            defaults={"name": ""},
        )
        return user

    @staticmethod
    def _events_for_user(user_id):
        return Event.objects.select_related("owner").filter(owner__telegram_id=user_id)

    @staticmethod
    def _increment_user_metric(user_id, field_name):
        TelegramUser.objects.filter(telegram_id=user_id).update(
            **{field_name: F(field_name) + 1}
        )

    @staticmethod
    def _event_to_dict(event):
        return {
            "id": event.id,
            "name": event.name,
            "date": event.date,
            "time": event.time,
            "details": event.details,
            "user_id": event.user_id,
        }

    @staticmethod
    def _parse_date(value):
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date_cls):
            return value

        if value is None:
            raise ValueError("Дата не указана.")

        raw_value = str(value).strip()
        normalized = raw_value.lower().replace("ё", "е")
        today = date_cls.today()

        relative_dates = {
            "сегодня": today,
            "today": today,
            "завтра": today + timedelta(days=1),
            "tomorrow": today + timedelta(days=1),
            "послезавтра": today + timedelta(days=2),
            "после завтра": today + timedelta(days=2),
            "вчера": today - timedelta(days=1),
            "yesterday": today - timedelta(days=1),
        }
        if normalized in relative_dates:
            return relative_dates[normalized]

        relative_match = re.fullmatch(
            r"через\s+(\d+)\s+(?:день|дня|дней)",
            normalized,
        )
        if relative_match:
            return today + timedelta(days=int(relative_match.group(1)))

        date_from_iso = CalendarTgBot._parse_iso_date(raw_value)
        if date_from_iso:
            return date_from_iso

        date_from_known_formats = CalendarTgBot._parse_known_date_formats(raw_value)
        if date_from_known_formats:
            return date_from_known_formats

        date_from_compact_digits = CalendarTgBot._parse_compact_digits(normalized)
        if date_from_compact_digits:
            return date_from_compact_digits

        date_from_numeric_parts = CalendarTgBot._parse_numeric_parts(normalized)
        if date_from_numeric_parts:
            return date_from_numeric_parts

        date_from_month_name = CalendarTgBot._parse_month_name(normalized)
        if date_from_month_name:
            return date_from_month_name

        raise ValueError(
            "Не удалось распознать дату. Примеры: 01.01.2020, "
            "2020-01-01, 1 января 2020, завтра."
        )

    @staticmethod
    def _parse_time(value):
        if isinstance(value, datetime):
            return value.time()

        if isinstance(value, time_cls):
            return value

        for time_format in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(value, time_format).time()
            except (TypeError, ValueError):
                pass

        raise ValueError("Время должно быть в формате ЧЧ:ММ.")

    @staticmethod
    def _parse_iso_date(value):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @staticmethod
    def _parse_known_date_formats(value):
        for date_format in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d.%m",
            "%d/%m",
            "%d-%m",
        ):
            try:
                parsed = datetime.strptime(value, date_format).date()
            except ValueError:
                continue

            if "%Y" not in date_format and "%y" not in date_format:
                parsed = parsed.replace(year=date_cls.today().year)

            return parsed

        return None

    @staticmethod
    def _parse_compact_digits(value):
        if not re.fullmatch(r"\d{6}|\d{8}", value):
            return None

        try:
            if len(value) == 8 and value[:4].isdigit() and int(value[:4]) > 1900:
                return date_cls(int(value[:4]), int(value[4:6]), int(value[6:8]))

            if len(value) == 8:
                return date_cls(int(value[4:8]), int(value[2:4]), int(value[:2]))

            return date_cls(
                CalendarTgBot._normalize_year(int(value[4:6])),
                int(value[2:4]),
                int(value[:2]),
            )
        except ValueError:
            return None

    @staticmethod
    def _parse_numeric_parts(value):
        numeric_match = re.fullmatch(
            r"(\d{1,4})[./-](\d{1,2})(?:[./-](\d{1,4}))?",
            value,
        )
        if not numeric_match:
            return None

        first, second, third = numeric_match.groups()
        try:
            if len(first) == 4:
                return date_cls(int(first), int(second), int(third))

            year = CalendarTgBot._normalize_year(int(third)) if third else date_cls.today().year
            return date_cls(year, int(second), int(first))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_month_name(value):
        cleaned_value = re.sub(r"\b(?:г|года|year)\b\.?", " ", value)
        cleaned_value = cleaned_value.replace(",", " ")
        tokens = re.findall(r"[a-zа-я]+|\d{1,4}", cleaned_value)

        month_indexes = [
            index for index, token in enumerate(tokens)
            if token in CalendarTgBot.MONTHS
        ]
        if not month_indexes:
            return None

        month_index = month_indexes[0]
        month = CalendarTgBot.MONTHS[tokens[month_index]]
        number_tokens = [
            (index, token)
            for index, token in enumerate(tokens)
            if token.isdigit()
        ]

        day_token = CalendarTgBot._pick_day_token(number_tokens, month_index)
        if day_token is None:
            return None

        day_index, day_value = day_token
        year = date_cls.today().year
        for index, token in number_tokens:
            if index == day_index:
                continue

            numeric_year = int(token)
            if len(token) >= 3 or len(number_tokens) > 1:
                year = CalendarTgBot._normalize_year(numeric_year)
                break

        try:
            return date_cls(year, month, int(day_value))
        except ValueError:
            return None

    @staticmethod
    def _pick_day_token(number_tokens, month_index):
        before_month = [
            (index, token)
            for index, token in number_tokens
            if index < month_index and int(token) <= 31
        ]
        if before_month:
            return before_month[-1]

        after_month = [
            (index, token)
            for index, token in number_tokens
            if index > month_index and int(token) <= 31
        ]
        if after_month:
            return after_month[0]

        for index, token in number_tokens:
            if int(token) <= 31:
                return index, token

        return None

    @staticmethod
    def _normalize_year(year):
        if year < 100:
            return 2000 + year if year < 70 else 1900 + year

        return year
