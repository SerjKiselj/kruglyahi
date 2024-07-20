import logging
import tempfile
import subprocess
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне видео, и я конвертирую его в круглое видеосообщение.')

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

        # Отправка сообщения о начале конвертации
        await update.message.reply_text('Начинаю конвертацию видео, это может занять некоторое время...')

        # Использование временного файла для выходного видео
        output_path = tempfile.mktemp(suffix=".mp4")
        command = [
            'ffmpeg', '-i', video_path, '-vf', 'scale=240:240,setsar=1:1,format=yuv420p,fps=60',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-an', output_path
        ]

        # Асинхронный запуск конвертации
        await asyncio.to_thread(subprocess.run, command, check=True)
        logger.info(f'Конвертация завершена: {output_path}')

        # Отправка сконвертированного видео
        with open(output_path, 'rb') as video:
            await update.message.reply_video_note(video)

        # Очистка временных файлов
        os.remove(video_path)
        os.remove(output_path)

        # Сообщение о завершении
        await update.message.reply_text('Конвертация завершена!')
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}')
        await update.message.reply_text(f'Произошла ошибка: {e}')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))

    application.run_polling()

if __name__ == '__main__':
    main()
