import os
import logging
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Application
from django_bootstrap import setup_django

setup_django()

from calendar_bot.models import BotStatistics
from datetime import datetime
from tg_handlers import (
    start, 
    create_event_handler,
    get_event_handler,
    delete_event_handler,
    list_events_handler,
    update_event_handler,
    register_user_handler
    )

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BotStatistics.objects.get_or_create(date=datetime.now().date(), user_count=0, event_count=0, edited_events=0, cancelled_events=0)


def main():
    logger.info("Starting Telegram bot")
    app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_user_handler))
    app.add_handler(CommandHandler('create_event', create_event_handler))
    app.add_handler(CommandHandler('get_event', get_event_handler))
    app.add_handler(CommandHandler('delete_event', delete_event_handler))
    app.add_handler(CommandHandler('list_events', list_events_handler))
    app.add_handler(CommandHandler('update_event', update_event_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
