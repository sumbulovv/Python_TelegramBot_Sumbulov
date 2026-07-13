import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from django_bootstrap import setup_django

setup_django()

from calendar_bot.models import BotStatistics
from tg_handlers import (
    appointment_response_handler,
    calendar_handler,
    create_event_handler,
    delete_event_handler,
    get_event_handler,
    invite_user_handler,
    list_appointments_handler,
    list_events_handler,
    login_user_handler,
    register_user_handler,
    start,
    update_event_handler,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BotStatistics.objects.get_or_create(
    date=datetime.now().date(),
    defaults={
        "user_count": 0,
        "event_count": 0,
        "edited_events": 0,
        "cancelled_events": 0,
    },
)


def main():
    logger.info("Starting Telegram bot")
    app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_user_handler))
    app.add_handler(CommandHandler("login", login_user_handler))
    app.add_handler(CommandHandler("calendar", calendar_handler))
    app.add_handler(CommandHandler("create_event", create_event_handler))
    app.add_handler(CommandHandler("get_event", get_event_handler))
    app.add_handler(CommandHandler("delete_event", delete_event_handler))
    app.add_handler(CommandHandler("list_events", list_events_handler))
    app.add_handler(CommandHandler("update_event", update_event_handler))
    app.add_handler(CommandHandler("invite_user", invite_user_handler))
    app.add_handler(CommandHandler("appointments", list_appointments_handler))
    app.add_handler(CommandHandler("list_appointments", list_appointments_handler))
    app.add_handler(
        CallbackQueryHandler(
            appointment_response_handler,
            pattern=r"^appointment:(confirm|decline):\d+$",
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
