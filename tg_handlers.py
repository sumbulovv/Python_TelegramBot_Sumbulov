import logging
import os
from datetime import datetime
from urllib.parse import urlencode

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
    create_event_export_token,
    get_appointment_details,
    get_user_appointment_details,
    invite_user_to_event,
    list_user_appointments,
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
                text="Сначала войдите командой /login <telegram_id> или /register."
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
            text_event = _format_event_line(event)
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
            events_text = "\n".join([_format_event_line(event) for event in events])
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Список событий:\n{events_text}",
                reply_markup=_build_event_sharing_keyboard(events, user_id),
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="События не найдены.",
                reply_markup=_build_event_export_keyboard(user_id),
            )
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
        created = await _login_telegram_user(user_id, user_name)
        if created:
            await sync_to_async(_increment_statistics, thread_sensitive=True)("user_count")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пользователь зарегистрирован.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пользователь уже зарегистрирован.")
    except Exception:
        logger.exception("Failed to register user")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


async def login_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        actual_user_id = update.effective_user.id
        requested_user_id = int(context.args[0]) if context.args else actual_user_id

        if requested_user_id != actual_user_id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Можно подключить только свой Telegram ID.",
            )
            return

        user_name = update.effective_user.username or update.effective_user.first_name
        created = await _login_telegram_user(requested_user_id, user_name)
        if created:
            await sync_to_async(_increment_statistics, thread_sensitive=True)("user_count")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Вход выполнен. Telegram ID {requested_user_id} подключен к учетной записи.",
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Вы уже вошли с Telegram ID {requested_user_id}.",
            )
    except (IndexError, ValueError):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Проверьте формат команды: /login <telegram_id>",
        )
    except Exception:
        logger.exception("Failed to login user")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


async def _login_telegram_user(user_id, user_name):
    calendar = CalendarTgBot()
    return await sync_to_async(
        calendar.login_user,
        thread_sensitive=True,
    )(user_id, user_name)


@require_registration
async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        shared_user_id = int(context.args[0]) if context.args else None
        calendar = CalendarTgBot()
        events = await sync_to_async(
            calendar.get_user_calendar,
            thread_sensitive=True,
        )(user_id)
        shared_events = []
        if shared_user_id is not None:
            shared_events = await sync_to_async(
                calendar.list_public_events_by_telegram_id,
                thread_sensitive=True,
            )(shared_user_id)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_format_user_calendar(events, shared_events, shared_user_id),
            reply_markup=_build_event_sharing_keyboard(events, user_id),
        )
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Проверьте формат команды: /calendar [telegram_id]",
        )
    except Exception:
        logger.exception("Failed to show user calendar")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Войдите командой /login <telegram_id>, затем откройте календарь "
        "через /calendar. Для выгрузки событий используйте /export_events."
    )


@require_registration
async def export_events_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите формат выгрузки ваших событий. Ссылки действуют 24 часа.",
        reply_markup=_build_event_export_keyboard(user_id),
    )


@require_registration
async def share_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_event_public_from_command(update, context, is_public=True)


@require_registration
async def unshare_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_event_public_from_command(update, context, is_public=False)


@require_registration
async def shared_events_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Использование: /shared_events <telegram_id>",
            )
            return

        shared_user_id = int(context.args[0])
        calendar = CalendarTgBot()
        shared_events = await sync_to_async(
            calendar.list_public_events_by_telegram_id,
            thread_sensitive=True,
        )(shared_user_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_format_shared_events(shared_events, shared_user_id),
        )
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Проверьте формат команды: /shared_events <telegram_id>",
        )
    except Exception:
        logger.exception("Failed to show shared events")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


async def _set_event_public_from_command(update, context, is_public):
    try:
        if not context.args:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    "Использование: /share_event <event_id>"
                    if is_public
                    else "Использование: /unshare_event <event_id>"
                ),
            )
            return

        user_id = update.effective_user.id
        event_id = int(context.args[0])
        calendar = CalendarTgBot()
        event = await sync_to_async(
            calendar.set_event_public,
            thread_sensitive=True,
        )(event_id, user_id, is_public)
        if not event:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_format_event_public_update(event),
        )
    except ValueError:
        command = "/share_event <event_id>" if is_public else "/unshare_event <event_id>"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Проверьте формат команды: {command}",
        )
    except Exception:
        logger.exception("Failed to update event public flag")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


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


async def public_event_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, action, event_id = query.data.split(":")
        if action != "toggle":
            raise ValueError("Unsupported public event action.")

        user_id = update.effective_user.id
        calendar = CalendarTgBot()
        is_registered = await sync_to_async(
            calendar.is_user_registered,
            thread_sensitive=True,
        )(user_id)
        if not is_registered:
            await query.edit_message_text(text="Сначала войдите командой /login <telegram_id> или /register.")
            return

        event = await sync_to_async(
            calendar.toggle_event_public,
            thread_sensitive=True,
        )(int(event_id), user_id)
        if not event:
            await query.edit_message_text(text="Событие не найдено.")
            return

        events = await sync_to_async(
            calendar.get_user_calendar,
            thread_sensitive=True,
        )(user_id)
        await query.edit_message_text(
            text=_format_user_calendar(events),
            reply_markup=_build_event_sharing_keyboard(events, user_id),
        )
    except (IndexError, ValueError):
        await query.edit_message_text(text="Не удалось изменить доступность события.")
    except Exception:
        logger.exception("Failed to process public event callback")
        await query.edit_message_text(text="Что-то пошло не так. Попробуйте еще раз.")


