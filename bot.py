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

    total_duration = await get_video_duration(video_path)

    await create_video_note_and_send(update, context, video_path, total_duration)
    await create_voice_message_and_send(update, context, video_path, total_duration)

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_note = update.message.video_note
    video_file = await video_note.get_file()
    video_path = os.path.join('video_storage', f"{video_note.file_id}.mp4")
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    await video_file.download_to_drive(video_path)

    total_duration = await get_video_duration(video_path)

    await create_video_note_and_send(update, context, video_path, total_duration)
    await create_voice_message_and_send(update, context, video_path, total_duration)

async def create_video_note_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str, total_duration: float) -> None:
    try:
        logger.debug(f'Начинается процесс конвертации видео в видеосообщение: {video_path}')
        status_message = await update.message.reply_text('Начинается процесс конвертации видео в видеосообщение...')
        
        output_path = tempfile.mktemp(suffix=".mp4")
        width, height = await get_video_dimensions(video_path)
        size = min(width, height)
        
        command = ['ffmpeg', '-i', video_path, '-vf', f'scale={size}:{size}:force_original_aspect_ratio=decrease,pad={size}:{size}:(ow-iw)/2:(oh-ih)/2', '-c:v', 'libx264', '-an', output_path]
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                if status_message.text != f'Конвертация видео в видеосообщение: {percent}%':
                    await status_message.edit_text(f'Конвертация видео в видеосообщение: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        with open(output_path, 'rb') as video_note:
            await update.message.reply_video_note(video_note)
        
        os.remove(output_path)
        logger.debug(f'Временный MP4 файл удалён: {output_path}')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def create_voice_message_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str, total_duration: float) -> None:
    try:
        logger.debug(f'Начинается процесс конвертации видео в голосовое сообщение: {video_path}')
        status_message = await update.message.reply_text('Начинается процесс конвертации видео в голосовое сообщение...')
        
        output_path = tempfile.mktemp(suffix=".ogg")
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_path]
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                if status_message.text != f'Конвертация видео в голосовое сообщение: {percent}%':
                    await status_message.edit_text(f'Конвертация видео в голосовое сообщение: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        with open(output_path, 'rb') as audio:
            await update.message.reply_voice(audio)
        
        os.remove(output_path)
        logger.debug(f'Временный OGG файл удалён: {output_path}')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

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
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        total_duration = await get_video_duration(ogg_path)

        # Отображение прогресса
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

        # Добавление пунктуации
        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка голосового сообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(wav_path)
        logger.debug(f'Временный WAV файл удалён: {wav_path}')

    except Exception as e:
        logger.error(f'Ошибка обработки голосового сообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

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
                
