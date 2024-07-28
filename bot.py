import logging
import os
import tempfile
import re
import subprocess
import speech_recognition as sr
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

user_stats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Я бот для обработки видео и аудио сообщений. Что вы хотите сделать?',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("О боте", callback_data='about')]
        ])
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.message.reply_text(
        'Я бот, который помогает конвертировать видео в видеосообщения и голосовые сообщения, '
        'а также расшифровывать видеосообщения и голосовые сообщения в текст.',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Статистика", callback_data='statistics')]
        ])
    )

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    stats = user_stats.get(user_id, {
        'video_to_note': 0,
        'video_to_voice': 0,
        'video_note_to_text': 0,
        'voice_to_text': 0
    })
    await update.callback_query.message.edit_text(
        f"Ваша статистика:\n\n"
        f"Конвертировано видео в видеосообщения: {stats['video_to_note']}\n"
        f"Конвертировано видео в голосовые сообщения: {stats['video_to_voice']}\n"
        f"Расшифровано видеосообщений: {stats['video_note_to_text']}\n"
        f"Расшифровано голосовых сообщений: {stats['voice_to_text']}"
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Что вы хотите сделать с видео?',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Сделать видеосообщение", callback_data='video_note')],
            [InlineKeyboardButton("Сделать голосовое сообщение", callback_data='voice_message')]
        ])
    )

    # Сохранение пути к видеофайлу в контексте пользователя
    video_file = update.message.video.file_id
    file = await context.bot.get_file(video_file)
    video_path = os.path.join('video_storage', f"{video_file}.mp4")
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    await file.download_to_drive(video_path)
    context.user_data['video_path'] = video_path

async def create_video_note_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_path = context.user_data.get('video_path')
    if not video_path:
        await update.callback_query.message.reply_text('Ошибка: путь к видеофайлу не найден.')
        return

    try:
        user_id = update.callback_query.from_user.id
        logger.debug(f'Создание видеосообщения для пользователя {user_id} из видео {video_path}')
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        command = [
            'ffmpeg', '-i', video_path, '-vf', 'scale=240:240,setsar=1:1',
            '-an', '-vcodec', 'libx264', '-crf', '23', '-preset', 'veryfast', temp_file.name
        ]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        status_message = await update.callback_query.message.reply_text('Начинается процесс создания видеосообщения...')
        
        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Создание видеосообщения: {percent}%')

        await status_message.edit_text('Создание завершено!')
        await context.bot.send_video_note(
            chat_id=user_id,
            video_note=open(temp_file.name, 'rb')
        )
        os.remove(temp_file.name)
        logger.debug(f'Временный файл видеосообщения удалён: {temp_file.name}')

        # Обновление статистики
        if user_id not in user_stats:
            user_stats[user_id] = {
                'video_to_note': 0,
                'video_to_voice': 0,
                'video_note_to_text': 0,
                'voice_to_text': 0
            }
        user_stats[user_id]['video_to_note'] += 1

    except Exception as e:
        logger.error(f'Ошибка создания видеосообщения: {e}', exc_info=True)
        await update.callback_query.message.reply_text(f'Произошла ошибка: {e}')

