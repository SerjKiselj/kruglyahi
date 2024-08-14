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

# Игры в памяти
games = {}

def start_game(size=3, win_length=3):
    return [EMPTY] * (size * size)

def generate_game_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))

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

def minimax(board, player, size, win_length, depth=0, max_depth=5, alpha=float('-inf'), beta=float('inf')):
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
        [InlineKeyboardButton("Создать игру", callback_data='create_game')],
        [InlineKeyboardButton("Присоединиться к игре", callback_data='join_game')]
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
    size = context.user_data.get('size', 3)
    difficulty = context.user_data.get('difficulty', 'ordinary')
    await update.message.reply_text(
        f"Текущий размер поля: {size}x{size}\n"
        f"Текущая сложность: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}",
        reply_markup=main_menu_keyboard()
    )

async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = generate_game_code()
    games[game_code] = {
        'board': start_game(context.user_data.get('size', 3), context.user_data.get('win_length', 3)),
        'creator_id': update.message.from_user.id,
        'opponent_id': None,
        'player_turn': True
    }
    context.user_data['game_code'] = game_code
    await update.message.reply_text(
        f"Игра создана! Ваш код игры: {game_code}. Пригласите друга, отправив ему этот код с помощью команды /invite <username>."
    )

async def invite_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Используйте команду в формате: /invite <username>")
        return

    invited_username = context.args[0]
    try:
        invited_user = await context.bot.get_chat_member(chat_id='@' + invited_username, user_id=invited_username)
    except Exception:
        await update.message.reply_text("Не удалось найти пользователя.")
        return

    game_code = context.user_data.get('game_code')
    if not game_code:
        await update.message.reply_text("Сначала создайте игру командой /create_game.")
        return

    # Отправка сообщения приглашенному игроку
    await context.bot.send_message(
        invited_user.user.id,
        f"Вас пригласили в игру крестики-нолики. Используйте команду /join {game_code}, чтобы присоединиться."
    )
    await update.message.reply_text(f"Приглашение отправлено пользователю {invited_username}.")

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Используйте команду в формате: /join <код_игры>")
        return

    game_code = context.args[0]
    game = games.get(game_code)

    if not game or game['opponent_id']:
        await update.message.reply_text("Не удалось найти игру с таким кодом или игра уже заполнена.")
        return

    game['opponent_id'] = update.message.from_user.id
    game['player_turn'] = False

    context.user_data['game_code'] = game_code
    await update.message.reply_text(
        f"Вы присоединились к игре с кодом {game_code}. Игра начнется, когда создатель начнет игру."
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_code = context.user_data.get('game_code')
    game = games.get(game_code)

    if not game:
        await query.message.reply_text("Игра не найдена.")
        return

    if query.data == 'create_game':
        await create_game(update, context)
        return

    if query.data == 'choose_difficulty':
        await query.message.edit_text("Выберите сложность:", reply_markup=difficulty_keyboard())
        return

    if query.data == 'choose_size':
        await query.message.edit_text("Выберите размер поля:", reply_markup=size_keyboard())
        return

    if query.data.startswith('size_'):
        size_map = {'size_3': 3, 'size_4': 4, 'size_5': 5}
        size = size_map.get(query.data, 3)
        context.user_data['size'] = size
        context.user_data['win_length'] = min(size, 3)
        await query.message.edit_text(f"Размер поля изменен на {size}x{size}.", reply_markup=main_menu_keyboard())
        return

    if query.data.startswith('difficulty_'):
        context.user_data['difficulty'] = 'ordinary' if query.data == 'difficulty_ordinary' else 'impossible'
        await query.message.edit_text(f"Сложность установлена на {context.user_data['difficulty']}.", reply_markup=main_menu_keyboard())
        return

    if query.data.startswith('start_game'):
        if not game['creator_id'] == update.message.from_user.id:
            await query.message.answer("Только создатель игры может начать её.")
            return
        game['board'] = start_game(context.user_data.get('size', 3), context.user_data.get('win_length', 3))
        game['player_turn'] = True
        await query.message.edit_text("Игра началась! Вы играете за 'X'.", reply_markup=format_keyboard(game['board'], context.user_data.get('size', 3)))
        return

    if query.data.startswith('join_game'):
        await query.message.reply_text("Присоединиться к игре можно только через команду /join <код_игры>")
        return

    if not game['board']:
        await query.message.reply_text("Начните новую игру командой /start")
        return

    if game['player_turn'] != (update.message.from_user.id == game['creator_id']):
        await query.answer("Сейчас ход другого игрока!")
        return

    player_move = int(query.data)

    if game['board'][player_move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    game['board'][player_move] = PLAYER_X if update.message.from_user.id == game['creator_id'] else PLAYER_O
    game['player_turn'] = not game['player_turn']

    if check_win(game['board'], PLAYER_X, context.user_data.get('size', 3), context.user_data.get('win_length', 3)) or \
       check_win(game['board'], PLAYER_O, context.user_data.get('size', 3), context.user_data.get('win_length', 3)):
        await update_message(update, context, game)
        await query.message.reply_text(f"{'Вы выиграли!' if update.message.from_user.id == game['creator_id'] else 'Вы проиграли!'}")
        games.pop(game_code)
        return

    if check_draw(game['board']):
        await update_message(update, context, game)
        await query.message.reply_text("Ничья!")
        games.pop(game_code)
        return

    if game['opponent_id']:
        ai_move = make_ai_move(game['board'], context.user_data['difficulty'], context.user_data.get('size', 3), context.user_data.get('win_length', 3))
        if check_win(game['board'], PLAYER_O, context.user_data.get('size', 3), context.user_data.get('win_length', 3)):
            await update_message(update, context, game)
            await query.message.reply_text("Вы проиграли!")
            games.pop(game_code)
            return

        if check_draw(game['board']):
            await update_message(update, context, game)
            await query.message.reply_text("Ничья!")
            games.pop(game_code)
            return

    game['player_turn'] = not game['player_turn']
    await update_message(update, context, game)

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE, game):
    board = game['board']
    size = context.user_data.get('size', 3)
    await update.callback_query.message.edit_text(
        text="Текущая доска:\n\n" + format_board(board, size),
        reply_markup=format_keyboard(board, size)
    )

def format_board(board, size):
    return "\n".join(" | ".join(board[i*size + j] or ' ' for j in range(size)) for i in range(size))

def main():
    application = Application.builder().token("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("invite", invite_player))
    application.add_handler(CommandHandler("join", join_game))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
    
