import csv
import json
from datetime import datetime, timedelta
from io import StringIO

from django.core import signing
from django.db import transaction
from django.db.models import Q

from .models import Appointment, Event


BUSY_APPOINTMENT_STATUSES = (
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
)
APPOINTMENT_STATUS_ALIASES = {
    "pending": Appointment.Status.PENDING,
    "ожидание": Appointment.Status.PENDING,
    "ожидает": Appointment.Status.PENDING,
    "confirmed": Appointment.Status.CONFIRMED,
    "confirm": Appointment.Status.CONFIRMED,
    "подтверждено": Appointment.Status.CONFIRMED,
    "подтвержден": Appointment.Status.CONFIRMED,
    "cancelled": Appointment.Status.CANCELLED,
    "canceled": Appointment.Status.CANCELLED,
    "cancel": Appointment.Status.CANCELLED,
    "declined": Appointment.Status.CANCELLED,
    "decline": Appointment.Status.CANCELLED,
    "отменено": Appointment.Status.CANCELLED,
    "отменен": Appointment.Status.CANCELLED,
    "отклонено": Appointment.Status.CANCELLED,
    "отклонен": Appointment.Status.CANCELLED,
}
EVENT_EXPORT_TOKEN_SALT = "calendar_bot.event_export"
EVENT_EXPORT_FIELDS = (
    "id",
    "name",
    "date",
    "time",
    "details",
    "is_public",
    "owner_telegram_id",
)


class AppointmentError(Exception):
    pass


class EventNotFoundError(AppointmentError):
    pass


class AppointmentNotFoundError(AppointmentError):
    pass


class ParticipantBusyError(AppointmentError):
    def __init__(self, busy_intervals):
        self.busy_intervals = busy_intervals
        super().__init__("Participant is busy at the requested time.")


class AppointmentPermissionError(AppointmentError):
    pass


def create_event_export_token(telegram_id):
    return signing.dumps(
        {"telegram_id": int(telegram_id)},
        salt=EVENT_EXPORT_TOKEN_SALT,
    )


def parse_event_export_token(token, max_age=None):
    payload = signing.loads(
        token,
        salt=EVENT_EXPORT_TOKEN_SALT,
        max_age=max_age,
    )
    return int(payload["telegram_id"])


def export_user_events(telegram_id, export_format="json"):
    normalized_format = str(export_format or "json").strip().lower()
    events = [
        _event_to_export_row(event)
        for event in Event.objects.select_related("owner").filter(
            owner__telegram_id=telegram_id,
        )
    ]

    if normalized_format == "json":
        return {
            "content": json.dumps(
                {"events": events},
                ensure_ascii=False,
                indent=2,
            ),
            "content_type": "application/json; charset=utf-8",
            "filename": f"events_{telegram_id}.json",
        }

    if normalized_format == "csv":
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=EVENT_EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(events)
        return {
            "content": output.getvalue(),
            "content_type": "text/csv; charset=utf-8",
            "filename": f"events_{telegram_id}.csv",
        }

    raise ValueError("Unsupported export format. Use json or csv.")


def list_public_events_by_telegram_id(telegram_id):
    events = Event.objects.select_related("owner").filter(
        owner__telegram_id=telegram_id,
        is_public=True,
    )
    return [_event_to_details(event) for event in events]


def set_event_public(event_id, owner_user_id, is_public=True):
    event = Event.objects.select_related("owner").filter(
        id=event_id,
        owner__telegram_id=owner_user_id,
    ).first()
    if not event:
        return None

    event.is_public = is_public
    event.save(update_fields=["is_public"])
    return _event_to_details(event)


def toggle_event_public(event_id, owner_user_id):
    event = Event.objects.select_related("owner").filter(
        id=event_id,
        owner__telegram_id=owner_user_id,
    ).first()
    if not event:
        return None

    event.is_public = not event.is_public
    event.save(update_fields=["is_public"])
    return _event_to_details(event)


def get_user_busy_intervals(user_id, appointment_date=None, statuses=None):
    statuses = statuses or BUSY_APPOINTMENT_STATUSES
    appointments = Appointment.objects.select_related("event").filter(
        user_id=user_id,
        status__in=statuses,
    )

    if appointment_date is not None:
        appointments = appointments.filter(appointment_date=appointment_date)

    return [
        {
            "appointment_id": appointment.id,
            "event_id": appointment.event_id,
            "event_name": appointment.event.name,
            "start": appointment.starts_at,
            "end": appointment.ends_at,
            "status": appointment.status,
        }
        for appointment in appointments
    ]


