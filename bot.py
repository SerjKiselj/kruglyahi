import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import asyncio

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'
WIN_COMBOS = [
    [0, 1, 2],  # верхний ряд
    [3, 4, 5],  # средний ряд
    [6, 7, 8],  # нижний ряд
    [0, 3, 6],  # первый столбец
    [1, 4, 7],  # второй столбец
    [2, 5, 8],  # третий столбец
    [0, 4, 8],  # диагональ слева направо
    [2, 4, 6],  # диагональ справа налево
]

# Функции для работы с игрой

def start_game(size=3, win_length=3):
    return [EMPTY] * (size * size)

def check_win(board, player, size, win_length):
    for combo in WIN_COMBOS:
        if all(board[pos] == player for pos in combo):
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

def minimax(board, player, size, win_length, depth=0, max_depth=5, alpha=float('-inf'), beta=float('inf')):
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if check_win(board, PLAYER_X, size, win_length):
        return (-10 + depth, None)  # Чем быстрее победа, тем лучше
    if check_win(board, PLAYER_O, size, win_length):
        return (10 - depth, None)   # Чем быстрее победа, тем лучше
    if check_draw(board):
        return (0, None)            # Ничья

    # Ограничение глубины рекурсии
    if depth == max_depth:
        return (heuristic_evaluation(board, player, size, win_length), None)

    best_move = None

    if player == PLAYER_O:
        best_score = float('-inf')
        for move in empty_positions:
            board[move] = PLAYER_O
            score = minimax(board, PLAYER_X, size, win_length, depth + 1, max_depth, alpha, beta)[0]
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
            score = minimax(board, PLAYER_O, size, win_length, depth + 1, max_depth, alpha, beta)[0]
            board[move] = EMPTY
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return (best_score, best_move)

def heuristic_evaluation(board, player, size, win_length):
    """Простая эвристика, оценивающая текущее состояние доски.
       Возвращает положительное значение для благоприятной позиции для бота и отрицательное для игрока."""
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    bot_score = 0
    player_score = 0

    for i in range(size):
        for j in range(size):
            if board[i * size + j] == player:
                bot_score += score_position(board, i, j, player, size, win_length)
            elif board[i * size + j] == opponent:
                player_score += score_position(board, i, j, opponent, size, win_length)

    return bot_score - player_score

def score_position(board, row, col, player, size, win_length):
    """Оценивает позицию по строкам, столбцам и диагоналям."""
    score = 0

    # Проверка строки
    if col <= size - win_length:
        if all(board[row * size + col + k] == player for k in range(win_length)):
            score += 1

    # Проверка столбца
    if row <= size - win_length:
        if all(board[(row + k) * size + col] == player for k in range(win_length)):
            score += 1

    # Проверка диагонали слева направо
    if row <= size - win_length and col <= size - win_length:
        if all(board[(row + k) * size + col + k] == player for k in range(win_length)):
            score += 1

    # Проверка диагонали справа налево
    if row <= size - win_length and col >= win_length - 1:
        if all(board[(row + k) * size + col - k] == player for k in range(win_length)):
            score += 1

    return score

def format_keyboard(board, size):
    keyboard = [
        [InlineKeyboardButton(board[i*size + j] or ' ', callback_data=str(i*size + j)) for j in range(size)]
        for i in range(size)
    ]
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать игру", callback_data='start_game')],
        [InlineKeyboardButton("Выбрать сложность", callback_data='choose_difficulty')]
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
    size = context.user_data.get('size', 3)  # Размер поля по умолчанию 3x3
    win_length = context.user_data.get('win_length', 3)  # Длина победной комбинации по умолчанию 3

    if query.data == 'start_game':
        context.user_data['board'] = start_game(size, win_length)
        context.user_data['player_turn'] = True
        context.user_data['difficulty'] = 'easy'

        await query.message.edit_text(
            "Игра началась! Вы играете за 'X'.",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
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
    
