import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import requests

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Получаем данные с биржи Bybit
def get_crypto_prices():
    url = 'https://api.bybit.com/v2/public/tickers'
    response = requests.get(url)
    data = response.json()
    return data['result']

# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Узнать курсы криптовалют", callback_data='price')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Привет! Я бот, который показывает курсы криптовалют с биржи Bybit. Выберите команду:', reply_markup=reply_markup)

# Обработка нажатий на кнопки
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    if query.data == 'price':
        prices = get_crypto_prices()
        response = ""
        for price in prices:
            symbol = price['symbol']
            last_price = price['last_price']
            response += f'{symbol}: {last_price}\n'
        query.edit_message_text(text=response)

def main():
    # Вставьте сюда свой токен
    token = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

    updater = Updater(token)

    dispatcher = updater.dispatcher

    # Регистрируем обработчики команд и нажатий кнопок
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))

    # Запускаем бота
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
