import logging
import tempfile
import subprocess
import os
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне видео, и я конвертирую его в круглое видеосообщение.')

async def get_video_dimensions(video_path: str) -> tuple:
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    output = subprocess.check_output(command).decode().strip().split('\n')
    width, height = int(output[0]), int(output[1])
    return width, height

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Получение файла видео
        video_file = update.message.video.file_id
        file = await context.bot.get_file(video_file)

        # Использование временного файла для загрузки видео
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            video_path = temp_file.name
        
        # Загрузка файла
        await file.download_to_drive(video_path)
        logger.info(f'Видео загружено: {video_path}')

        # Проверка размера файла
        file_size = os.path.getsize(video_path)
        if file_size > 2 * 1024 * 1024 * 1024:  # 2 ГБ
            await update.message.reply_text('Размер видео слишком большой. Пожалуйста, отправьте видео размером менее 2 ГБ.')
            os.remove(video_path)
            return

        # Определение размеров видео
        width, height = await get_video_dimensions(video_path)
        logger.info(f'Размеры исходного видео: {width}x{height}')

        # Определение параметров для обрезки до 1:1
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        # Использование временного файла для 
