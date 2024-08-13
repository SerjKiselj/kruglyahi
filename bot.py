import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения состояния игры
games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Используйте /play, чтобы начать игру.')

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    game_id = user.id

    if game_id not in games:
        games[game_id] = {
            'player1': user.id,
            'player2': None,
            'board': [' '] * 9,
            'turn': user.id
        }
        await update.message.reply_text('Вы начали новую игру! Пригласите друга с помощью команды /invite <имя_пользователя>')
    else:
        await update.message.reply_text('Вы уже находитесь в игре.')

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if len(context.args) == 1:
        invitee_username = context.args[0]
        bot = context.bot
        try:
            invitee = await bot.get_chat(invitee_username)
            invitee_id = invitee.id
        except:
            await update.message.reply_text('Не удалось найти пользователя.')
            return

        game_id = user.id
        if game_id in games:
            if games[game_id]['player2'] is None:
                games[game_id]['player2'] = invitee_id
                await context.bot.send_message(invitee_id, f'{user.first_name} пригласил вас играть в крестики-нолики. Используйте команду /accept, чтобы принять приглашение.')
                await update.message.reply_text(f'Приглашение отправлено {invitee_username}.')
            else:
                await update.message.reply_text('В игре уже есть два игрока.')
        else:
            await update.message.reply_text('Вы не начали игру.')
    else:
        await update.message.reply_text('Используйте команду так: /invite <имя_пользователя>')

async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    for game_id, game in games.items():
        if game['player2'] == user.id:
            game['player2'] = user.id
            await context.bot.send_message(game['player1'], 'Ваш друг принял приглашение. Игра началась!')
            await context.bot.send_message(user.id, 'Вы присоединились к игре.')
            await show_board(update.effective_chat.id, game_id)
            return
    await update.message.reply_text('Вы не получили приглашение в игру.')

async def show_board(chat_id: int, game_id: int) -> None:
    game = games[game_id]
    board = game['board']
    buttons = [[InlineKeyboardButton(board[i * 3 + j], callback_data=f'{game_id}-{i * 3 + j}') for j in range(3)] for i in range(3)]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id, 'Ваш ход:\n\n' + format_board(board), reply_markup=reply_markup)

def format_board(board: list) -> str:
    return f"""
    {board[0]}|{board[1]}|{board[2]}
    -----
    {board[3]}|{board[4]}|{board[5]}
    -----
    {board[6]}|{board[7]}|{board[8]}
    """

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split('-')
    game_id = int(data[0])
    index = int(data[1])

    game = games.get(game_id)
    if game and game['turn'] == query.from_user.id:
        if game['board'][index] == ' ':
            game['board'][index] = 'X' if query.from_user.id == game['player1'] else 'O'
            game['turn'] = game['player2'] if query.from_user.id == game['player1'] else game['player1']
            await show_board(update.effective_chat.id, game_id)
        else:
            await query.answer('Это поле уже занято.')

async def main() -> None:
    # Убедитесь, что используете правильный токен
    application = Application.builder().token("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s").build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("accept", accept))

    # Обработчик нажатий кнопок
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Запуск бота
    await application.run_polling()

if __name__ == '__main__':
    # Запуск цикла событий
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
