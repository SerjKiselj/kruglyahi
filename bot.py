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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне видео, и я предложу, что с ним можно сделать.')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Получение файла видео
        video_file = update.message.video.file_id
        file = await context.bot.get_file(video_file)

        # Сохранение файла временно
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

        # Сохранение состояния пользователя
        user_state[update.message.from_user.id] = video_path

        # Предложение пользователю выбора
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
        # Определение размеров видео
        width, height = await get_video_dimensions(video_path)
        logger.info(f'Размеры исходного видео: {width}x{height}')

        # Определение параметров для обрезки до 1:1
        crop_size = min(width, height)
        x_offset = (width - crop_size) // 2
        y_offset = (height - crop_size) // 2

        # Использование временного файла для выходного видео
        output_path = tempfile.mktemp(suffix=".mp4")
        
        # Команда для выполнения конвертации с прогрессом
        command = [
            'ffmpeg', '-i', video_path,
            '-vf', f'crop={crop_size}:{crop_size}:{x_offset}:{y_offset},scale=240:240,setsar=1:1,format=yuv420p',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-b:v', '2M',
            '-c:a', 'aac', '-b:a', '128k', '-shortest',
            '-progress', '-', output_path
        ]

        # Запуск конвертации
        process = subprocess.Popen(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

        progress = 0
        for line in process.stderr:
            logger.info(f'ffmpeg output: {line.strip()}')

            # Поиск времени из вывода ffmpeg
            match_out_time = re.search(r'out_time_ms=(\d+)', line)
            match_duration = re.search(r'duration=(\d+)', line)
            if match_out_time and match_duration:
                out_time_ms = int(match_out_time.group(1))
                duration_ms = int(match_duration.group(1))
                new_progress = (out_time_ms / duration_ms) * 100
                if new_progress - progress >= 5:  # Обновляем только если прогресс изменился на 5%
                    progress = new_progress
                    await query.message.reply_text(f'Конвертация в процессе... Прогресс: {progress:.2f}%')

        # Завершение процесса и проверка результата
        process.wait()
        logger.info(f'Конвертация завершена: {output_path}')

        # Отправка сконвертированного видео
        with open(output_path, 'rb') as video:
            await query.message.reply_video_note(video)

        # Очистка временных файлов
        os.remove(video_path)
        os.remove(output_path)

        # Сообщение о завершении
        await query.message.reply_text('Конвертация завершена!')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}')
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def create_voice_message_and_send(query: Update, context: ContextTypes.DEFAULT_TYPE, video_path: str) -> None:
    try:
        # Использование временного файла для выходного аудио
        output_path = tempfile.mktemp(suffix=".ogg")

        # Команда для извлечения аудио
        command = [
            'ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_path
        ]

        # Запуск извлечения аудио
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        logger.info(f'ffmpeg output: {process.stdout}')

        # Отправка аудиосообщения
        with open(output_path, 'rb') as audio:
            await query.message.reply_voice(audio)

        # Очистка временных файлов
        os.remove(video_path)
        os.remove(output_path)

        # Сообщение о завершении
        await query.message.reply_text('Создание голосового сообщения завершено!')
    
    except Exception as e:
        logger.error(f'Ошибка обработки видео: {e}')
        await query.message.reply_text(f'Произошла ошибка: {e}')

async def get_video_dimensions(video_path: str) -> tuple:
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    output = subprocess.check_output(command).decode().strip().split('\n')
    width, height = int(output[0]), int(output[1])
    return width, height

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Получение файла голосового сообщения
        voice_file = update.message.voice.file_id
        file = await context.bot.get_file(voice_file)

        # Сохранение файла временно
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            voice_path = temp_file.name

        # Загрузка файла
        await file.download_to_drive(voice_path)
        logger.info(f'Голосовое сообщение загружено: {voice_path}')

        # Конвертация ogg в wav для обработки
        wav_path = tempfile.mktemp(suffix=".wav")
        audio = AudioSegment.from_file(voice_path)
        audio.export(wav_path, format="wav")

        # Распознавание речи
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")

        # Отправка расшифрованного текста пользователю
        await update.message.reply_text(f'Расшифровка голосового сообщения: {text}')

        # Очистка временных файлов
        os.remove(voice_path)
        os.remove(wav_path)

    except Exception as e:
        logger.error(f'Ошибка обработки голосового сообщения: {e}')
        await update.message.reply_text(f'Произошла ошибка: {e}')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
    
