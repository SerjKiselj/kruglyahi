import asyncio
import os
import tempfile
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import speech_recognition as sr
import re
import ffmpeg

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Отправь мне видео или голосовое сообщение, и я обработаю его для тебя."
    )

async def convert_video_to_video_message(video_path, output_path, update_progress):
    try:
        # Получаем продолжительность видео
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])

        # Начинаем процесс конвертации
        process = (
            ffmpeg
            .input(video_path)
            .filter('scale', 640, 640, force_original_aspect_ratio='increase')
            .filter('crop', 640, 640)
            .output(output_path, vcodec='libx264', preset='fast')
            .global_args('-y')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        for percentage in range(0, 101, 10):
            await update_progress(percentage)
            await asyncio.sleep(duration / 10)

        process.wait()

    except Exception as e:
        logger.error(f'Ошибка конвертации видео: {e}', exc_info=True)
        raise

async def convert_video_to_voice(video_path, output_path, update_progress):
    try:
        # Получаем продолжительность видео
        probe = ffmpeg.probe(video_path)
        duration = float(probe['format']['duration'])

        # Начинаем процесс конвертации
        process = (
            ffmpeg
            .input(video_path)
            .output(output_path, acodec='libopus', audio_bitrate='64k', vn=None)
            .global_args('-y')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        for percentage in range(0, 101, 10):
            await update_progress(percentage)
            await asyncio.sleep(duration / 10)

        process.wait()

    except Exception as e:
        logger.error(f'Ошибка конвертации видео в голос: {e}', exc_info=True)
        raise

async def handle_video(update: Update, context: CallbackContext):
    video_file = await update.message.video.get_file()
    video_path = tempfile.mktemp(suffix='.mp4')
    await video_file.download_to_drive(video_path)
    video_message_path = tempfile.mktemp(suffix='.mp4')
    voice_message_path = tempfile.mktemp(suffix='.ogg')

    async def update_progress(percentage):
        await update.message.reply_text(f'Конвертация видеосообщения: {percentage}%')

    try:
        await update.message.reply_text("Начинается процесс конвертации видео в видеосообщение...")
        await convert_video_to_video_message(video_path, video_message_path, update_progress)
        await update.message.reply_video(video_message_path)
        await update.message.reply_text("Конвертация видеосообщения завершена!")
    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка: {e}')
    finally:
        os.remove(video_path)
        if os.path.exists(video_message_path):
            os.remove(video_message_path)

    async def update_voice_progress(percentage):
        await update.message.reply_text(f'Конвертация видео в голос: {percentage}%')

    try:
        await update.message.reply_text("Начинается процесс конвертации видео в голосовое сообщение...")
        await convert_video_to_voice(video_path, voice_message_path, update_voice_progress)
        await update.message.reply_voice(voice_message_path)
        await update.message.reply_text("Конвертация видео в голосовое сообщение завершена!")
    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка: {e}')
    finally:
        if os.path.exists(voice_message_path):
            os.remove(voice_message_path)

async def handle_video_message(update: Update, context: CallbackContext):
    video_file = await update.message.video_note.get_file()
    video_path = tempfile.mktemp(suffix='.mp4')
    await video_file.download_to_drive(video_path)
    voice_message_path = tempfile.mktemp(suffix='.ogg')

    async def update_progress(percentage):
        await update.message.reply_text(f'Конвертация видеосообщения в аудио: {percentage}%')

    try:
        await update.message.reply_text("Начинается процесс конвертации видеосообщения в аудио...")
        await convert_video_to_voice(video_path, voice_message_path, update_progress)
        await update.message.reply_voice(voice_message_path)
        await update.message.reply_text("Конвертация видеосообщения в аудио завершена!")
    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка: {e}')
    finally:
        os.remove(video_path)
        if os.path.exists(voice_message_path):
            os.remove(voice_message_path)

async def handle_voice(update: Update, context: CallbackContext):
    voice_file = await update.message.voice.get_file()
    voice_path = tempfile.mktemp(suffix='.ogg')
    await voice_file.download_to_drive(voice_path)
    wav_path = tempfile.mktemp(suffix='.wav')

    recognizer = sr.Recognizer()
    async def update_progress(percentage):
        await update.message.reply_text(f'Конвертация голосового сообщения: {percentage}%')

    try:
        await update.message.reply_text("Начинается процесс конвертации голосового сообщения...")
        
        # Конвертация OGG в WAV
        ffmpeg.input(voice_path).output(wav_path, ar=16000, ac=1).run()
        
        for percentage in range(0, 101, 10):
            await update_progress(percentage)
            await asyncio.sleep(0.1)  # Примерное время обработки для демонстрации прогресса

        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU")
            text = add_punctuation(text)
        
        await update.message.reply_text(f'Расшифровка голосового сообщения: {text}')
    except Exception as e:
        logger.error(f'Ошибка обработки голосового сообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')
    finally:
        os.remove(voice_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

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
