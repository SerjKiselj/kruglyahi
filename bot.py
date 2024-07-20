from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import subprocess

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне видео, и я конвертирую его в круглое видеосообщение.')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_file = await update.message.video.get_file()
    video_path = video_file.file_path

    # Конвертация видео в круглое видеосообщение
    output_path = "output.mp4"
    command = [
        'ffmpeg', '-i', video_path, '-vf', 'scale=240:240,setsar=1:1,format=yuv420p', '-c:v', 'libx264', '-an', output_path
    ]
    subprocess.run(command)

    with open(output_path, 'rb') as video:
        await update.message.reply_video_note(video)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))

    application.run_polling()

if __name__ == '__main__':
    main()
