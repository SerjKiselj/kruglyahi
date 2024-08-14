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

def minimax(board, player, size, win_length, depth=0, max_depth=3, alpha=float('-inf'), beta=float('inf')):
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if check_win(board, PLAYER_X, size, win_length):
        return (-10 + depth, None)  # Чем быстрее проигрыш, тем хуже
    if check_win(board, PLAYER_O, size, win_length):
        return (10 - depth, None)   # Чем быстрее победа, тем лучше
    if check_draw(board):
        return (0, None)            # Ничья

    # Ограничение глубины рекурсии
    if depth == max_depth or not empty_positions:
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
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')],
        [InlineKeyboardButton("Играть с другом", callback_data='play_with_friend')]
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

def game_code_keyboard(code):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Играть", callback_data=f'join_{code}')],
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
    query.answer()

    board = context.user_data.get('board', [])
    size = context.user_data.get('size', 3)
    win_length = context.user_data.get('win_length', 3)
    
    if 'player1' not in context.user_data:
        context.user_data['player1'] = query.from_user.id

    if query.data == 'start_game':
        context.user_data['board'] = start_game(size, win_length)
        context.user_data['current_turn'] = PLAYER_X
        context.user_data['player1'] = query.from_user.id
        context.user_data['player2'] = None
        context.user_data['game_started'] = True
        context.user_data['game_code'] = random.randint(1000, 9999)
        await query.edit_message_text("Игра началась! Ваш ход.", reply_markup=format_keyboard(context.user_data['board'], size))

    elif query.data == 'choose_difficulty':
        await query.edit_message_text("Выберите сложность:", reply_markup=difficulty_keyboard())

    elif query.data == 'choose_size':
        await query.edit_message_text("Выберите размер поля:", reply_markup=size_keyboard())

    elif query.data.startswith('difficulty_'):
        context.user_data['difficulty'] = query.data.split('_')[1]
        await query.edit_message_text(f"Сложность установлена на: {'Обычный' if context.user_data['difficulty'] == 'ordinary' else 'Невозможный'}", reply_markup=main_menu_keyboard())

    elif query.data.startswith('size_'):
        context.user_data['size'] = int(query.data.split('_')[1])
        await query.edit_message_text(f"Размер поля установлен на: {context.user_data['size']}x{context.user_data['size']}", reply_markup=main_menu_keyboard())

    elif query.data == 'play_with_friend':
        code = random.randint(1000, 9999)
        context.user_data['game_code'] = code
        await query.edit_message_text("Отправьте код вашему другу. Он сможет присоединиться к игре, используя код ниже.", reply_markup=game_code_keyboard(code))

    elif query.data.startswith('join_'):
        code = query.data.split('_')[1]
        if code == str(context.user_data.get('game_code')):
            if context.user_data.get('player2') is None:
                context.user_data['player2'] = query.from_user.id
                await query.edit_message_text("Вы присоединились к игре. Ожидайте, пока первый игрок начнет.", reply_markup=main_menu_keyboard())
            else:
                await query.edit_message_text("Игра уже началась.")
        else:
            await query.edit_message_text("Неверный код.")

    elif query.data == 'cancel':
        await query.edit_message_text("Отмена действия.", reply_markup=main_menu_keyboard())

    elif query.data.isdigit():
        if context.user_data.get('game_started') and context.user_data['current_turn'] == query.from_user.id:
            move = int(query.data)
            if board[move] == EMPTY:
                board[move] = PLAYER_X
                if check_win(board, PLAYER_X, size, win_length):
                    await query.edit_message_text("Поздравляем! Вы выиграли!", reply_markup=format_keyboard(board, size))
                    context.user_data['game_started'] = False
                elif check_draw(board):
                    await query.edit_message_text("Ничья!", reply_markup=format_keyboard(board, size))
                    context.user_data['game_started'] = False
                else:
                    # Ход ИИ
                    make_ai_move(board, context.user_data['difficulty'], size, win_length)
                    if check_win(board, PLAYER_O, size, win_length):
                        await query.edit_message_text("Игра закончилась. ИИ выиграл!", reply_markup=format_keyboard(board, size))
                        context.user_data['game_started'] = False
                    elif check_draw(board):
                        await query.edit_message_text("Ничья!", reply_markup=format_keyboard(board, size))
                        context.user_data['game_started'] = False
                    else:
                        context.user_data['current_turn'] = context.user_data['player2'] if context.user_data['current_turn'] == context.user_data['player1'] else context.user_data['player1']
                        await query.edit_message_text("Ваш ход.", reply_markup=format_keyboard(board, size))
            else:
                await query.edit_message_text("Эта ячейка уже занята!", reply_markup=format_keyboard(board, size))
        else:
            await query.answer("Это не ваш ход!", show_alert=True)

async def main():
    application = Application.builder().token("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    # Проверяем, запущен ли цикл событий
    loop = asyncio.get_event_loop()
    if loop.is_running():
        await application.run_polling()
    else:
        await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
    
