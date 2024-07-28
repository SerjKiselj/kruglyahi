import logging
import os
import re
import subprocess
import tempfile
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from pydub import AudioSegment
import speech_recognition as sr

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

# Хранение состояния пользователя
user_state = {}

def init_db():
    conn = sqlite3.connect('bot_usage.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_usage(user_id, command):
    conn = sqlite3.connect('bot_usage.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO usage_log (user_id, command) VALUES (?, ?)
    ''', (user_id, command))
    conn.commit()
    conn.close()

def get_user_statistics(user_id):
    conn = sqlite3.connect('bot_usage.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT command, COUNT(*) as count 
        FROM usage_log 
        WHERE user_id = ?
        GROUP BY command 
        ORDER BY count DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def add_punctuation(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    punctuated_text = '. '.join([sentence.capitalize() for sentence in sentences])
    return punctuated_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    log_usage(user_id, '/start')
    await update.message.reply_text(
        'Привет! Я бот, который поможет вам с видео и аудио файлами. Отправьте мне видео, видеосообщение или голосовое сообщение, и я предложу, что с ним можно сделать.'
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    log_usage(user_id, 'handle_video')
    # остальной код обработки видео

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    log_usage(user_id, 'handle_voice')
    # остальной код обработки голосового сообщения

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    log_usage(user_id, 'handle_video_message')
    # остальной код обработки видеосообщения

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

    logger.debug(f'Получен запрос кнопки от пользователя {user_id}: {query.data}')

    if query.data == 'about_bot':
        keyboard = [
            [InlineKeyboardButton("Статистика", callback_data='user_stats')],
            [InlineKeyboardButton("Назад", callback_data='about_bot')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text='Я бот, который помогает с видео и аудио файлами. Я могу конвертировать видео в аудио, видеосообщения и голосовые сообщения, а также расшифровывать их в текст.',
            reply_markup=reply_markup
        )
    elif query.data == 'user_stats':
        stats = get_user_statistics(user_id)
        stats_text = "Ваша статистика использования бота:\n\n"
        for command, count in stats:
            stats_text += f"Команда {command}: {count} раз(а)\n"
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data='about_bot')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=stats_text, reply_markup=reply_markup)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Статистика", callback_data='user_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Я бот, который помогает с видео и аудио файлами. Я могу конвертировать видео в аудио, видеосообщения и голосовые сообщения, а также расшифровывать их в текст.',
        reply_markup=reply_markup
    )

def main() -> None:
    init_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(CallbackQueryHandler(button))

    logger.info('Бот запущен')
    application.run_polling()

if __name__ == '__main__':
    main()
