import logging
import tempfile
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from moviepy.editor import VideoFileClip, vfx

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

        # Загрузка видео с использованием moviepy
        video = VideoFileClip(video_path)

        # Определение размеров видео и обрезка до 1:1
        width, height = video.size
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        # Обрезка и изменение размера видео
        video = video.crop(x1=x_offset, y1=y_offset, x2=x_offset + crop_size, y2=y_offset + crop_size)
        video = video.resize((240, 240))

        # Использование временного файла для выходного видео
        output_path = tempfile.mktemp(suffix=".mp4")

        # Функция для обновления прогресса
        def update_progress(current_time, total_time):
            progress = (current_time / total_time) * 100
            logger.info(f'Прогресс: {progress:.2f}%')
            if update_progress.last_progress is None or progress - update_progress.last_progress >= 1:
                update_progress.last_progress = progress
                context.bot.send_message(chat_id=update.message.chat_id, text=f'Прогресс: {progress:.2f}%')

        update_progress.last_progress = None

        # Сохранение видео с отслеживанием прогресса
        video.write_videofile(output_path, codec='libx264', audio_codec='aac', temp_audiofile='temp-audio.m4a',
                              remove_temp=True, progress_bar=False, logger=None, 
                              verbose=False, threads=4, write_logfile=None, 
                              audio=True, audio_fps=44100,
                              callback=lambda t: update_progress(t, video.duration))

        logger.info(f'Конвертация завершена: {output_path}')

        # Отправка сконвертированного видео
        with open(output_path, 'rb') as video_file:
            await update.message.reply_video_note(video_file)

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
