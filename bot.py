import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'

# Глобальное хранилище для активных игр
active_games = {}

def start_game(size=3, win_length=3):
    return [EMPTY] * (size * size)

def generate_win_combos(size, win_length):
    combos = []

    # Горизонтальные и вертикальные
    for i in range(size):
        combos.append([i * size + j for j in range(size)])
        combos.append([j * size + i for j in range(size)])

    # Диагонали
    if win_length <= size:
        combos.append([i * size + i for i in range(size)])
        combos.append([i * size + (size - 1 - i) for i in range(size)])

    return combos

def check_win(board, player, size, win_length):
    combos = generate_win_combos(size, win_length)
    for combo in combos:
        if len(combo) >= win_length and all(board[pos] == player for pos in combo):
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

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать игру с ИИ", callback_data='start_game_ai')],
        [InlineKeyboardButton("Начать игру с другом", callback_data='start_game_friend')],
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')]
    ])

def size_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("3x3", callback_data='size_3')],
        [InlineKeyboardButton("4x4", callback_data='size_4')],
        [InlineKeyboardButton("5x5", callback_data='size_5')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    size = context.user_data.get('size', 3)  # Размер поля по умолчанию 3x3
    await update.message.reply_text(
        f"Текущий размер поля: {size}x{size}\n"
        "Нажмите кнопку ниже, чтобы начать игру в крестики-нолики.",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)  # Размер поля по умолчанию 3x3
    win_length = context.user_data.get('win_length', 3)  # Длина победной комбинации по умолчанию 3

    if query.data == 'start_game_ai':
        context.user_data['board'] = start_game(size, win_length)
        context.user_data['player_turn'] = True

        await query.message.edit_text(
            f"Игра началась! Вы играете за 'X'.\nРазмер поля: {size}x{size}",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
        return

    if query.data == 'start_game_friend':
        context.user_data['board'] = start_game(size, win_length)
        context.user_data['player_turn'] = True
        context.user_data['opponent_id'] = None  # Идентификатор противника будет назначен позже

        await query.message.edit_text(
            f"Игра началась! Вы играете за 'X'.\nРазмер поля: {size}x{size}",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
        return

    if query.data.startswith('size_'):
        size_map = {'size_3': 3, 'size_4': 4, 'size_5': 5}
        size = size_map.get(query.data, 3)
        context.user_data['size'] = size
        context.user_data['win_length'] = min(size, 3)  # Длина победной комбинации не может быть больше размера поля
        await query.message.edit_text(f"Размер поля изменен на {size}x{size}.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'cancel':
        await query.message.edit_text("Отменено.", reply_markup=main_menu_keyboard())
        return

    if not board:
        await query.message.reply_text("Начните новую игру командой /start")
        return

    player_move = int(query.data)

    if board[player_move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    if not context.user_data['player_turn']:
        await query.answer("Сейчас ход вашего противника!")
        return

    board[player_move] = PLAYER_X if context.user_data['player_turn'] else PLAYER_O
    context.user_data['player_turn'] = not context.user_data['player_turn']

    # Проверяем победу
    if check_win(board, PLAYER_X, size, win_length):
        await update_message(update, context)
        await query.message.reply_text("Поздравляю, X выиграли!")
        context.user_data['board'] = None
        return
    elif check_win(board, PLAYER_O, size, win_length):
        await update_message(update, context)
        await query.message.reply_text("Поздравляю, O выиграли!")
        context.user_data['board'] = None
        return
    elif check_draw(board):
        await update_message(update, context)
        await query.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return

    await update_message(update, context)

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)  # Размер поля по умолчанию 3x3
    if board:
        await update.callback_query.message.edit_text(
            "Игра в крестики-нолики\n\n",
            reply_markup=format_keyboard(board, size)
        )

def main():
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    app.run_polling()

if __name__ == '__main__':
    main()
    
