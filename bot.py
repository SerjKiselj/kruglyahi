import logging
import random
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import asyncio

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name') - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'

# Хранилище игр
games = {}
players = {}

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
        [InlineKeyboardButton("Создать игру", callback_data='new_game')],
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
        f"Текущая сложность: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}\n"
        "Нажмите кнопку ниже, чтобы начать игру в крестики-нолики.",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == 'start_game':
        size = context.user_data.get('size', 3)
        win_length = context.user_data.get('win_length', 3)
        context.user_data['board'] = start_game(size=size, win_length=win_length)
        context.user_data['player_turn'] = True
        context.user_data['current_player'] = PLAYER_X

        await query.message.edit_text(
            f"Игра началась! Вы играете за 'X'.\nРазмер поля: {size}x{size}\nСложность: {'Обычный' if context.user_data['difficulty'] == 'ordinary' else 'Невозможный'}",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
        return

    if data == 'new_game':
        user_id = update.effective_user.id
        if user_id not in games:
            game_id = uuid4().hex
            games[game_id] = {'player1': user_id, 'player2': None, 'board': start_game(size=3, win_length=3), 'turn': user_id}
            await query.message.edit_text(
                text="Игра создана! Поделитесь этим ID с другим игроком, чтобы он присоединился.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Скопировать ID", callback_data=f'copy_id_{game_id}')]])
            )
        else:
            await query.message.reply_text("Вы уже создали игру.")

    if data.startswith('copy_id_'):
        game_id = data.split('_')[2]
        await query.message.reply_text(f"Ваш ID игры: {game_id}")

    if data == 'join_game':
        user_id = update.effective_user.id
        if user_id not in players:
            await query.message.reply_text("Введите ID игры, к которой хотите присоединиться.")
            context.user_data['waiting_for_game_id'] = True
        else:
            await query.message.reply_text("Вы уже участвуете в игре.")

    if data.startswith('size_'):
        size = int(data.split('_')[1])
        context.user_data['size'] = size
        await query.message.edit_text("Выберите сложность:", reply_markup=difficulty_keyboard())

    if data.startswith('difficulty_'):
        difficulty = data.split('_')[1]
        context.user_data['difficulty'] = difficulty
        await query.message.edit_text("Выберите размер поля:", reply_markup=size_keyboard())

    if data == 'cancel':
        await query.message.edit_text("Действие отменено.")

    if data.isdigit():
        move = int(data)
        if context.user_data.get('player_turn') and context.user_data.get('current_player') == PLAYER_X:
            board = context.user_data.get('board')
            size = context.user_data.get('size', 3)
            win_length = context.user_data.get('win_length', 3)

            if board[move] == EMPTY:
                board[move] = PLAYER_X
                if check_win(board, PLAYER_X, size, win_length):
                    await query.message.edit_text(f"Поздравляем! Вы выиграли!\n{format_board(board, size)}")
                    return
                if check_draw(board):
                    await query.message.edit_text(f"Ничья!\n{format_board(board, size)}")
                    return
                make_ai_move(board, context.user_data.get('difficulty', 'ordinary'), size, win_length)
                if check_win(board, PLAYER_O, size, win_length):
                    await query.message.edit_text(f"AI выиграл!\n{format_board(board, size)}")
                    return
                if check_draw(board):
                    await query.message.edit_text(f"Ничья!\n{format_board(board, size)}")
                    return
                context.user_data['player_turn'] = not context.user_data['player_turn']
                await query.message.edit_text(f"Ваш ход!\n{format_board(board, size)}", reply_markup=format_keyboard(board, size))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_game_id'):
        game_id = update.message.text
        if game_id in games:
            user_id = update.effective_user.id
            game = games[game_id]
            if game['player2'] is None:
                game['player2'] = user_id
                players[user_id] = game_id
                await update.message.reply_text("Вы присоединились к игре!")
                await update.message.reply_text(f"Ваш ход будет, когда игрок {game['player1']} сделает первый ход.")
            else:
                await update.message.reply_text("Игра уже заполнена.")
        else:
            await update.message.reply_text("Неверный ID игры.")
        context.user_data['waiting_for_game_id'] = False

async def main():
    application = Application.builder().token('7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
    
