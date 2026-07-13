import logging
from telegram import Update
from telegram.ext import ContextTypes
from calendartgbot import CalendarTgBot


logger = logging.getLogger(__name__)


async def create_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        event_name = context.args[0]
        event_datetime = context.args[1]
        event_time = context.args[2] if len(context.args) > 2 else None
        event_details = " ".join(context.args[3:]) if len(context.args) > 3 else None
        calendar = CalendarTgBot()
        event_id = calendar.create_event(event_name, event_datetime, event_time, event_details)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Событие '{event_name}' создано с ID {event_id}.")
    except Exception:
        logger.exception("Failed to create event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def get_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        event_id = int(context.args[0])
        calendar = CalendarTgBot()
        event = calendar.get_event(event_id)
        if event:
            text_event = f"ID: {event['id']}, Name: {event['name']}, Date: {event['date']}, Time: {event['time']}, Details: {event['details']}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Событие: {text_event}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except Exception:
        logger.exception("Failed to get event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def delete_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        event_id = int(context.args[0])
        calendar = CalendarTgBot()
        result = calendar.delete_event(event_id)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие удалено.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except Exception:
        logger.exception("Failed to delete event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def list_events_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        calendar = CalendarTgBot()
        events = calendar.list_events()
        if events:
            events_text = "\n".join([f"ID: {event['id']}, Name: {event['name']}, Date: {event['date']}, Time: {event['time']}, Details: {event['details']}" for event in events])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Список событий:\n{events_text}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="События не найдены.")
    except Exception:
        logger.exception("Failed to list events")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def update_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        event_id = int(context.args[0])
        event_name = context.args[1] if len(context.args) > 1 else None
        event_datetime = context.args[2] if len(context.args) > 2 else None
        event_time = context.args[3] if len(context.args) > 3 else None
        event_details = " ".join(context.args[4:]) if len(context.args) > 4 else None
        calendar = CalendarTgBot()
        result = calendar.update_event(event_id, name=event_name, date=event_datetime, time=event_time, details=event_details)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие обновлено.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Событие не найдено.")
    except Exception:
        logger.exception("Failed to update event")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю.")
