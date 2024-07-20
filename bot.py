from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import subprocess

# Ваш токен, полученный от BotFather
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Отправь мне видео, и я конвертирую его в круглое видеосообщение.')

def handle_video(update: Update, context: CallbackContext) -> None:
    video_file = update.message.video.get_file()
    video_path = video_file.download()

    # Конвертация видео в круглое видеосообщение
    output_path = "output.mp4"
    command = [
        'ffmpeg', '-i', video_path, '-vf', 'scale=240:240,setsar=1:1,format=yuv420p', '-c:v', 'libx264', '-an', output_path
    ]
    subprocess.run(command)

    with open(output_path, 'rb') as video:
        update.message.reply_video_note(video)

def main() -> None:
    updater = Updater(TOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.video, handle_video))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
