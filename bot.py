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
        [InlineKeyboardButton(board[i * size + j] or ' ', callback_data=str(i * size + j)) for j in range(size)]
        for i in range(size)
    ]
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать игру", callback_data='start_game')],
        [InlineKeyboardButton("Выбрать сложность", callback_data='choose_difficulty')],
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')],
        [InlineKeyboardButton("Пригласить друга", callback_data='invite_friend')]
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
    await update.message.reply_text(
        "Добро пожаловать в Крестики-нолики!\nВыберите действие ниже:",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == 'start_game':
        if 'game_id' in context.user_data:
            await query.message.reply_text("Вы уже находитесь в игре.")
            return
        
        size = context.user_data.get('size', 3)
        difficulty = context.user_data.get('difficulty', 'ordinary')
        game_id = f"{update.effective_chat.id}_{user_id}"
        
        context.user_data[game_id] = {
            'players': [user_id],
            'board': start_game(size=size, win_length=context.user_data.get('win_length', 3)),
            'current_turn': user_id,
            'status': 'waiting'
        }
        context.user_data['game_id'] = game_id

        await query.message.edit_text(
            f"Игра началась! Вы играете за 'X'.\nРазмер поля: {size}x{size}\nСложность: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}",
            reply_markup=format_keyboard(context.user_data[game_id]['board'], size)
        )
        return

    if data == 'choose_difficulty':
        await query.message.edit_text("Выберите сложность:", reply_markup=difficulty_keyboard())
        return

    if data == 'choose_size':
        await query.message.edit_text("Выберите размер поля:", reply_markup=size_keyboard())
        return

    if data == 'invite_friend':
        if 'game_id' not in context.user_data:
            await query.message.reply_text("Сначала начните игру.")
            return

        game_id = context.user_data['game_id']
        invite_text = f"Игрок {update.effective_user.full_name} пригласил вас играть в Крестики-Нолики. Присоединитесь к игре по ссылке: /join_{game_id}"
        await query.message.reply_text(invite_text)
        return

    if data.startswith('size_'):
        size = int(data.split('_')[1])
        context.user_data['size'] = size
        await query.message.edit_text(
            f"Выбран размер поля: {size}x{size}",
            reply_markup=main_menu_keyboard()
        )
        return

    if data.startswith('difficulty_'):
        difficulty = data.split('_')[1]
        context.user_data['difficulty'] = difficulty
        await query.message.edit_text(
            f"Выбрана сложность: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}",
            reply_markup=main_menu_keyboard()
        )
        return

    if data == 'cancel':
        await query.message.edit_text("Выберите действие ниже:", reply_markup=main_menu_keyboard())
        return

    if data.startswith('join_'):
        game_id = data[len('join_'):]
        if game_id in context.user_data and len(context.user_data[game_id]['players']) == 1:
            context.user_data[game_id]['players'].append(user_id)
            context.user_data[game_id]['status'] = 'playing'
            await query.message.reply_text("Вы присоединились к игре!")
            await query.message.reply_text("Игра началась!")
            return
        else:
            await query.message.reply_text("Невозможно присоединиться к игре. Попробуйте позже.")
            return

    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)
    win_length = context.user_data.get('win_length', 3)

    if board is None:
        await query.message.reply_text("Начните новую игру командой /start")
        return

    player_move = int(data)

    if board[player_move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    game_id = context.user_data.get('game_id')
    if game_id is None or context.user_data[game_id]['current_turn'] != user_id:
        await query.answer("Сейчас не ваш ход!")
        return

    board[player_move] = PLAYER_X
    context.user_data[game_id]['current_turn'] = [p for p in context.user_data[game_id]['players'] if p != user_id][0]

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
    