async def create_voice_message_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video_path = context.user_data.get('video_path')
    if not video_path:
        await update.callback_query.message.reply_text('Ошибка: путь к видеофайлу не найден.')
        return

    try:
        user_id = update.callback_query.from_user.id
        logger.debug(f'Создание голосового сообщения для пользователя {user_id} из видео {video_path}')
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        command = [
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'libopus', temp_file.name
        ]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        status_message = await update.callback_query.message.reply_text('Начинается процесс создания голосового сообщения...')
        
        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Создание голосового сообщения: {percent}%')

        await status_message.edit_text('Создание завершено!')
        await context.bot.send_voice(
            chat_id=user_id,
            voice=open(temp_file.name, 'rb')
        )
        os.remove(temp_file.name)
        logger.debug(f'Временный файл голосового сообщения удалён: {temp_file.name}')

        # Обновление статистики
        if user_id not in user_stats:
            user_stats[user_id] = {
                'video_to_note': 0,
                'video_to_voice': 0,
                'video_note_to_text': 0,
                'voice_to_text': 0
            }
        user_stats[user_id]['video_to_voice'] += 1

    except Exception as e:
        logger.error(f'Ошибка создания голосового сообщения: {e}', exc_info=True)
        await update.callback_query.message.reply_text(f'Произошла ошибка: {e}')

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено голосовое сообщение от пользователя {update.message.from_user.id}')
        voice_file = update.message.voice.file_id
        file = await context.bot.get_file(voice_file)

        ogg_path = os.path.join('voice_storage', f"{voice_file}.ogg")
        os.makedirs(os.path.dirname(ogg_path), exist_ok=True)
        
        await file.download_to_drive(ogg_path)
        logger.info(f'Голосовое сообщение загружено: {ogg_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', ogg_path, wav_path]
        total_duration = await get_video_duration(ogg_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        status_message = await update.message.reply_text('Начинается процесс конвертации голосового сообщения в текст...')

        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация голосового сообщения в текст: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language="ru-RU")
        text = add_punctuation(text)
        await update.message.reply_text(f'Расшифровка: {text}')

        user_id = update.message.from_user.id
        if user_id not in user_stats:
            user_stats[user_id] = {
                'video_to_note': 0,
                'video_to_voice': 0,
                'video_note_to_text': 0,
                'voice_to_text': 0
            }
        user_stats[user_id]['voice_to_text'] += 1

        os.remove(ogg_path)
        os.remove(wav_path)
        logger.debug(f'Временные файлы удалены: {ogg_path}, {wav_path}')

    except Exception as e:
        logger.error(f'Ошибка расшифровки голосового сообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено видеосообщение от пользователя {update.message.from_user.id}')
        video_note_file = update.message.video_note.file_id
        file = await context.bot.get_file(video_note_file)

        video_note_path = os.path.join('video_note_storage', f"{video_note_file}.mp4")
        os.makedirs(os.path.dirname(video_note_path), exist_ok=True)
        
        await file.download_to_drive(video_note_path)
        logger.info(f'Видеосообщение загружено: {video_note_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', video_note_path, '-vn', wav_path]
        total_duration = await get_video_duration(video_note_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        status_message = await update.message.reply_text('Начинается процесс конвертации видеосообщения в текст...')

        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видеосообщения в текст: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language="ru-RU")
        text = add_punctuation(text)
        await update.message.reply_text(f'Расшифровка: {text}')

        user_id = update.message.from_user.id
        if user_id not in user_stats:
            user_stats[user_id] = {
                'video_to_note': 0,
                'video_to_voice': 0,
                'video_note_to_text': 0,
                'voice_to_text': 0
            }
        user_stats[user_id]['video_note_to_text'] += 1

        os.remove(video_note_path)
        os.remove(wav_path)
        logger.debug(f'Временные файлы удалены: {video_note_path}, {wav_path}')

    except Exception as e:
        logger.error(f'Ошибка расшифровки видеосообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

def add_punctuation(text: str) -> str:
    # Простая реализация добавления пунктуации
    return text.capitalize() + '.'

async def get_video_duration(path: str) -> str:
    result = subprocess.run(['ffmpeg', '-i', path], stderr=subprocess.PIPE, universal_newlines=True)
    match = re.search(r'Duration: (\d+:\d+:\d+.\d+)', result.stderr)
    return match.group(1) if match else '0:00:00.0'

def calculate_progress(current_time: str, total_time: str) -> int:
    current_time_parts = list(map(float, current_time.split(":")))
    total_time_parts = list(map(float, total_time.split(":")))
    
    current_seconds = current_time_parts[0] * 3600 + current_time_parts[1] * 60 + current_time_parts[2]
    total_seconds = total_time_parts[0] * 3600 + total_time_parts[1] * 60 + total_time_parts[2]
    
    return int((current_seconds / total_seconds) * 100)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(about, pattern='about'))
    application.add_handler(CallbackQueryHandler(statistics, pattern='statistics'))
    application.add_handler(MessageHandler(filters.Regex("О боте"), about))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(CallbackQueryHandler(create_video_note_and_send, pattern='video_note'))
    application.add_handler(CallbackQueryHandler(create_voice_message_and_send, pattern='voice_message'))

    application.run_polling()

if __name__ == '__main__':
    main()
