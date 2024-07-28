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
        'Привет! Я бот, который поможет вам с видео и аудио файлами. Отправьте мне видео, видеосообщение или голосовое сообщение, и я предложу, что с ним можно сделать.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("О боте", callback_data='about_bot')]])
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    log_usage(user_id, 'handle_video')
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
    user_id = update.message.from_user.id
    log_usage(user_id, 'handle_video_message')
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
    elif user_id not in user_state:
        await query.edit_message_text(text="Видео не найдено, пожалуйста, отправьте видео ещё раз.")
        return

    video_path = user_state[user_id]

    if query.data == 'video_note':
        await create_video_note_and_send(query, context, video_path)
    elif query.data == 'voice_message':
        await create_voice_message_and_send(query, context, video_path)

async def create_video_note_and_send(query: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
    user_id = query.from_user.id
    log_usage(user_id, 'create_video_note_and_send')
    try:
        logger.debug(f'Начинается процесс конвертации видео в видеосообщение: {video_path}')
        status_message = await query.message.reply_text('Начинается процесс конвертации видео в видеосообщение...')
        
        width, height = await get_video_dimensions(video_path)
        logger.debug(f'Размеры исходного видео: {width}x{height}')

        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        output_path = tempfile.mktemp(suffix=".mp4")
        command = [
            'ffmpeg', '-i', video_path, '-vf', f'crop={crop_size}:{crop_size}:{x_offset}:{y_offset},scale=240:240',
            '-c:v', 'libx264', '-preset', 'slow', '-tune', 'film', '-c:a', 'aac', '-b:a', '128k', '-f', 'mp4', output_path
        ]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видео в видеосообщение: {percent}%')

        await status_message.edit_text('Конвертация завершена!')
        await query.message.reply_video_note(
            video_note=open(output_path, 'rb')
        )
        logger.debug(f'Видеосообщение отправлено: {output_path}')

        os.remove(output_path)
        logger.debug(f'Временный файл видеосообщения удалён: {output_path}')

    except Exception as e:
        logger.error(f'Ошибка конвертации видео в видеосообщение: {e}', exc_info=True)
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def create_voice_message_and_send(query: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
    user_id = query.from_user.id
    log_usage(user_id, 'create_voice_message_and_send')
    try:
        logger.debug(f'Начинается процесс конвертации видео в голосовое сообщение: {video_path}')
        status_message = await query.message.reply_text('Начинается процесс конвертации видео в голосовое сообщение...')

        audio_path = tempfile.mktemp(suffix=".mp3")
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видео в голосовое сообщение: {percent}%')

        await status_message.edit_text('Конвертация завершена!')
        await query.message.reply_voice(voice=open(audio_path, 'rb'))
        logger.debug(f'Голосовое сообщение отправлено: {audio_path}')

        os.remove(audio_path)
        logger.debug(f'Временный файл аудио удалён: {audio_path}')

    except Exception as e:
        logger.error(f'Ошибка конвертации видео в голосовое сообщение: {e}', exc_info=True)
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def get_video_duration(video_path: str) -> float:
    result = subprocess.run(
        ['ffmpeg', '-i', video_path],
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    match = re.search(r'Duration: (\d+):(\d+):(\d+.\d+)', result.stderr)
    if match:
        hours, minutes, seconds = map(float, match.groups())
        return hours * 3600 + minutes * 60 + seconds
    return 0.0

def calculate_progress(current_time: str, total_duration: float) -> int:
    hours, minutes, seconds = map(float, current_time.split(':'))
    current_seconds = hours * 3600 + minutes * 60 + seconds
    percent = int((current_seconds / total_duration) * 100)
    return percent

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    log_usage(user_id, 'handle_voice')
    try:
        logger.debug(f'Получено голосовое сообщение от пользователя {update.message.from_user.id}')
        await update.message.reply_text("Начинается процесс расшифровки голосового сообщения...")
        voice_file = update.message.voice.file_id
        file = await context.bot.get_file(voice_file)

        ogg_path = os.path.join('voice_storage', f"{voice_file}.ogg")
        os.makedirs(os.path.dirname(ogg_path), exist_ok=True)

        await file.download_to_drive(ogg_path)
        logger.info(f'Голосовое сообщение загружено: {ogg_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', ogg_path, wav_path]
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.debug(f'Распознанный текст: {text}')

        # Добавление пунктуации
        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка голосового сообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(wav_path)
        logger.debug(f'Временный WAV файл удалён: {wav_path}')

    except Exception as e:
        logger.error(f'Ошибка обработки голосового сообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

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
