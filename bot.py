import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import random
import string

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'

# Хранилище для игр и кодов комнат
games = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def start_game(size=3):
    return [EMPTY] * (size * size)

def generate_win_combos(size):
    combos = []

    for i in range(size):
        combos.append([i * size + j for j in range(size)])
        combos.append([j * size + i for j in range(size)])

    combos.append([i * size + i for i in range(size)])
    combos.append([i * size + (size - 1 - i) for i in range(size)])

    return combos

def check_win(board, player, size):
    combos = generate_win_combos(size)
    for combo in combos:
        if all(board[pos] == player for pos in combo):
            return True
    return False

def check_draw(board):
    return all(cell != EMPTY for cell in board)

def format_keyboard(board, size):
    keyboard = [
        [InlineKeyboardButton(board[i*size + j] or ' ', callback_data=str(i*size + j)) for j in range(size)]
        for i in range(size)
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Играть с ИИ", callback_data="play_with_ai")],
        [InlineKeyboardButton("Играть с другом", callback_data="play_with_friend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выбери режим игры:", reply_markup=reply_markup)

async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mode = query.data

    if mode == "play_with_ai":
        await play_with_ai(update, context)
    elif mode == "play_with_friend":
        await select_friend_option(update, context)

async def play_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = start_game()
    context.user_data['board'] = board
    context.user_data['turn'] = PLAYER_X
    context.user_data['size'] = 3

    await update.callback_query.message.reply_text(
        "Ты играешь с ИИ. Начинаем!",
        reply_markup=format_keyboard(board, context.user_data['size'])
    )

async def select_friend_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Создать комнату", callback_data="create_room")],
        [InlineKeyboardButton("Присоединиться к комнате", callback_data="join_room")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text("Выбери опцию:", reply_markup=reply_markup)

async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_code = generate_room_code()
    context.user_data['room_code'] = room_code
    games[room_code] = {
        'board': start_game(),
        'players': [update.callback_query.from_user.id],
        'turn': PLAYER_X,
        'size': 3
    }
    await update.callback_query.message.reply_text(f"Комната создана! Код комнаты: {room_code}. Передай его другу, чтобы он присоединился.")

async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_code = context.args[0].upper()
    if room_code not in games:
        await update.message.reply_text("Комната с таким кодом не найдена.")
        return

    game = games[room_code]
    if len(game['players']) >= 2:
        await update.message.reply_text("В этой комнате уже играют два игрока.")
        return

    game['players'].append(update.message.from_user.id)
    context.user_data['room_code'] = room_code
    await update.message.reply_text("Ты присоединился к игре! Ожидай своего хода.")
    await send_board_update(room_code, context)

async def send_board_update(room_code, context):
    game = games[room_code]
    board = game['board']
    size = game['size']

    for player_id in game['players']:
        await context.bot.send_message(
            chat_id=player_id,
            text=f"Ход {'X' if game['turn'] == PLAYER_X else 'O'}:",
            reply_markup=format_keyboard(board, size)
        )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    room_code = context.user_data.get('room_code')
    if not room_code or room_code not in games:
        await query.answer("Комната не найдена.")
        return

    game = games[room_code]
    if user_id not in game['players']:
        await query.answer("Ты не участвуешь в этой игре.")
        return

    if game['turn'] == PLAYER_X and game['players'][0] != user_id:
        await query.answer("Сейчас ходит другой игрок.")
        return

    if game['turn'] == PLAYER_O and game['players'][1] != user_id:
        await query.answer("Сейчас ходит другой игрок.")
        return

    board = game['board']
    size = game['size']
    move = int(query.data)

    if board[move] != EMPTY:
        await query.answer("Это место уже занято.")
        return

    board[move] = game['turn']
    if check_win(board, game['turn'], size):
        await query.edit_message_text(f"Игрок {game['turn']} выиграл!", reply_markup=None)
        await end_game(room_code)
        return

    if check_draw(board):
        await query.edit_message_text("Ничья!", reply_markup=None)
        await end_game(room_code)
        return

    game['turn'] = PLAYER_O if game['turn'] == PLAYER_X else PLAYER_X
    await send_board_update(room_code, context)

async def end_game(room_code):
    if room_code in games:
        del games[room_code]

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используйте команду /start для начала игры.")

if __name__ == '__main__':
    application = Application.builder().token('7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s').build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(select_mode, pattern="^(play_with_ai|play_with_friend)$"))
    application.add_handler(CallbackQueryHandler(create_room, pattern="^create_room$"))
    application.add_handler(CallbackQueryHandler(join_room, pattern="^join_room$"))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler('help', help_command))

    application.run_polling()
        
