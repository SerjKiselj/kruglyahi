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

# Хранилище игр
games = {}

def start_game(size=3):
    return [EMPTY] * (size * size)

def format_keyboard(board, size):
    keyboard = [
        [InlineKeyboardButton(board[i*size + j] or ' ', callback_data=str(i*size + j)) for j in range(size)]
        for i in range(size)
    ]
    return InlineKeyboardMarkup(keyboard)

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

def handle_move(board, player, move, size, win_length):
    board[move] = player
    if check_win(board, player, size, win_length):
        return f"Игрок {player} выиграл!", True
    if check_draw(board):
        return "Ничья!", True
    return None, False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    if chat_id in games:
        await update.message.reply_text("Игра уже начата.")
        return
    games[chat_id] = {'board': start_game(), 'player1': user_id, 'player2': None, 'turn': user_id, 'size': 3, 'win_length': 3}
    await update.message.reply_text("Игра началась! Ожидаем второго игрока. Используйте команду /join для присоединения.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    if chat_id not in games:
        await update.message.reply_text("Нет активной игры в этом чате. Начните новую игру командой /start.")
        return
    game = games[chat_id]
    if game['player2'] is not None:
        await update.message.reply_text("Игра уже заполнена.")
        return
    game['player2'] = user_id
    game['turn'] = game['player1']
    await update.message.reply_text("Вы присоединились к игре. Ваш ход!")
    await update.message.reply_text(
        "Игра в крестики-нолики началась!",
        reply_markup=format_keyboard(game['board'], game['size'])
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if chat_id not in games:
        await query.message.reply_text("Нет активной игры в этом чате.")
        return

    game = games[chat_id]
    if user_id not in [game['player1'], game['player2']]:
        await query.message.reply_text("Вы не участвуете в этой игре.")
        return

    if game['turn'] != user_id:
        await query.answer("Не ваш ход!")
        return

    board = game['board']
    move = int(query.data)
    if board[move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    result_message, game_over = handle_move(board, PLAYER_X if user_id == game['player1'] else PLAYER_O, move, game['size'], game['win_length'])
    if game_over:
        await query.message.edit_text(result_message)
        del games[chat_id]
        return

    if game['player2']:
        ai_move = make_ai_move(board, 'impossible', game['size'], game['win_length'])
        result_message, game_over = handle_move(board, PLAYER_O, ai_move, game['size'], game['win_length'])
        if game_over:
            await query.message.edit_text(result_message)
            del games[chat_id]
            return

    game['turn'] = game['player2'] if user_id == game['player1'] else game['player1']
    await query.message.edit_text(
        "Ход игрока {}".format(game['player1'] if game['turn'] == game['player1'] else game['player2']),
        reply_markup=format_keyboard(board, game['size'])
    )

def main():
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"  # Замените на ваш токен
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == '__main__':
    main()
    
