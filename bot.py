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

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

# Хранение состояния пользователя
user_state = {}

def add_punctuation(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    punctuated_text = '. '.join([sentence.capitalize() for sentence in sentences])
    return punctuated_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug(f'Команда /start от пользователя {update.message.from_user.id}')
    await update.message.reply_text(
        'Привет! Я бот, который поможет вам с видео и аудио файлами. Отправьте мне видео, видеосообщение или голосовое сообщение, и я предложу, что с ним можно сделать.'
    )

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
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        logger.debug(f'Видео конвертировано в WAV: {wav_path}')

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

    if user_id not in user_state:
        await query.edit_message_text(text="Видео не найдено, пожалуйста, отправьте видео ещё раз.")
        return

    video_path = user_state[user_id]

    if query.data == 'video_note':
        await create_video_note_and_send(query, context, video_path)
    elif query.data == 'voice_message':
        await create_voice_message_and_send(query, context, video_path)

async def create_video_note_and_send(query: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
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
            'ffmpeg', '-i', video_path,
            '-vf', f'crop={crop_size}:{crop_size}:{x_offset}:{y_offset},scale=240:240,setsar=1:1,format=yuv420p',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-b:v', '2M',
            '-c:a', 'aac', '-b:a', '128k', '-shortest',
            output_path
        ]

        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        
        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видео в видеосообщение: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        with open(output_path, 'rb') as video:
            await query.message.reply_video_note(video)

        os.remove(output_path)
        logger.debug(f'Временный MP4 файл удалён: {output_path}')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}', exc_info=True)
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def create_voice_message_and_send(query: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
    try:
        logger.debug(f'Начинается процесс конвертации видео в голосовое сообщение: {video_path}')
        status_message = await query.message.reply_text('Начинается процесс конвертации видео в голосовое сообщение...')
        
        output_path = tempfile.mktemp(suffix=".ogg")

        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_path]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видео в голосовое сообщение: {percent}%')

        await status_message.edit_text('Создание голосового сообщения завершено!')

        with open(output_path, 'rb') as audio:
            await query.message.reply_voice(audio)

        os.remove(output_path)
        logger.debug(f'Временный OGG файл удалён: {output_path}')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}', exc_info=True)
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def get_video_dimensions(video_path):
    logger.debug(f'Получение размеров видео: {video_path}')
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0:s=x', video_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    width, height = map(int, result.stdout.strip().split('x'))
    logger.debug(f'Полученные размеры видео: {width}x{height}')
    return width, height

async def get_video_duration(video_path):
    logger.debug(f'Получение длительности видео: {video_path}')
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    duration = float(result.stdout.strip())
    logger.debug(f'Длительность видео: {duration} секунд')
    return duration

def calculate_progress(current_time, total_duration):
    time_parts = list(map(float, re.split('[:.]', current_time)))
    current_seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2] + time_parts[3] / 100
    percent = int((current_seconds / total_duration) * 100)
    return percent

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено голосовое сообщение от пользователя {update.message.from_user.id}')
        status_message = await update.message.reply_text('Начинается процесс конвертации голосового сообщения...')

        voice_file = update.message.voice.file_id
        file = await context.bot.get_file(voice_file)

        ogg_path = os.path.join('audio_storage', f"{voice_file}.ogg")
        os.makedirs(os.path.dirname(ogg_path), exist_ok=True)

        await file.download_to_drive(ogg_path)
        logger.info(f'Голосовое сообщение загружено: {ogg_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', ogg_path, wav_path]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        logger.debug(f'Голосовое сообщение конвертировано в WAV: {wav_path}')

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
        logger.error(f'Ошибка распознавания голоса: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(CallbackQueryHandler(button))

    logger.info('Бот запущен')
    application.run_polling()

if __name__ == '__main__':
    main()
    
