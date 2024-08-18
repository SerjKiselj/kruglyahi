import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import string

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальное хранилище игр
games = {}

# Константы
EMPTY = ''
PLAYERS = ['X', 'O']

def start_game(size=3):
    return [EMPTY] * (size * size)

def format_keyboard(board, size):
    keyboard = [
        [InlineKeyboardButton(board[i*size + j] or ' ', callback_data=str(i*size + j)) for j in range(size)]
        for i in range(size)
    ]
    return InlineKeyboardMarkup(keyboard)

def check_win(board, player, size):
    lines = []
    for i in range(size):
        lines.append(board[i*size:(i+1)*size])  # строки
        lines.append(board[i::size])  # столбцы
    lines.append([board[i*(size+1)] for i in range(size)])  # главная диагональ
    lines.append([board[(i+1)*(size-1)] for i in range(size)])  # побочная диагональ

    for line in lines:
        if all(cell == player for cell in line):
            return True
    return False

def check_draw(board):
    return all(cell != EMPTY for cell in board)

def generate_game_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    game_code = generate_game_code()
    games[game_code] = {
        'board': start_game(),
        'players': [user_id],
        'current_player': 'X',  # Начинает игрок 'X'
        'size': 3
    }
    await update.message.reply_text(f"Вы создали новую игру! Ваш уникальный код игры: `{game_code}`. Отправьте этот код другим игрокам.")

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Пожалуйста, укажите код игры для присоединения.")
        return

    game_code = args[0].upper()
    if game_code not in games:
        await update.message.reply_text("Игра с таким кодом не найдена.")
        return

    game = games[game_code]
    if len(game['players']) >= 2:
        await update.message.reply_text("В этой игре уже достаточно игроков.")
        return

    if user_id in game['players']:
        await update.message.reply_text("Вы уже участвуете в этой игре.")
        return

    # Присоединение игрока
    game['players'].append(user_id)
    game['current_player'] = 'X' if len(game['players']) == 1 else 'O'  # Определяем символ для нового игрока
    await update.message.reply_text(f"Вы присоединились к игре как '{game['current_player']}'!")

    if len(game['players']) == 2:
        for player in game['players']:
            await context.bot.send_message(player, "Игра начнётся, как только оба игрока готовы.")
    
    for player in game['players']:
        if player != user_id:
            await context.bot.send_message(player, f"Игрок присоединился: {update.message.from_user.first_name}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать в игру крестики-нолики! Используйте команды /create_game для создания игры и /join_game <код> для присоединения к игре.")

async def handle_game_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    query = update.callback_query
    data = query.data
    game_code = context.user_data.get('game_code')
    
    if not game_code or game_code not in games:
        await query.message.reply_text("Игра не найдена или не назначена.")
        return

    game = games[game_code]
    board = game['board']
    size = game['size']
    current_player = game['current_player']
    
    if user_id not in game['players']:
        await query.answer("Вы не участвуете в этой игре.")
        return

    if user_id == game['players'][0]:
        player = 'X'
    else:
        player = 'O'
    
    if player != current_player:
        await query.answer("Сейчас не ваш ход.")
        return

    move = int(data)
    if board[move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    board[move] = player
    if check_win(board, player, size):
        await query.message.edit_text(f"Игрок '{player}' выиграл!")
        game['board'] = start_game(size)
        game['players'] = []  # Очистка игроков после завершения игры
        return

    if check_draw(board):
        await query.message.edit_text("Ничья!")
        game['board'] = start_game(size)
        return

    # Переключение хода
    game['current_player'] = 'X' if current_player == 'O' else 'O'
    await query.message.edit_text("Ход сделан. Ожидайте следующего хода.", reply_markup=format_keyboard(board, size))
    for player in game['players']:
        await context.bot.send_message(player, "Сделан ход. Ожидайте своей очереди.")

def main():
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create_game", create_game))
    app.add_handler(CommandHandler("join_game", join_game))
    app.add_handler(CallbackQueryHandler(handle_game_move))

    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    app.run_polling()

if __name__ == '__main__':
    main()
