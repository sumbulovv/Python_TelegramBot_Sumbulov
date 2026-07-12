from telegram import Update
from telegram.ext import ContextTypes
from notes import create_note, read_note, edit_note, delete_note, display_notes, display_sorted_notes

async def create_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        note_text = " ".join(context.args)
        note_name = str(update.effective_chat.id)
        result = create_note(note_name, note_text)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Заметка создана.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def read_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        note_name = str(update.effective_chat.id)
        result = read_note(note_name)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Заметка не найдена.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def edit_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        note_name = str(update.effective_chat.id)
        note_text = " ".join(context.args)
        result = edit_note(note_name, note_text)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Заметка не найдена.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def delete_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        note_name = str(update.effective_chat.id)
        result = delete_note(note_name)
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Заметка не найдена.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def display_notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        result = display_notes()
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Список заметок: \n" + "\n".join(result))
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Заметки не найдены.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")
        
async def display_notes_reverse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        result = display_sorted_notes()
        if result:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Список заметок в обратном порядке: \n" + "\n".join(result))
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Заметки не найдены.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Что-то пошло не так. Попробуйте еще раз.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю.")