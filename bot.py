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

def make_ai_move(board, difficulty, size, win_length):
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if difficulty == 'ordinary':
        if random.random() < 0.3:
            move = random.choice(empty_positions)
        else:
            move = block_or_win(board, PLAYER_O, size, win_length) or minimax(board, PLAYER_O, size, win_length)[1]
    elif difficulty == 'impossible':
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

def minimax(board, player, size, win_length, depth=0, max_depth=5 if size > 3 else 10, alpha=float('-inf'), beta=float('inf')):
    logger.info(f"Minimax call at depth {depth}, size {size}, max_depth {max_depth}")

    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if check_win(board, PLAYER_X, size, win_length):
        return (-10 + depth, None)  # Чем быстрее проигрыш, тем хуже
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
        [InlineKeyboardButton("Выбрать сложность", callback_data='choose_difficulty')],
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')]
    ])

def difficulty_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Обычный", callback_data='difficulty_ordinary')],
        [InlineKeyboardButton("Невозможный", callback_data='difficulty_impossible')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
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
    difficulty = context.user_data.get('difficulty', 'ordinary')
    await update.message.reply_text(
        f"Текущий размер поля: {size}x{size}\n"
        f"Текущая сложность: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}\n"
        "Нажмите кнопку ниже, чтобы начать игру в крестики-нолики.",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)  # Размер поля по умолчанию 3x3
    win_length = context.user_data.get('win_length', 3)  # Длина победной комбинации по умолчанию 3

    # Убедитесь, что есть ключи по умолчанию
    if 'difficulty' not in context.user_data:
        context.user_data['difficulty'] = 'ordinary'
    if 'size' not in context.user_data:
        context.user_data['size'] = 3
    if 'win_length' not in context.user_data:
        context.user_data['win_length'] = 3

    if query.data == 'start_game':
        context.user_data['board'] = start_game(size, win_length)
        board = context.user_data['board']
        await query.edit_message_text(
            "Вы начали новую игру!",
            reply_markup=format_keyboard(board, size)
        )
    elif query.data.startswith('difficulty_'):
        context.user_data['difficulty'] = query.data.split('_')[1]
        await query.answer(f"Сложность изменена на {'Обычный' if context.user_data['difficulty'] == 'ordinary' else 'Невозможный'}")
        await query.edit_message_text(
            "Выберите сложность:",
            reply_markup=difficulty_keyboard()
        )
    elif query.data.startswith('size_'):
        size = int(query.data.split('_')[1])
        context.user_data['size'] = size
        await query.answer(f"Размер поля изменен на {size}x{size}")
        await query.edit_message_text(
            "Выберите размер поля:",
            reply_markup=size_keyboard()
        )
    elif board and board[int(query.data)] == EMPTY:
        board[int(query.data)] = PLAYER_X
        if check_win(board, PLAYER_X, size, win_length):
            await query.edit_message_text("Вы выиграли!", reply_markup=format_keyboard(board, size))
            return
        elif check_draw(board):
            await query.edit_message_text("Ничья!", reply_markup=format_keyboard(board, size))
            return
        await query.edit_message_text("Ход бота...", reply_markup=format_keyboard(board, size))
        
        # Ход бота
        ai_move = await make_ai_move_async(board, context.user_data['difficulty'], size, win_length)
        board[ai_move] = PLAYER_O
        if check_win(board, PLAYER_O, size, win_length):
            await query.edit_message_text("Вы проиграли!", reply_markup=format_keyboard(board, size))
        elif check_draw(board):
            await query.edit_message_text("Ничья!", reply_markup=format_keyboard(board, size))
        else:
            await query.edit_message_text("Ваш ход:", reply_markup=format_keyboard(board, size))

    elif query.data == 'choose_difficulty':
        await query.edit_message_text("Выберите сложность:", reply_markup=difficulty_keyboard())
    elif query.data == 'choose_size':
        await query.edit_message_text("Выберите размер поля:", reply_markup=size_keyboard())
    elif query.data == 'cancel':
        await query.edit_message_text("Отмена. Возвращение в главное меню.", reply_markup=main_menu_keyboard())

async def make_ai_move_async(board, difficulty, size, win_length):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, make_ai_move, board, difficulty, size, win_length)

if __name__ == '__main__':
    application = Application.builder().token('7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()
        
