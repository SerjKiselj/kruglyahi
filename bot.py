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

# Глобальное хранилище игр
games = {}

def start_game(size=3, win_length=3):
    return [EMPTY] * (size * size)

def generate_win_combos(size, win_length):
    combos = []
    for i in range(size):
        combos.append([i * size + j for j in range(size)])
        combos.append([j * size + i for j in range(size)])
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
        return (-10 + depth, None)
    if check_win(board, PLAYER_O, size, win_length):
        return (10 - depth, None)
    if check_draw(board):
        return (0, None)
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
    score = 0
    if col <= size - win_length:
        if all(board[row * size + col + k] == player for k in range(win_length)):
            score += 1
    if row <= size - win_length:
        if all(board[(row + k) * size + col] == player for k in range(win_length)):
            score += 1
    if row <= size - win_length and col <= size - win_length:
        if all(board[(row + k) * size + col + k] == player for k in range(win_length)):
            score += 1
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
    user_id = update.message.from_user.id
    if user_id not in games:
        games[user_id] = {'size': 3, 'win_length': 3, 'difficulty': 'ordinary'}
        await update.message.reply_text(
            "Вы выбрали одиночную игру. Нажмите кнопку ниже, чтобы начать.",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text("Вы уже играете!")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    board = games.get(user_id, {}).get('board')
    size = games.get(user_id, {}).get('size', 3)
    win_length = games.get(user_id, {}).get('win_length', 3)
    current_player = games.get(user_id, {}).get('current_player', PLAYER_X)

    if query.data == 'start_game':
        if 'player1' not in games:
            games['player1'] = {'board': start_game(size, win_length), 'size': size, 'win_length': win_length, 'current_player': PLAYER_X}
            await query.message.edit_text("Игра началась! Ожидаем второго игрока.", reply_markup=main_menu_keyboard())
        else:
            if 'player2' not in games:
                games['player2'] = {'board': start_game(size, win_length), 'size': size, 'win_length': win_length, 'current_player': PLAYER_O}
            await query.message.edit_text("Игра началась! Вы играете за 'O'.", reply_markup=format_keyboard(games['player2']['board'], size))
        return

    if query.data == 'choose_difficulty':
        await query.message.edit_text("Выберите сложность:", reply_markup=difficulty_keyboard())
        return

    if query.data.startswith('difficulty_'):
        difficulty = query.data.split('_')[1]
        if user_id in games:
            games[user_id]['difficulty'] = difficulty
            await query.message.edit_text(f"Сложность игры установлена на {difficulty}.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'choose_size':
        await query.message.edit_text("Выберите размер поля:", reply_markup=size_keyboard())
        return

    if query.data.startswith('size_'):
        size = int(query.data.split('_')[1])
        if user_id in games:
            games[user_id]['size'] = size
            games[user_id]['win_length'] = min(size, games[user_id]['win_length'])
            await query.message.edit_text(f"Размер поля установлен на {size}x{size}.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'cancel':
        await query.message.edit_text("Операция отменена.", reply_markup=main_menu_keyboard())
        return

    if board is None:
        await query.message.reply_text("Игра еще не началась. Нажмите 'Начать игру' для начала.")
        return

    move = int(query.data)
    if board[move] != EMPTY:
        await query.message.reply_text("Эта клетка уже занята!")
        return

    if current_player != PLAYER_X:
        await query.message.reply_text("Сейчас ход другого игрока!")
        return

    board[move] = PLAYER_X
    if check_win(board, PLAYER_X, size, win_length):
        await query.message.edit_text("Вы выиграли!", reply_markup=None)
        return
    if check_draw(board):
        await query.message.edit_text("Ничья!", reply_markup=None)
        return

    ai_move = make_ai_move(board, games[user_id]['difficulty'], size, win_length)
    if check_win(board, PLAYER_O, size, win_length):
        await query.message.edit_text("AI выиграл!", reply_markup=None)
        return
    if check_draw(board):
        await query.message.edit_text("Ничья!", reply_markup=None)
        return

    await query.message.edit_text("Ход AI:", reply_markup=format_keyboard(board, size))
    games[user_id]['current_player'] = PLAYER_X

async def main():
    application = Application.builder().token("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
            
