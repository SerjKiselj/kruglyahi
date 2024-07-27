import logging
import tempfile
import os
import subprocess
import re
import speech_recognition as sr
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from pydub import AudioSegment

# Настройка логирования
logging.basicConfig(level=logging.INFO)
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
    await update.message.reply_text(
        'Привет! Я бот, который поможет вам с видео и аудио файлами. Отправьте мне видео, видеосообщение или голосовое сообщение, и я предложу, что с ним можно сделать.'
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        video_file = update.message.video.file_id
        file = await context.bot.get_file(video_file)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            video_path = temp_file.name
        
        await file.download_to_drive(video_path)
        logger.info(f'Видео загружено: {video_path}')

        file_size = os.path.getsize(video_path)
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
        logger.error(f'Ошибка обработки видео: {e}')
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        video_note_file = update.message.video_note.file_id
        file = await context.bot.get_file(video_note_file)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            video_path = temp_file.name
        
        await file.download_to_drive(video_path)
        logger.info(f'Видеосообщение загружено: {video_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', wav_path]
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        await update.message.reply_text("Конвертация видеосообщения в аудио...")
        
        progress = 0
        for line in process.stderr:
            logger.info(f'ffmpeg output: {line.strip()}')

            match_out_time = re.search(r'out_time_ms=(\d+)', line)
            match_duration = re.search(r'duration=(\d+)', line)
            if match_out_time and match_duration:
                out_time_ms = int(match_out_time.group(1))
                duration_ms = int(match_duration.group(1))
                new_progress = (out_time_ms / duration_ms) * 100
                if new_progress - progress >= 5:
                    progress = new_progress
                    await update.message.reply_text(f'Конвертация в процессе... Прогресс: {progress:.2f}%')

        process.wait()
        logger.info(f'Конвертация завершена: {wav_path}')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")

        # Добавление пунктуации
        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка видеосообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(video_path)
        os.remove(wav_path)

    except Exception as e:
        logger.error(f'Ошибка обработки видеосообщения: {e}')
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

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
        width, height = await get_video_dimensions(video_path)
        logger.info(f'Размеры исходного видео: {width}x{height}')

        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        output_path = tempfile.mktemp(suffix=".mp4")
        
        command = [
            'ffmpeg', '-i', video_path,
            '-vf', f'crop={crop_size}:{crop_size}:{x_offset}:{y_offset},scale=240:240,setsar=1:1,format=yuv420p',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-b:v', '2M',
            '-c:a', 'aac', '-b:a', '128k', '-shortest',
            '-progress', '-', output_path
        ]

        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        progress = 0
        await query.message.reply_text("Конвертация видео в видеосообщение...")
        for line in process.stderr:
            logger.info(f'ffmpeg output: {line.strip()}')

            match_out_time = re.search(r'out_time_ms=(\d+)', line)
            match_duration = re.search(r'duration=(\d+)', line)
            if match_out_time and match_duration:
                out_time_ms = int(match_out_time.group(1))
                duration_ms = int(match_duration.group(1))
                new_progress = (out_time_ms / duration_ms) * 100
                if new_progress - progress >= 5:
                    progress = new_progress
                    await query.message.reply_text(f'Конвертация в процессе... Прогресс: {progress:.2f}%')

        process.wait()
        logger.info(f'Конвертация завершена: {output_path}')

        with open(output_path, 'rb') as video:
            await query.message.reply_video_note(video)

        os.remove(video_path)
        os.remove(output_path)

        await query.message.reply_text('Конвертация завершена!')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}')
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def create_voice_message_and_send(query: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
    try:
        output_path = tempfile.mktemp(suffix=".ogg")

        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_path]
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        progress = 0
        await query.message.reply_text("Конвертация видео в голосовое сообщение...")
        for line in process.stderr:
            logger.info(f'ffmpeg output: {line.strip()}')

            match_out_time = re.search(r'out_time_ms=(\d+)', line)
            match_duration = re.search(r'duration=(\d+)', line)
            if match_out_time and match_duration:
                out_time_ms = int(match_out_time.group(1))
                duration_ms = int(match_duration.group(1))
                new_progress = (out_time_ms / duration_ms) * 100
                if new_progress - progress >= 5:
                    progress = new_progress
                    await query.message.reply_text(f'Конвертация в процессе... Прогресс: {progress:.2f}%')

        process.wait()
        logger.info(f'Конвертация завершена: {output_path}')

        with open(output_path, 'rb') as audio:
            await query.message.reply_voice(audio)

        os.remove(video_path)
        os.remove(output_path)

        await query.message.reply_text('Конвертация завершена!')

    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}')
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def get_video_dimensions(video_path):
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    width, height = map(int, result.stdout.strip().split('x'))
    return width, height

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == "__main__":
    main()
    
