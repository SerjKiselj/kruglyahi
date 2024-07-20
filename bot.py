from telegram import Update, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import subprocess
import os

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне видео, и я конвертирую его в круглое видеосообщение.')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_file = await update.message.video.get_file()
    video_path = await video_file.download()

    # Проверка размера файла
    file_size = os.path.getsize(video_path)
    if file_size > 2 * 1024 * 1024 * 1024:  # 2 ГБ
        await update.message.reply_text('Размер видео слишком большой. Пожалуйста, отправьте видео размером менее 2 ГБ.')
        return

    # Отправка сообщения о начале конвертации
    await update.message.reply_text('Начинаю конвертацию видео, это может занять некоторое время...')
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VIDEO_NOTE)

    # Конвертация видео в круглое видеосообщение
    output_path = "output.mp4"
    command = [
        'ffmpeg', '-i', video_path, '-vf', 'scale=240:240,setsar=1:1,format=yuv420p', '-c:v', 'libx264', '-an', output_path
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f'Ошибка при конвертации видео: {e}')
        return

    # Отправка сконвертированного видео
    with open(output_path, 'rb') as video:
        await update.message.reply_video_note(video)

    # Очистка временных файлов
    os.remove(video_path)
    os.remove(output_path)

    # Сообщение о завершении
    await update.message.reply_text('Конвертация завершена!')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))

    application.run_polling()

if __name__ == '__main__':
    main()
