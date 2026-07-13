import os
import logging
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Application
from tg_handlers import (
    start, 
    create_event_handler,
    get_event_handler,
    delete_event_handler,
    list_events_handler,
    update_event_handler
    )

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Telegram bot")
    app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler('create_event', create_event_handler))
    app.add_handler(CommandHandler('get_event', get_event_handler))
    app.add_handler(CommandHandler('delete_event', delete_event_handler))
    app.add_handler(CommandHandler('list_events', list_events_handler))
    app.add_handler(CommandHandler('update_event', update_event_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
