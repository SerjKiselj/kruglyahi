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

def start_game_with_friend(size=3, win_length=3):
    return {
        'board': start_game(size, win_length),
        'turn': 'player1',  # Определяет чей ход (player1 или player2)
        'player1': None,
        'player2': None
    }

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
    size = context.user_data.get('size', 3)
    difficulty = context.user_data.get('difficulty', 'ordinary')

    if context.user_data.get('game'):
        await update.message.reply_text("Игра уже идет!")
        return

    context.user_data['game'] = start_game_with_friend(size, context.user_data.get('win_length', 3))

    if not context.user_data['game']['player1']:
        context.user_data['game']['player1'] = update.message.from_user.id
        await update.message.reply_text("Вы первый игрок. Пожалуйста, отправьте вашему другу команду /start, чтобы начать игру.")
    elif not context.user_data['game']['player2']:
        context.user_data['game']['player2'] = update.message.from_user.id
        await update.message.reply_text("Вы второй игрок. Игра начинается!")

    await update.message.reply_text(
        f"Текущий размер поля: {size}x{size}\n"
        f"Текущая сложность: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}\n"
        "Нажмите кнопку ниже, чтобы начать игру в крестики-нолики.",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game = context.user_data.get('game')
    size = context.user_data.get('size', 3)
    win_length = context.user_data.get('win_length', 3)

    if not game:
        await query.message.reply_text("Начните новую игру командой /start")
        return

    if query.data == 'start_game':
        if game['player1'] == update.callback_query.from_user.id:
            await query.message.edit_text(
                f"Игра началась! Ваш ход!\nРазмер поля: {size}x{size}\nСложность: {'Обычный' if context.user_data['difficulty'] == 'ordinary' else 'Невозможный'}",
                reply_markup=format_keyboard(game['board'], size)
            )
        return

    if query.data.startswith('size_'):
        size_map = {'size_3': 3, 'size_4': 4, 'size_5': 5}
        size = size_map.get(query.data, 3)
        context.user_data['size'] = size
        context.user_data['win_length'] = min(size, 3)
        await query.message.edit_text(f"Размер поля изменен на {size}x{size}.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'difficulty_ordinary':
        context.user_data['difficulty'] = 'ordinary'
        await query.message.edit_text("Уровень сложности изменен на Обычный.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'difficulty_impossible':
        context.user_data['difficulty'] = 'impossible'
        await query.message.edit_text("Уровень сложности изменен на Невозможный.", reply_markup=main_menu_keyboard())
        return

    if query.data == 'cancel':
        await query.message.edit_text("Отменено.", reply_markup=main_menu_keyboard())
        return

    if update.callback_query.from_user.id not in [game['player1'], game['player2']]:
        await query.answer("Вы не участвуете в этой игре!")
        return

    player_move = int(query.data)
    if game['board'][player_move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    if game['turn'] == 'player1' and update.callback_query.from_user.id == game['player1']:
        game['board'][player_move] = PLAYER_X
        game['turn'] = 'player2'
    elif game['turn'] == 'player2' and update.callback_query.from_user.id == game['player2']:
        game['board'][player_move] = PLAYER_O
        game['turn'] = 'player1'
    else:
        await query.answer("Сейчас не ваш ход!")
        return

    if check_win(game['board'], PLAYER_X, size, win_length):
        await query.message.reply_text("Игрок 1 выиграл!")
        context.user_data['game'] = None
        return

    if check_win(game['board'], PLAYER_O, size, win_length):
        await query.message.reply_text("Игрок 2 выиграл!")
        context.user_data['game'] = None
        return

    if check_draw(game['board']):
        await query.message.reply_text("Ничья!")
        context.user_data['game'] = None
        return

    await update_message(update, context)

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = context.user_data.get('game')
    size = context.user_data.get('size', 3)
    if game:
        await update.callback_query.message.edit_text(
            "Игра в крестики-нолики\n\n" + ("Ход игрока 1" if game['turn'] == 'player1' else "Ход игрока 2"),
            reply_markup=format_keyboard(game['board'], size)
        )

def main():
    application = Application.builder().token('7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
            
