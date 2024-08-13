from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import logging

# Включение логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Глобальные переменные для хранения состояния игры
games = {}

# Команды и функции бота
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Используйте /play, чтобы начать игру.')

def play(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    game_id = user.id

    if game_id not in games:
        games[game_id] = {
            'player1': user.id,
            'player2': None,
            'board': [' '] * 9,
            'turn': user.id
        }
        update.message.reply_text('Вы начали новую игру! Пригласите друга с помощью команды /invite <имя_пользователя>')
    else:
        update.message.reply_text('Вы уже находитесь в игре.')

def invite(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if len(context.args) == 1:
        invitee_username = context.args[0]
        bot = context.bot
        try:
            invitee = bot.get_chat_member(update.message.chat_id, invitee_username)
            invitee_id = invitee.user.id
        except:
            update.message.reply_text('Не удалось найти пользователя.')
            return

        game_id = user.id
        if game_id in games:
            if games[game_id]['player2'] is None:
                games[game_id]['player2'] = invitee_id
                context.bot.send_message(invitee_id, f'{user.first_name} пригласил вас играть в крестики-нолики. Используйте команду /accept, чтобы принять приглашение.')
                update.message.reply_text(f'Приглашение отправлено {invitee_username}.')
            else:
                update.message.reply_text('В игре уже есть два игрока.')
        else:
            update.message.reply_text('Вы не начали игру.')
    else:
        update.message.reply_text('Используйте команду так: /invite <имя_пользователя>')

def accept(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    for game_id, game in games.items():
        if game['player2'] == user.id:
            game['player2'] = user.id
            context.bot.send_message(game['player1'], 'Ваш друг принял приглашение. Игра началась!')
            context.bot.send_message(user.id, 'Вы присоединились к игре.')
            show_board(update.message.chat_id, game_id)
            return
    update.message.reply_text('Вы не получили приглашение в игру.')

def show_board(chat_id: int, game_id: int) -> None:
    game = games[game_id]
    board = game['board']
    buttons = [[InlineKeyboardButton(board[i * 3 + j], callback_data=f'{game_id}-{i * 3 + j}') for j in range(3)] for i in range(3)]
    reply_markup = InlineKeyboardMarkup(buttons)
    context.bot.send_message(chat_id, 'Ваш ход:\n\n' + format_board(board), reply_markup=reply_markup)

def format_board(board: list) -> str:
    return f"""
    {board[0]}|{board[1]}|{board[2]}
    -----
    {board[3]}|{board[4]}|{board[5]}
    -----
    {board[6]}|{board[7]}|{board[8]}
    """

def handle_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    game_id, position = map(int, query.data.split('-'))
    game = games.get(game_id)
    
    if not game:
        query.answer(text="Игра не найдена")
        return

    if query.from_user.id != game['turn']:
        query.answer(text="Не ваш ход")
        return

    if game['board'][position] != ' ':
        query.answer(text="Ячейка уже занята")
        return

    # Обновление игрового поля
    game['board'][position] = 'X' if query.from_user.id == game['player1'] else 'O'
    game['turn'] = game['player2'] if query.from_user.id == game['player1'] else game['player1']
    
    # Проверка на победу
    winner = check_winner(game['board'])
    if winner:
        context.bot.send_message(update.effective_chat.id, f'Игрок {winner} выиграл!')
        del games[game_id]
        return

    # Проверка на ничью
    if ' ' not in game['board']:
        context.bot.send_message(update.effective_chat.id, 'Ничья!')
        del games[game_id]
        return
    
    show_board(update.effective_chat.id, game_id)
    query.answer()

def check_winner(board: list) -> str:
    winning_combinations = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for (a, b, c) in winning_combinations:
        if board[a] == board[b] == board[c] and board[a] != ' ':
            return board[a]
    return None

def main() -> None:
    updater = Updater("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s", use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("play", play))
    dispatcher.add_handler(CommandHandler("invite", invite))
    dispatcher.add_handler(CommandHandler("accept", accept))
    dispatcher.add_handler(CallbackQueryHandler(handle_button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
