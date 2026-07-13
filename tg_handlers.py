import logging
from telegram import Update
from telegram.ext import ContextTypes
from calendartgbot import CalendarTgBot


logger = logging.getLogger(__name__)


def require_registration(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        calendar = CalendarTgBot()

        if not calendar.is_user_registered(user_id):
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
        event_name = context.args[0]
        event_datetime = context.args[1]
        event_time = context.args[2] if len(context.args) > 2 else None
        event_details = " ".join(context.args[3:]) if len(context.args) > 3 else None
        calendar = CalendarTgBot()
        event_id = calendar.create_event(event_name, event_datetime, event_time, event_details, user_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Событие '{event_name}' создано с ID {event_id}.")
    except Exception:
        logger.exception("Failed to create event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")


@require_registration
async def get_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        event_id = int(context.args[0])
        calendar = CalendarTgBot()
        event = calendar.get_event(event_id, user_id)
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
        result = calendar.delete_event(event_id, user_id)
        if result:
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
        events = calendar.list_events(user_id)
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
        event_id = int(context.args[0])
        event_name = context.args[1] if len(context.args) > 1 else None
        event_datetime = context.args[2] if len(context.args) > 2 else None
        event_time = context.args[3] if len(context.args) > 3 else None
        event_details = " ".join(context.args[4:]) if len(context.args) > 4 else None
        calendar = CalendarTgBot()
        result = calendar.update_event(event_id, user_id, name=event_name, date=event_datetime, time=event_time, details=event_details)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие обновлено.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except Exception:
        logger.exception("Failed to update event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def register_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_name = update.effective_user.username or update.effective_user.first_name
        calendar = CalendarTgBot()
        result = calendar.register_user(user_id, user_name)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пользователь зарегистрирован.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Пользователь уже зарегистрирован.")
    except Exception:
        logger.exception("Failed to register user")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю.")
