import logging
import os
import re
import subprocess
import tempfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from pydub import AudioSegment
import speech_recognition as sr
import sqlite3

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('user_stats.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER PRIMARY KEY,
        videos_handled INTEGER,
        video_notes_created INTEGER,
        voice_messages_created INTEGER
    )''')
    conn.commit()
    conn.close()

# Логирование использования
def log_usage(user_id, action):
    conn = sqlite3.connect('user_stats.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO user_stats (user_id, videos_handled, video_notes_created, voice_messages_created) VALUES (?, 0, 0, 0)', (user_id,))
    if action == 'handle_video':
        c.execute('UPDATE user_stats SET videos_handled = videos_handled + 1 WHERE user_id = ?', (user_id,))
    elif action == 'video_note':
        c.execute('UPDATE user_stats SET video_notes_created = video_notes_created + 1 WHERE user_id = ?', (user_id,))
    elif action == 'voice_message':
        c.execute('UPDATE user_stats SET voice_messages_created = voice_messages_created + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Получение статистики пользователя
def get_user_stats(user_id):
    conn = sqlite3.connect('user_stats.db')
    c = conn.cursor()
    c.execute('SELECT videos_handled, video_notes_created, voice_messages_created FROM user_stats WHERE user_id = ?', (user_id,))
    stats = c.fetchone()
    conn.close()
    return stats if stats else (0, 0, 0)

def add_punctuation(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    punctuated_text = '. '.join([sentence.capitalize() for sentence in sentences])
    return punctuated_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug(f'Команда /start от пользователя {update.message.from_user.id}')
    keyboard = [
        [
            InlineKeyboardButton("О боте", callback_data='about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Привет! Я бот, который поможет вам с видео и аудио файлами. Отправьте мне видео, видеосообщение или голосовое сообщение, и я предложу, что с ним можно сделать.',
        reply_markup=reply_markup
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Статистика", callback_data='stats'),
            InlineKeyboardButton("Назад", callback_data='back_to_about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=(
            "Я бот, который может:\n"
            "- Преобразовывать видео в видеосообщения\n"
            "- Преобразовывать видео в голосовые сообщения\n"
            "- Расшифровывать аудио и видеосообщения в текст"
        ),
        reply_markup=reply_markup
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    stats = get_user_stats(user_id)
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Назад", callback_data='back_to_about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=(
            f"Ваша статистика использования:\n"
            f"- Обработанных видео: {stats[0]}\n"
            f"- Создано видеосообщений: {stats[1]}\n"
            f"- Создано голосовых сообщений: {stats[2]}"
        ),
        reply_markup=reply_markup
    )

async def back_to_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await about(update, context)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено видео от пользователя {update.message.from_user.id}')
        video_file = update.message.video.file_id
        file = await context.bot.get_file(video_file)

        video_path = os.path.join('video_storage', f"{video_file}.mp4")
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        await file.download_to_drive(video_path)
        logger.info(f'Видео загружено: {video_path}')

        file_size = os.path.getsize(video_path)
        logger.debug(f'Размер видео: {file_size} байт')
        if file_size > 2 * 1024 * 1024 * 1024:  # 2 ГБ
            await update.message.reply_text('Размер видео слишком большой. Пожалуйста, отправьте видео размером менее 2 ГБ.')
            os.remove(video_path)
            return

        log_usage(update.message.from_user.id, 'handle_video')

        user_state[update.message.from_user.id] = video_path

        keyboard = [
            [
                InlineKeyboardButton("Сделать видеосообщение", callback_data='video_note'),
                InlineKeyboardButton("Сделать голосовое сообщение", callback_data='voice_message')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Что вы хотите сделать с видео?', reply_markup=reply_markup)

    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено видеосообщение от пользователя {update.message.from_user.id}')
        await update.message.reply_text("Начинается процесс конвертации видеосообщения в аудио...")
        video_note_file = update.message.video_note.file_id
        file = await context.bot.get_file(video_note_file)

        video_path = os.path.join('video_storage', f"{video_note_file}.mp4")
        os.makedirs(os.path.dirname(video_path), exist_ok=True)

        await file.download_to_drive(video_path)
        logger.info(f'Видеосообщение загружено: {video_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', wav_path]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        status_message = await update.message.reply_text('Начинается процесс конвертации видеосообщения в аудио...')
        
        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видеосообщения в аудио: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.debug(f'Распознанный текст: {text}')

        # Добавление пунктуации
        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка видеосообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(wav_path)
        logger.debug(f'Временный WAV файл удалён: {wav_path}')

    except Exception as e:
        logger.error(f'Ошибка обработки видеосообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

    logger.debug(f'Получен запрос кнопки от пользователя {user_id}: {query.data}')

    if query.data == 'about':
        await about(update, context)
    elif query.data == 'stats':
        await stats(update, context)
    elif query.data == 'back_to_about':
        await back_to_about(update, context)
    elif query.data == 'video_note':
        video_path = user_state.get(user_id)
        if video_path:
            await query.edit_message_text(text='Начинаю создание видеосообщения...')
            await create_video_note_from_video(video_path, user_id, query)
        else:
            await query.edit_message_text(text='Видео не найдено. Пожалуйста, отправьте видео сначала.')
    elif query.data == 'voice_message':
        video_path = user_state.get(user_id)
        if video_path:
            await query.edit_message_text(text='Начинаю создание голосового сообщения...')
            await create_voice_message_from_video(video_path, user_id, query)
        else:
            await query.edit_message_text(text='Видео не найдено. Пожалуйста, отправьте видео сначала.')

def calculate_progress(current_time, total_duration):
    current_hours, current_minutes, current_seconds = map(float, current_time.split(':'))
    current_total_seconds = current_hours * 3600 + current_minutes * 60 + current_seconds

    total_hours, total_minutes, total_seconds = map(float, total_duration.split(':'))
    total_total_seconds = total_hours * 3600 + total_minutes * 60 + total_seconds

    percent = (current_total_seconds / total_total_seconds) * 100
    return round(percent, 2)

async def get_video_duration(video_path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = float(result.stdout)
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}:{int(minutes)}:{int(seconds)}"

async def create_video_note_from_video(video_path, user_id, query):
    output_path = os.path.join('video_storage', f"{user_id}_video_note.mp4")
    command = ['ffmpeg', '-i', video_path, '-vf', 'scale=320:320', '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '128k', '-y', output_path]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    process.wait()

    if process.returncode == 0:
        log_usage(user_id, 'video_note')
        with open(output_path, 'rb') as video_note_file:
            await query.message.reply_video_note(video_note_file)
        os.remove(output_path)
    else:
        await query.message.reply_text('Не удалось создать видеосообщение.')

async def create_voice_message_from_video(video_path, user_id, query):
    output_path = os.path.join('video_storage', f"{user_id}_voice_message.ogg")
    command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', '-c:a', 'libopus', '-b:a', '128k', '-y', output_path]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    process.wait()

    if process.returncode == 0:
        log_usage(user_id, 'voice_message')
        with open(output_path, 'rb') as voice_message_file:
            await query.message.reply_voice(voice_message_file)
        os.remove(output_path)
    else:
        await query.message.reply_text('Не удалось создать голосовое сообщение.')

def main() -> None:
    init_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