@require_registration
async def list_appointments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id

        if context.args and context.args[0].isdigit():
            appointment = await sync_to_async(
                get_user_appointment_details,
                thread_sensitive=True,
            )(int(context.args[0]), user_id)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_format_appointment_details(appointment, user_id),
            )
            return

        status = context.args[0] if context.args else None
        appointments = await sync_to_async(
            list_user_appointments,
            thread_sensitive=True,
        )(user_id, status=status)

        if not appointments:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Встречи не найдены.",
            )
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_format_appointments_list(appointments, user_id),
        )
    except AppointmentNotFoundError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Встреча не найдена.",
        )
    except AppointmentPermissionError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Эта встреча недоступна вашему пользователю.",
        )
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Проверьте команду: /appointments [id|pending|confirmed|cancelled]\n"
                "Также можно: ожидание, подтверждено, отменено."
            ),
        )
    except Exception:
        logger.exception("Failed to list appointments")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


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


def _format_appointments_list(appointments, current_user_id):
    appointment_lines = [
        _format_appointment_list_item(appointment, current_user_id)
        for appointment in appointments[:30]
    ]

    if len(appointments) > 30:
        appointment_lines.append(f"...и еще {len(appointments) - 30} встреч.")

    return "Ваши встречи:\n" + "\n".join(appointment_lines)


def _format_user_calendar(events, shared_events=None, shared_user_id=None):
    shared_events = shared_events or []
    sections = []

    if events:
        sections.append("Ваш календарь:\n" + _format_events_block(events))
    else:
        sections.append("Ваш календарь пуст.")

    if shared_user_id is not None:
        sections.append(_format_shared_events(shared_events, shared_user_id))

    return "\n\n".join(sections)


def _format_shared_events(events, shared_user_id):
    if not events:
        return f"Общие события пользователя {shared_user_id}:\nСобытия не найдены."

    return f"Общие события пользователя {shared_user_id}:\n" + _format_events_block(events)


def _format_events_block(events, limit=50):
    event_lines = [_format_event_line(event) for event in events[:limit]]

    if len(events) > limit:
        event_lines.append(f"...и еще {len(events) - limit} событий.")

    return "\n".join(event_lines)


def _format_event_line(event):
    return (
        f"ID {event['id']}: {event['name']} | "
        f"{event['date']} {event['time']} | "
        f"{event['details'] or '-'} | "
        f"{_format_event_public_status(event)}"
    )


def _format_event_public_status(event):
    return "публичное" if event.get("is_public") else "личное"


def _format_event_public_update(event):
    if event.get("is_public"):
        return f"Событие ID {event['id']} опубликовано и доступно другим пользователям."

    return f"Событие ID {event['id']} скрыто из общих событий."


def _build_event_sharing_keyboard(events, user_id=None):
    buttons = []
    for event in events[:20]:
        button_text = (
            f"Скрыть ID {event['id']}"
            if event.get("is_public")
            else f"Опубликовать ID {event['id']}"
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"event_public:toggle:{event['id']}",
                )
            ]
        )

    if user_id is not None:
        buttons.extend(_build_event_export_buttons(user_id))

    return InlineKeyboardMarkup(buttons) if buttons else None


def _build_event_export_keyboard(user_id):
    return InlineKeyboardMarkup(_build_event_export_buttons(user_id))


def _build_event_export_buttons(user_id):
    return [
        [
            InlineKeyboardButton(
                "Скачать JSON",
                url=_build_event_export_url(user_id, "json"),
            ),
            InlineKeyboardButton(
                "Скачать CSV",
                url=_build_event_export_url(user_id, "csv"),
            ),
        ]
    ]


def _build_event_export_url(user_id, export_format):
    base_url = os.environ["CALENDAR_EXPORT_BASE_URL"].rstrip("/")
    query = urlencode(
        {
            "token": create_event_export_token(user_id),
            "format": export_format,
        }
    )
    return f"{base_url}/events/export/?{query}"


def _format_appointment_list_item(appointment, current_user_id):
    role = _appointment_role(appointment, current_user_id)
    return (
        f"ID {appointment['appointment_id']}: {appointment['event_name']} | "
        f"{appointment['date']} {appointment['time']} | "
        f"{appointment['status_display']} | {role}"
    )


def _format_appointment_details(appointment, current_user_id):
    return (
        f"Встреча ID {appointment['appointment_id']}\n"
        f"Событие: {appointment['event_name']}\n"
        f"Event ID: {appointment['event_id']}\n"
        f"Дата: {appointment['date']}\n"
        f"Время: {appointment['time']}\n"
        f"Длительность: {appointment['duration_minutes']} мин.\n"
        f"Статус: {appointment['status_display']}\n"
        f"Организатор: {appointment['organizer_user_id']}\n"
        f"Участник: {appointment['participant_user_id']}\n"
        f"Ваша роль: {_appointment_role(appointment, current_user_id)}\n"
        f"Детали: {appointment['details'] or '-'}"
    )


def _appointment_role(appointment, current_user_id):
    if appointment["organizer_user_id"] == current_user_id:
        return "организатор"

    return "участник"


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
