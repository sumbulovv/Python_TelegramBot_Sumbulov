from datetime import datetime, timedelta

from django.db import transaction

from .models import Appointment, Event


BUSY_APPOINTMENT_STATUSES = (
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
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


def _intervals_overlap(first_start, first_end, second_start, second_end):
    return first_start < second_end and second_start < first_end
