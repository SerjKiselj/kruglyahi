import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelень)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Получаем данные с биржи Bybit
def get_crypto_prices():
    url = 'https://api.bybit.com/v2/public/tickers'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверка на наличие ошибок
        data = response.json()
        return data['result']
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении данных с Bybit: {e}")
        return []

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Узнать курсы криптовалют", callback_data='price')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привет! Я бот, который показывает курсы криптовалют с биржи Bybit. Выберите команду:', reply_markup=reply_markup)

# Обработка нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'price':
        prices = get_crypto_prices()
        if prices:
            response = ""
            for price in prices:
                symbol = price['symbol']
                last_price = price['last_price']
                response += f'{symbol}: {last_price}\n'
            await query.edit_message_text(text=response)
        else:
            await query.edit_message_text(text="Не удалось получить данные с Bybit. Попробуйте позже.")

def main():
    # Вставьте сюда свой токен
    token = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

    application = Application.builder().token(token).build()

    # Регистрируем обработчики команд и нажатий кнопок
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
