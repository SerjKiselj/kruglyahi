import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, CallbackContext

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'

# Хранилище игр
games = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Привет! Используйте команду /create_game, чтобы создать новую игру.\n"
        "Используйте команду /join_game <код_игры>, чтобы присоединиться к существующей игре."
    )

def create_game(update: Update, context: CallbackContext) -> None:
    game_id = str(update.message.chat_id)
    games[game_id] = {
        'board': [EMPTY] * 9,
        'players': [update.message.chat_id],
        'turn': PLAYER_X,
        'status': 'waiting'
    }
    update.message.reply_text(f"Игра создана! Ваш код игры: {game_id}. Передайте этот код другому игроку, чтобы присоединиться.")
    
def join_game(update: Update, context: CallbackContext) -> None:
    game_id = context.args[0]
    if game_id not in games:
        update.message.reply_text("Игра с таким кодом не найдена.")
        return
    
    game = games[game_id]
    
    if len(game['players']) >= 2:
        update.message.reply_text("Игра уже заполнена.")
        return
    
    game['players'].append(update.message.chat_id)
    game['status'] = 'ongoing'
    update.message.reply_text("Вы присоединились к игре! Ваш ход.")
    
    # Отправляем поле
    update.message.reply_text(
        f"Игра началась! Ваш ход. Игровое поле:\n{format_board(game['board'])}",
        reply_markup=format_keyboard(game['board'], game_id)
    )

def format_board(board):
    return "\n".join(
        "".join(board[i:i+3]) for i in range(0, 9, 3)
    )

def format_keyboard(board, game_id):
    keyboard = [
        [InlineKeyboardButton(board[i] or ' ', callback_data=f"{game_id}_{i}") for i in range(j, j+3)]
        for j in range(0, 9, 3)
    ]
    return InlineKeyboardMarkup(keyboard)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    game_id, pos = query.data.split('_')
    pos = int(pos)

    if game_id not in games:
        query.answer("Игра не найдена.")
        return

    game = games[game_id]

    if game['status'] != 'ongoing':
        query.answer("Игра завершена.")
        return

    if query.from_user.id not in game['players']:
        query.answer("Вы не участник этой игры.")
        return

    if game['board'][pos] != EMPTY:
        query.answer("Эта клетка уже занята.")
        return

    player = game['turn']
    game['board'][pos] = player

    # Проверка на победу и ничью
    if check_win(game['board'], player):
        query.message.edit_text(f"{format_board(game['board'])}\nИгрок {player} победил!")
        game['status'] = 'finished'
        return

    if EMPTY not in game['board']:
        query.message.edit_text(f"{format_board(game['board'])}\nНичья!")
        game['status'] = 'finished'
        return

    # Смена хода
    game['turn'] = PLAYER_X if player == PLAYER_O else PLAYER_O
    query.message.edit_text(
        f"{format_board(game['board'])}\nХод игрока {game['turn']}.",
        reply_markup=format_keyboard(game['board'], game_id)
    )
    query.answer()

def check_win(board, player):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]               # Diagonals
    ]
    return any(all(board[i] == player for i in condition) for condition in win_conditions)

def main() -> None:
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create_game", create_game))
    application.add_handler(CommandHandler("join_game", join_game))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
