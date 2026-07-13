import logging
from datetime import datetime

from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from django_bootstrap import setup_django

setup_django()

from calendartgbot import CalendarTgBot
from calendar_bot.models import BotStatistics
from calendar_bot.services import (
    AppointmentNotFoundError,
    AppointmentPermissionError,
    EventNotFoundError,
    ParticipantBusyError,
    get_appointment_details,
    invite_user_to_event,
    respond_to_appointment,
)

logger = logging.getLogger(__name__)


def _increment_statistics(field_name):
    stat, _ = BotStatistics.objects.get_or_create(date=datetime.now().date())
    setattr(stat, field_name, getattr(stat, field_name) + 1)
    stat.save()


def require_registration(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        calendar = CalendarTgBot()

        is_registered = await sync_to_async(
            calendar.is_user_registered,
            thread_sensitive=True,
        )(user_id)
        if not is_registered:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Сначала зарегистрируйтесь командой /register."
            )
            return

        await handler(update, context)

    return wrapper


@require_registration
async def create_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        event_name, event_datetime, event_time, event_details = _parse_create_event_args(
            context.args
        )
        calendar = CalendarTgBot()
        event_id = await sync_to_async(
            calendar.create_event,
            thread_sensitive=True,
        )(event_name, event_datetime, event_time, event_details, user_id)
        await sync_to_async(_increment_statistics, thread_sensitive=True)("event_count")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Событие '{event_name}' создано с ID {event_id}.")
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Проверьте формат команды: /create_event <name> <date> <time> [details]\n"
                "Дата: например 01.01.2020, 2020-01-01, 1 января 2020 или завтра. "
                "Время: ЧЧ:ММ."
            ),
        )
    except Exception:
        logger.exception("Failed to create event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


@require_registration
async def get_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        event_id = int(context.args[0])
        calendar = CalendarTgBot()
        event = await sync_to_async(
            calendar.get_event,
            thread_sensitive=True,
        )(event_id, user_id)
        if event:
            text_event = f"ID: {event['id']}, Name: {event['name']}, Date: {event['date']}, Time: {event['time']}, Details: {event['details']}, User ID: {event['user_id']}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Событие: {text_event}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except Exception:
        logger.exception("Failed to get event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


@require_registration
async def delete_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        event_id = int(context.args[0])
        calendar = CalendarTgBot()
        result = await sync_to_async(
            calendar.delete_event,
            thread_sensitive=True,
        )(event_id, user_id)
        if result:
            await sync_to_async(_increment_statistics, thread_sensitive=True)("cancelled_events")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие удалено.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except Exception:
        logger.exception("Failed to delete event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


@require_registration
async def list_events_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        calendar = CalendarTgBot()
        events = await sync_to_async(
            calendar.list_events,
            thread_sensitive=True,
        )(user_id)
        if events:
            events_text = "\n".join([f"ID: {event['id']}, Name: {event['name']}, Date: {event['date']}, Time: {event['time']}, Details: {event['details']}, User ID: {event['user_id']}" for event in events])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Список событий:\n{events_text}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="События не найдены.")
    except Exception:
        logger.exception("Failed to list events")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


@require_registration
async def update_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        event_id, event_name, event_datetime, event_time, event_details = _parse_update_event_args(
            context.args
        )
        calendar = CalendarTgBot()
        result = await sync_to_async(
            calendar.update_event,
            thread_sensitive=True,
        )(event_id, user_id, name=event_name, date=event_datetime, time=event_time, details=event_details)
        if result:
            await sync_to_async(_increment_statistics, thread_sensitive=True)("edited_events")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие обновлено.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Проверьте формат команды: /update_event <event_id> [name] [date] [time] [details]\n"
                "Дата: например 01.01.2020, 2020-01-01, 1 января 2020 или завтра. "
                "Время: ЧЧ:ММ."
            ),
        )
    except Exception:
        logger.exception("Failed to update event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def register_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        calendar = CalendarTgBot()
        result = await sync_to_async(
            calendar.register_user,
            thread_sensitive=True,
        )(user_id, user_name)
        if result:
            await sync_to_async(_increment_statistics, thread_sensitive=True)("user_count")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пользователь зарегистрирован.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пользователь уже зарегистрирован.")
    except Exception:
        logger.exception("Failed to register user")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю.")


@require_registration
async def invite_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Использование: /invite_user <event_id> <user_id> [duration_minutes]",
            )
            return

        organizer_user_id = update.effective_user.id
        event_id = int(context.args[0])
        participant_user_id = int(context.args[1])
        duration_minutes = int(context.args[2]) if len(context.args) > 2 else 60

        calendar = CalendarTgBot()
        is_participant_registered = await sync_to_async(
            calendar.is_user_registered,
            thread_sensitive=True,
        )(participant_user_id)
        if not is_participant_registered:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Участник не зарегистрирован в боте.",
            )
            return

        appointment = await sync_to_async(
            invite_user_to_event,
            thread_sensitive=True,
        )(event_id, organizer_user_id, participant_user_id, duration_minutes)
        appointment_details = await sync_to_async(
            get_appointment_details,
            thread_sensitive=True,
        )(appointment.id)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Подтвердить",
                        callback_data=f"appointment:confirm:{appointment.id}",
                    ),
                    InlineKeyboardButton(
                        "Отклонить",
                        callback_data=f"appointment:decline:{appointment.id}",
                    ),
                ]
            ]
        )
        invitation_text = _format_appointment_invitation(appointment_details)

        try:
            await context.bot.send_message(
                chat_id=participant_user_id,
                text=invitation_text,
                reply_markup=keyboard,
            )
        except TelegramError:
            logger.exception("Failed to send appointment invitation")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Приглашение создано со статусом «ожидание», но уведомление участнику отправить не удалось.",
            )
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Участник свободен. Приглашение отправлено, статус встречи: ожидание.",
        )
    except EventNotFoundError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except ParticipantBusyError as exc:
        busy_text = _format_busy_intervals(exc.busy_intervals)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Участник занят в это время:\n{busy_text}",
        )
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Проверьте формат команды: /invite_user <event_id> <user_id> [duration_minutes]",
        )
    except Exception:
        logger.exception("Failed to invite user")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


