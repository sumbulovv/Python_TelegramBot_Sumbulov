import os
from dotenv import load_dotenv
from telegram.ext import CommandHandler, Application
from tg_handlers import (
    create_note_handler, 
    start, 
    read_note_handler, 
    edit_note_handler, 
    delete_note_handler, 
    display_notes_handler, 
    display_notes_reverse_handler
    )

load_dotenv()

def main():
    app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler('create', create_note_handler))
    app.add_handler(CommandHandler('read', read_note_handler))
    app.add_handler(CommandHandler('edit', edit_note_handler))
    app.add_handler(CommandHandler('delete', delete_note_handler))
    app.add_handler(CommandHandler('display', display_notes_handler))
    app.add_handler(CommandHandler('display_reverse', display_notes_reverse_handler))

    app.run_polling()


if __name__ == "__main__":
    main()