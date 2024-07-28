import logging
import os
import re
import subprocess
import tempfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from pydub import AudioSegment
import speech_recognition as sr

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ваш токен, полученный от BotFather
TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

# Хранение состояния пользователя и статистики
user_state = {}
user_stats = {}

def add_punctuation(text):
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    punctuated_text = '. '.join([sentence.capitalize() for sentence in sentences])
    return punctuated_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug(f'Команда /start от пользователя {update.message.from_user.id}')
    await update.message.reply_text(
        'Привет! Я бот, который поможет вам с видео и аудио файлами. Отправьте мне видео, видеосообщение или голосовое сообщение, и я предложу, что с ним можно сделать.',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("О боте", callback_data='about')],
            [InlineKeyboardButton("Топ пользователей", callback_data='top')]
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
        'voice_to_text': 0,
        'points': 0
    })
    await update.callback_query.message.edit_text(
        f"Ваша статистика:\n\n"
        f"Конвертировано видео в видеосообщения: {stats['video_to_note']}\n"
        f"Конвертировано видео в голосовые сообщения: {stats['video_to_voice']}\n"
        f"Расшифровано видеосообщений: {stats['video_note_to_text']}\n"
        f"Расшифровано голосовых сообщений: {stats['voice_to_text']}\n"
        f"Очки: {stats['points']}"
    )

