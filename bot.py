import logging
import os
import re
import subprocess
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import speech_recognition as sr

# Устанавливаем логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправьте мне видео или голосовое сообщение.')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video = update.message.video
    video_file = await video.get_file()
    video_path = os.path.join('video_storage', f"{video.file_id}.mp4")
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    await video_file.download_to_drive(video_path)

    await transcribe_video_to_text(update, context, video_path)

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_note = update.message.video_note
    video_file = await video_note.get_file()
    video_path = os.path.join('video_storage', f"{video_note.file_id}.mp4")
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    await video_file.download_to_drive(video_path)

    await transcribe_video_to_text(update, context, video_path)

async def transcribe_video_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
    try:
        logger.debug(f'Начинается процесс расшифровки видео в текст: {video_path}')
        status_message = await update.message.reply_text('Начинается процесс расшифровки видео в текст...')
        
        # Извлекаем аудио из видео
        audio_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path]
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        # Получение длительности видео для прогресса
        total_duration = await get_video_duration(video_path)

        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                if status_message.text != f'Конвертация видео в аудио: {percent}%':
                    await status_message.edit_text(f'Конвертация видео в аудио: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.debug(f'Распознанный текст: {text}')

        # Добавление пунктуации
        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка видеосообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(audio_path)
        logger.debug(f'Временный аудиофайл удалён: {audio_path}')

    except Exception as e:
        logger.error(f'Ошибка обработки видеосообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

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
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        total_duration = await get_audio_duration(ogg_path)

        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                if status_message.text != f'Конвертация голосового сообщения: {percent}%':
                    await status_message.edit_text(f'Конвертация голосового сообщения: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.debug(f'Распознанный текст: {text}')

        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка голосового сообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(wav_path)
        logger.debug(f'Временный WAV файл удалён: {wav_path}')

    except Exception as e:
        logger.error(f'Ошибка обработки голосового сообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def get_video_duration(video_path):
    logger.debug(f'Получение длительности видео: {video_path}')
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    duration = float(result.stdout.strip())
    logger.debug(f'Длительность видео: {duration} секунд')
    return duration

async def get_audio_duration(audio_path):
    logger.debug(f'Получение длительности аудио: {audio_path}')
    command = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    duration = float(result.stdout.strip())
    logger.debug(f'Длительность аудио: {duration} секунд')
    return duration

def calculate_progress(current_time, total_duration):
    time_parts = list(map(float, re.split('[:.]', current_time)))
    current_seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2] + time_parts[3] / 100
    percent = int((current_seconds / total_duration) * 100)
    return percent

def add_punctuation(text):
    punctuated_text = re.sub(r'([а-яё])([А-ЯЁ])', r'\1. \2', text)
    punctuated_text = punctuated_text[0].upper() + punctuated_text[1:]
    if not punctuated_text.endswith('.'):
        punctuated_text += '.'
    return punctuated_text

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()

if __name__ == '__main__':
    main()