def is_user_available(user_id, starts_at, ends_at, exclude_appointment_id=None):
    appointments = Appointment.objects.select_related("event").filter(
        user_id=user_id,
        appointment_date=starts_at.date(),
        status__in=BUSY_APPOINTMENT_STATUSES,
    )

    if exclude_appointment_id is not None:
        appointments = appointments.exclude(id=exclude_appointment_id)

    busy_intervals = []
    for appointment in appointments:
        if _intervals_overlap(starts_at, ends_at, appointment.starts_at, appointment.ends_at):
            busy_intervals.append(
                {
                    "appointment_id": appointment.id,
                    "event_id": appointment.event_id,
                    "event_name": appointment.event.name,
                    "start": appointment.starts_at,
                    "end": appointment.ends_at,
                    "status": appointment.status,
                }
            )

    return len(busy_intervals) == 0, busy_intervals


@transaction.atomic
def invite_user_to_event(event_id, organizer_user_id, participant_user_id, duration_minutes=60):
    if duration_minutes <= 0:
        raise ValueError("Appointment duration must be positive.")

    try:
        event = Event.objects.select_for_update().get(id=event_id, user_id=organizer_user_id)
    except Event.DoesNotExist as exc:
        raise EventNotFoundError("Event was not found for this organizer.") from exc

    existing_appointment = Appointment.objects.filter(
        event=event,
        user_id=participant_user_id,
    ).first()

    starts_at = datetime.combine(event.date, event.time)
    ends_at = starts_at + timedelta(minutes=duration_minutes)
    is_available, busy_intervals = is_user_available(
        participant_user_id,
        starts_at,
        ends_at,
        exclude_appointment_id=existing_appointment.id if existing_appointment else None,
    )

    if not is_available:
        raise ParticipantBusyError(busy_intervals)

    appointment, _ = Appointment.objects.update_or_create(
        event=event,
        user_id=participant_user_id,
        defaults={
            "appointment_date": event.date,
            "appointment_time": event.time,
            "duration_minutes": duration_minutes,
            "details": event.details,
            "status": Appointment.Status.PENDING,
        },
    )
    return appointment


@transaction.atomic
def respond_to_appointment(appointment_id, participant_user_id, status):
    status = Appointment.Status(status)

    if status not in (Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED):
        raise ValueError("Unsupported appointment response status.")

    try:
        appointment = Appointment.objects.select_related("event").select_for_update().get(
            id=appointment_id
        )
    except Appointment.DoesNotExist as exc:
        raise AppointmentNotFoundError("Appointment was not found.") from exc

    if appointment.user_id != participant_user_id:
        raise AppointmentPermissionError("Only the invited participant can answer.")

    appointment.status = status
    appointment.save(update_fields=["status"])
    return appointment


def get_appointment_details(appointment_id):
    appointment = Appointment.objects.select_related("event").get(id=appointment_id)
    return _appointment_to_details(appointment)


def get_user_appointment_details(appointment_id, user_id):
    try:
        appointment = Appointment.objects.select_related("event").get(id=appointment_id)
    except Appointment.DoesNotExist as exc:
        raise AppointmentNotFoundError("Appointment was not found.") from exc

    if appointment.user_id != user_id and appointment.event.user_id != user_id:
        raise AppointmentPermissionError("Appointment is not available for this user.")

    return _appointment_to_details(appointment)


def list_user_appointments(user_id, status=None):
    appointments = Appointment.objects.select_related("event").filter(
        Q(user_id=user_id) | Q(event__user_id=user_id)
    )

    if status:
        appointments = appointments.filter(status=normalize_appointment_status(status))

    return [_appointment_to_details(appointment) for appointment in appointments]


def normalize_appointment_status(status):
    if not status:
        return None

    normalized = str(status).strip().lower().replace("ё", "е")
    if normalized in APPOINTMENT_STATUS_ALIASES:
        return APPOINTMENT_STATUS_ALIASES[normalized]

    return Appointment.Status(normalized)


def _appointment_to_details(appointment):
    return {
        "appointment_id": appointment.id,
        "event_id": appointment.event_id,
        "event_name": appointment.event.name,
        "organizer_user_id": appointment.event.user_id,
        "participant_user_id": appointment.user_id,
        "date": appointment.appointment_date,
        "time": appointment.appointment_time,
        "duration_minutes": appointment.duration_minutes,
        "details": appointment.details,
        "status": appointment.status,
        "status_display": appointment.get_status_display(),
    }


def _event_to_details(event):
    return {
        "id": event.id,
        "name": event.name,
        "date": event.date,
        "time": event.time,
        "details": event.details,
        "user_id": event.user_id,
        "is_public": event.is_public,
    }


def _event_to_export_row(event):
    return {
        "id": event.id,
        "name": event.name,
        "date": event.date.isoformat(),
        "time": event.time.isoformat(),
        "details": event.details or "",
        "is_public": event.is_public,
        "owner_telegram_id": event.owner.telegram_id,
    }


def _intervals_overlap(first_start, first_end, second_start, second_end):
    return first_start < second_end and second_start < first_end
