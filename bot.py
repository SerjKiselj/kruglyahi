import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'

# Функции для работы с игрой

def start_game(size):
    return [EMPTY] * (size * size)

def check_win(board, player, size, win_length):
    # Проверяем строки
    for row in range(size):
        for col in range(size - win_length + 1):
            if all(board[row * size + col + i] == player for i in range(win_length)):
                return True

    # Проверяем столбцы
    for col in range(size):
        for row in range(size - win_length + 1):
            if all(board[(row + i) * size + col] == player for i in range(win_length)):
                return True

    # Проверяем диагонали
    for row in range(size - win_length + 1):
        for col in range(size - win_length + 1):
            # Диагональ слева направо
            if all(board[(row + i) * size + col + i] == player for i in range(win_length)):
                return True
            # Диагональ справа налево
            if all(board[(row + i) * size + col + win_length - 1 - i] == player for i in range(win_length)):
                return True

    return False

def check_draw(board):
    return all(cell != EMPTY for cell in board)

def make_ai_move(board, difficulty, size, win_length):
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if difficulty == 'easy':
        if random.random() < 0.7:
            move = random.choice(empty_positions)
        else:
            move = block_or_win(board, PLAYER_O, size, win_length) or random.choice(empty_positions)
    elif difficulty == 'medium':
        move = block_or_win(board, PLAYER_O, size, win_length) or random.choice(empty_positions)
    else:
        move = minimax(board, PLAYER_O, size, win_length)[1]
    
    board[move] = PLAYER_O
    return move

def block_or_win(board, player, size, win_length):
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    for move in [i for i, cell in enumerate(board) if cell == EMPTY]:
        board[move] = player
        if check_win(board, player, size, win_length):
            board[move] = EMPTY
            return move
        board[move] = EMPTY
    
    for move in [i for i, cell in enumerate(board) if cell == EMPTY]:
        board[move] = opponent
        if check_win(board, opponent, size, win_length):
            board[move] = EMPTY
            return move
        board[move] = EMPTY
    
    return None

def minimax(board, player, size, win_length, alpha=float('-inf'), beta=float('inf')):
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if check_win(board, PLAYER_X, size, win_length):
        return (-10, None)
    if check_win(board, PLAYER_O, size, win_length):
        return (10, None)
    if check_draw(board):
        return (0, None)

    best_move = None

    if player == PLAYER_O:
        best_score = float('-inf')
        for move in empty_positions:
            board[move] = PLAYER_O
            score = minimax(board, PLAYER_X, size, win_length, alpha, beta)[0]
            board[move] = EMPTY
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return (best_score, best_move)
    else:
        best_score = float('inf')
        for move in empty_positions:
            board[move] = PLAYER_X
            score = minimax(board, PLAYER_O, size, win_length, alpha, beta)[0]
            board[move] = EMPTY
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return (best_score, best_move)

def format_keyboard(board, size):
    keyboard = [
        [InlineKeyboardButton(board[i * size + j] or ' ', callback_data=str(i * size + j)) for j in range(size)]
        for i in range(size)
    ]
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать игру", callback_data='start_game')],
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')],
        [InlineKeyboardButton("Выбрать сложность", callback_data='choose_difficulty')]
    ])

def size_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("3x3", callback_data='size_3')],
        [InlineKeyboardButton("4x4", callback_data='size_4')],
        [InlineKeyboardButton("5x5", callback_data='size_5')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
    ])

def difficulty_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Легкий", callback_data='difficulty_easy')],
        [InlineKeyboardButton("Средний", callback_data='difficulty_medium')],
        [InlineKeyboardButton("Сложный", callback_data='difficulty_hard')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Нажмите кнопку ниже, чтобы начать игру в крестики-нолики.",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    board = context.user_data.get('board')

    if query.data == 'start_game':
        size = context.user_data.get('size', 3)
        context.user_data['board'] = start_game(size)
        context.user_data['player_turn'] = True
        context.user_data['difficulty'] = 'easy'
        context.user_data['win_length'] = size  # Победа при наборе ряда равного размеру поля

        await query.message.edit_text(
            f"Игра началась на поле {size}x{size}! Вы играете за 'X'.",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
        return

    if query.data == 'choose_size':
        await query.message.edit_text("Выберите размер поля:", reply_markup=size_keyboard())
        return

    if query.data.startswith('size_'):
        size = int(query.data.split('_')[1])
        context.user_data['size'] = size
        context.user_data['win_length'] = size  # Обновление длины выигрышного ряда в зависимости от размера поля
        await query.message.edit_text(f"Размер поля изменен на {size}x{size}.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'choose_difficulty':
        await query.message.edit_text("Выберите уровень сложности:", reply_markup=difficulty_keyboard())
        return

    if query.data == 'difficulty_easy':
        context.user_data['difficulty'] = 'easy'
        await query.message.edit_text("Уровень сложности изменен на Легкий.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'difficulty_medium':
        context.user_data['difficulty'] = 'medium'
        await query.message.edit_text("Уровень сложности изменен на Средний.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'difficulty_hard':
        context.user_data['difficulty'] = 'hard'
        await query.message.edit_text("Уровень сложности изменен на Сложный.", reply_markup=main_menu_keyboard())
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
        await query.answer("Сейчас ход ИИ!")
        return

    board[player_move] = PLAYER_X
    context.user_data['player_turn'] = False

    size = context.user_data['size']
    win_length = context.user_data['win_length']

    if check_win(board, PLAYER_X, size, win_length):
        await update_message(update, context)
        await query.message.reply_text("Поздравляю, вы выиграли!")
        context.user_data['board'] = None
        return

    if check_draw(board):
        await update_message(update, context)
        await query.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return

    ai_move = make_ai_move(board, context.user_data['difficulty'], size, win_length)

    if check_win(board, PLAYER_O, size, win_length):
        await update_message(update, context)
        await query.message.reply_text("Вы проиграли!")
        context.user_data['board'] = None
        return

    if check_draw(board):
        await update_message(update, context)
        await query.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return

    context.user_data['player_turn'] = True
    await update_message(update, context)

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)
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
        