async def top_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['points'], reverse=True)
    top_users_text = "Топ пользователей:\n\n"
    for i, (user_id, stats) in enumerate(sorted_users[:10], start=1):
        user = await context.bot.get_chat(user_id)
        top_users_text += f"{i}. {user.full_name} - {stats['points']} очков\n"

    await update.callback_query.message.reply_text(top_users_text)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено видео от пользователя {update.message.from_user.id}')
        video_file = update.message.video.file_id
        file = await context.bot.get_file(video_file)

        video_path = os.path.join('video_storage', f"{video_file}.mp4")
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        await file.download_to_drive(video_path)
        logger.info(f'Видео загружено: {video_path}')

        file_size = os.path.getsize(video_path)
        logger.debug(f'Размер видео: {file_size} байт')
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
        logger.error(f'Ошибка обработки видео: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено видеосообщение от пользователя {update.message.from_user.id}')
        await update.message.reply_text("Начинается процесс конвертации видеосообщения в аудио...")
        video_note_file = update.message.video_note.file_id
        file = await context.bot.get_file(video_note_file)

        video_path = os.path.join('video_storage', f"{video_note_file}.mp4")
        os.makedirs(os.path.dirname(video_path), exist_ok=True)

        await file.download_to_drive(video_path)
        logger.info(f'Видеосообщение загружено: {video_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', wav_path]
        total_duration = await get_video_duration(video_path)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        status_message = await update.message.reply_text('Начинается процесс конвертации видеосообщения в аудио...')
        
        # Отображение прогресса
        while process.poll() is None:
            output = process.stderr.readline()
            match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
            if match:
                current_time = match.group(1)
                percent = calculate_progress(current_time, total_duration)
                await status_message.edit_text(f'Конвертация видеосообщения в аудио: {percent}%')

        await status_message.edit_text('Конвертация завершена!')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.debug(f'Распознанный текст: {text}')

        # Добавление пунктуации
        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка видеосообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(wav_path)
        logger.debug(f'Временный WAV файл удалён: {wav_path}')

        user_id = update.message.from_user.id
        if user_id not in user_stats:
            user_stats[user_id] = {
                'video_to_note': 0,
                'video_to_voice': 0,
                'video_note_to_text': 0,
                'voice_to_text': 0,
                'points': 0
            }
        user_stats[user_id]['video_note_to_text'] += 1
        user_stats[user_id]['points'] += 1

    except Exception as e:
        logger.error(f'Ошибка обработки видеосообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()

    logger.debug(f'Получен запрос кнопки от пользователя {user_id}: {query.data}')

    if user_id not in user_state:
        await query.edit_message_text(text="Видео не найдено, пожалуйста, отправьте видео ещё раз.")
        return

    video_path = user_state[user_id]

    if query.data == 'video_note':
        await create_video_note_and_send(query, context, video_path)
    elif query.data == 'voice_message':
        await create_voice_message_and_send(query, context, video_path)
    elif query.data == 'top':
        await top_users(update, context)

async def create_video_note_and_send(query, context, video_path):
    try:
        video_note_path = os.path.join('video_storage', f"{os.path.basename(video_path)}_note.mp4")

        command = [
            'ffmpeg', '-i', video_path, '-vf', 'scale=240:240', '-c:v', 'libx264', '-crf', '23',
            '-preset', 'ultrafast', '-c:a', 'aac', '-strict', 'experimental', '-r', '30', '-b:a', '64k',
            video_note_path
        ]
        subprocess.run(command, check=True)
        logger.info(f'Видеосообщение создано: {video_note_path}')

        await context.bot.send_video_note(
            chat_id=query.message.chat_id,
            video_note=open(video_note_path, 'rb')
        )
        await query.edit_message_text(text="Ваше видео было успешно конвертировано в видеосообщение.")

        user_id = query.from_user.id
        user_stats[user_id]['video_to_note'] += 1
        user_stats[user_id]['points'] += 1

    except Exception as e:
        logger.error(f'Ошибка при создании видеосообщения: {e}', exc_info=True)
        await query.edit_message_text(text=f'Произошла ошибка: {e}')

async def create_voice_message_and_send(query, context, video_path):
    try:
        voice_message_path = os.path.join('video_storage', f"{os.path.basename(video_path)}.ogg")

        command = [
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'libopus', '-b:a', '64k', voice_message_path
        ]
        subprocess.run(command, check=True)
        logger.info(f'Голосовое сообщение создано: {voice_message_path}')

        await context.bot.send_voice(
            chat_id=query.message.chat_id,
            voice=open(voice_message_path, 'rb')
        )
        await query.edit_message_text(text="Ваше видео было успешно конвертировано в голосовое сообщение.")

        user_id = query.from_user.id
        user_stats[user_id]['video_to_voice'] += 1
        user_stats[user_id]['points'] += 1

    except Exception as e:
        logger.error(f'Ошибка при создании голосового сообщения: {e}', exc_info=True)
        await query.edit_message_text(text=f'Произошла ошибка: {e}')

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.debug(f'Получено голосовое сообщение от пользователя {update.message.from_user.id}')
        await update.message.reply_text("Начинается процесс расшифровки голосового сообщения...")

        voice_file = update.message.voice.file_id
        file = await context.bot.get_file(voice_file)

        ogg_path = os.path.join('audio_storage', f"{voice_file}.ogg")
        os.makedirs(os.path.dirname(ogg_path), exist_ok=True)

        await file.download_to_drive(ogg_path)
        logger.info(f'Голосовое сообщение загружено: {ogg_path}')

        wav_path = tempfile.mktemp(suffix=".wav")
        command = ['ffmpeg', '-i', ogg_path, wav_path]
        subprocess.run(command, check=True)
        logger.debug(f'Голосовое сообщение сконвертировано в WAV: {wav_path}')

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.debug(f'Распознанный текст: {text}')

        punctuated_text = add_punctuation(text)

        await update.message.reply_text(f'*Расшифровка голосового сообщения:*\n\n_{punctuated_text}_', parse_mode='Markdown')

        os.remove(wav_path)
        logger.debug(f'Временный WAV файл удалён: {wav_path}')

        user_id = update.message.from_user.id
        if user_id not in user_stats:
            user_stats[user_id] = {
                'video_to_note': 0,
                'video_to_voice': 0,
                'video_note_to_text': 0,
                'voice_to_text': 0,
                'points': 0
            }
        user_stats[user_id]['voice_to_text'] += 1
        user_stats[user_id]['points'] += 1

    except Exception as e:
        logger.error(f'Ошибка обработки голосового сообщения: {e}', exc_info=True)
        await update.message.reply_text(f'Произошла ошибка: {e}')

def calculate_progress(current_time, total_duration):
    current_parts = list(map(float, current_time.split(":")))
    total_parts = list(map(float, total_duration.split(":")))
    current_seconds = current_parts[0] * 3600 + current_parts[1] * 60 + current_parts[2]
    total_seconds = total_parts[0] * 3600 + total_parts[1] * 60 + total_parts[2]
    return int((current_seconds / total_seconds) * 100)

async def get_video_duration(video_path):
    command = ['ffmpeg', '-i', video_path]
    result = subprocess.run(command, stderr=subprocess.PIPE, text=True)
    duration_line = [x for x in result.stderr.split('\n') if 'Duration' in x]
    duration_str = duration_line[0].split(',')[0].split('Duration: ')[1]
    return duration_str.strip()

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    application.run_polling()

if __name__ == '__main__':
    main()
        