async def appointment_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, action, appointment_id = query.data.split(":")
        response_status = {
            "confirm": "confirmed",
            "decline": "cancelled",
        }[action]
        participant_user_id = update.effective_user.id
        appointment = await sync_to_async(
            respond_to_appointment,
            thread_sensitive=True,
        )(int(appointment_id), participant_user_id, response_status)
        appointment_details = await sync_to_async(
            get_appointment_details,
            thread_sensitive=True,
        )(appointment.id)

        participant_text = _format_appointment_response_for_participant(appointment_details)
        organizer_text = _format_appointment_response_for_organizer(appointment_details)

        await query.edit_message_text(text=participant_text)
        await context.bot.send_message(
            chat_id=appointment_details["organizer_user_id"],
            text=organizer_text,
        )
    except AppointmentPermissionError:
        await query.edit_message_text(text="Ответить на это приглашение может только приглашенный участник.")
    except (AppointmentNotFoundError, KeyError, ValueError):
        await query.edit_message_text(text="Не удалось обработать ответ на приглашение.")
    except Exception:
        logger.exception("Failed to process appointment response")
        await query.edit_message_text(text="Что-то пошло не так. Попробуйте еще раз.")


def _format_appointment_invitation(appointment):
    return (
        "Вас пригласили на встречу.\n"
        f"Событие: {appointment['event_name']}\n"
        f"Дата: {appointment['date']}\n"
        f"Время: {appointment['time']}\n"
        f"Длительность: {appointment['duration_minutes']} мин.\n"
        f"Статус: {appointment['status_display']}"
    )


def _format_appointment_response_for_participant(appointment):
    return (
        f"Ваш ответ сохранен.\n"
        f"Событие: {appointment['event_name']}\n"
        f"Статус: {appointment['status_display']}"
    )


def _format_appointment_response_for_organizer(appointment):
    return (
        f"Участник {appointment['participant_user_id']} ответил на приглашение.\n"
        f"Событие: {appointment['event_name']}\n"
        f"Статус: {appointment['status_display']}"
    )


def _format_busy_intervals(busy_intervals):
    return "\n".join(
        f"{interval['event_name']}: {interval['start']} - {interval['end']} ({interval['status']})"
        for interval in busy_intervals
    )


def _parse_create_event_args(args):
    if len(args) < 3:
        raise ValueError("Not enough arguments to create an event.")

    event_name = args[0]
    event_date, event_time, details_start = _extract_date_and_time(args, date_start=1)
    event_details = " ".join(args[details_start:]) if len(args) > details_start else None
    return event_name, event_date, event_time, event_details


def _parse_update_event_args(args):
    if not args:
        raise ValueError("Event id is required.")

    event_id = int(args[0])
    event_name = args[1] if len(args) > 1 else None
    event_date = None
    event_time = None
    event_details = None

    if len(args) > 2:
        try:
            event_date, event_time, details_start = _extract_date_and_time(args, date_start=2)
            event_details = " ".join(args[details_start:]) if len(args) > details_start else None
        except ValueError:
            event_date = " ".join(args[2:])

    return event_id, event_name, event_date, event_time, event_details


def _extract_date_and_time(args, date_start):
    for index in range(date_start + 1, len(args)):
        if _looks_like_time(args[index]):
            return " ".join(args[date_start:index]), args[index], index + 1

    raise ValueError("Time argument was not found.")


def _looks_like_time(value):
    try:
        CalendarTgBot._parse_time(value)
    except ValueError:
        return False

    return True
