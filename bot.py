import logging
import random
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
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
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')],
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
    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)
    win_length = context.user_data.get('win_length', 3)
    game_id = context.user_data.get('game_id')

    if query.data == 'start_game':
        context.user_data['board'] = start_game(size, win_length)
        context.user_data['player_turn'] = True
        await query.message.edit_text(
            f"Игра началась! Вы играете за 'X'.\nРазмер поля: {size}x{size}\nСложность: {'Обычный' if context.user_data['difficulty'] == 'ordinary' else 'Невозможный'}",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
        return

    if query.data == 'choose_difficulty':
        await query.message.edit_text("Выберите уровень сложности:", reply_markup=difficulty_keyboard())
        return

    if query.data == 'choose_size':
        await query.message.edit_text("Выберите размер поля:", reply_markup=size_keyboard())
        return

    if query.data.startswith('difficulty_'):
        context.user_data['difficulty'] = 'ordinary' if query.data == 'difficulty_ordinary' else 'impossible'
        await query.message.reply_text(f"Сложность установлена на {'Обычный' if context.user_data['difficulty'] == 'ordinary' else 'Невозможный'}")
        return

    if query.data.startswith('size_'):
        context.user_data['size'] = int(query.data.split('_')[1])
        context.user_data['win_length'] = context.user_data['size']
        await query.message.reply_text(f"Размер поля установлен на {context.user_data['size']}x{context.user_data['size']}")
        return

    if query.data == 'new_game':
        user_id = update.effective_user.id
        game_id = str(uuid4())
        games[game_id] = {
            'board': start_game(size=context.user_data.get('size', 3), win_length=context.user_data.get('win_length', 3)),
            'players': [user_id],
            'current_turn': user_id,
            'status': 'waiting'
        }
        await query.message.reply_text(
            f"Игра создана! Ваш ID игры: {game_id}\nПригласите другого игрока, используя команду /invite {game_id} <username>."
        )
        return

    if query.data == 'join_game':
        await query.message.reply_text("Введите ID игры для присоединения:", reply_markup=None)
        return

    if query.data == 'cancel':
        await query.message.reply_text("Отменено")
        return

    if query.data.isdigit() and board is not None:
        move = int(query.data)
        if board[move] == EMPTY:
            board[move] = PLAYER_X if context.user_data['player_turn'] else PLAYER_O
            if check_win(board, PLAYER_X if context.user_data['player_turn'] else PLAYER_O, size, win_length):
                await query.message.edit_text("Поздравляю, вы выиграли!")
                del context.user_data['board']
                return
            if check_draw(board):
                await query.message.edit_text("Ничья!")
                del context.user_data['board']
                return
            context.user_data['player_turn'] = not context.user_data['player_turn']
            if not context.user_data['player_turn']:
                make_ai_move(board, context.user_data['difficulty'], size, win_length)
                if check_win(board, PLAYER_O, size, win_length):
                    await query.message.edit_text("AI выиграл!")
                    del context.user_data['board']
                    return
                if check_draw(board):
                    await query.message.edit_text("Ничья!")
                    del context.user_data['board']
                    return
                context.user_data['player_turn'] = True
            await query.message.edit_text(
                "Сделайте ваш ход:\n\n",
                reply_markup=format_keyboard(board, size)
            )
        else:
            await query.message.answer("Эта клетка уже занята!")

async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    game_id = str(uuid4())
    size = context.user_data.get('size', 3)
    win_length = context.user_data.get('win_length', 3)
    
    games[game_id] = {
        'board': start_game(size=size, win_length=win_length),
        'players': [user_id],
        'current_turn': user_id,
        'status': 'waiting'
    }
    
    await update.message.reply_text(
        f"Игра создана! Ваш ID игры: {game_id}\nПригласите другого игрока, используя команду /invite {game_id} <username>."
    )

async def invite_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Используйте команду в формате: /invite <game_id> <username>")
        return

    game_id, username = context.args
    user_id = update.message.from_user.id

    if game_id not in games:
        await update.message.reply_text("Игра не найдена.")
        return

    game = games[game_id]

    if user_id != game['players'][0]:
        await update.message.reply_text("Вы не можете приглашать игроков, так как не являетесь создателем игры.")
        return

    try:
        invited_user = await context.bot.get_chat(username)
        await context.bot.send_message(
            chat_id=invited_user.id,
            text=f"Вас пригласили в игру крестики-нолики. Используйте команду /accept {game_id}, чтобы присоединиться.",
            parse_mode=ParseMode.MARKDOWN
        )
        game['status'] = 'pending'
        await update.message.reply_text("Приглашение отправлено.")
    except Exception as e:
        await update.message.reply_text("Не удалось найти пользователя.")
        logger.error(f"Ошибка при отправке приглашения: {e}")

async def accept_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Используйте команду в формате: /accept <game_id>")
        return

    game_id = context.args[0]
    user_id = update.message.from_user.id

    if game_id not in games:
        await update.message.reply_text("Игра не найдена.")
        return

    game = games[game_id]

    if game['status'] == 'waiting':
        await update.message.reply_text("Ожидайте приглашение от создателя игры.")
        return

    if len(game['players']) >= 2:
        await update.message.reply_text("Игра уже заполнена.")
        return

    game['players'].append(user_id)
    game['status'] = 'started'
    await update.message.reply_text("Вы присоединились к игре!")

    # Обновляем состояние игры
    await update_message(update, context)

async def make_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_id = context.user_data.get('game_id')
    user_id = update.effective_user.id

    if game_id not in games:
        await query.answer("Игра не найдена.")
        return

    game = games[game_id]

    if user_id != game['current_turn']:
        await query.answer("Не ваш ход!")
        return

    move = int(query.data)
    if game['board'][move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return

    game['board'][move] = PLAYER_X if user_id == game['players'][0] else PLAYER_O

    if check_win(game['board'], PLAYER_X if user_id == game['players'][0] else PLAYER_O, size=3, win_length=3):
        await query.message.reply_text("Поздравляю, вы выиграли!")
        del games[game_id]
        return

    if check_draw(game['board']):
        await query.message.reply_text("Ничья!")
        del games[game_id]
        return

    # Переключение хода
    game['current_turn'] = game['players'][1] if user_id == game['players'][0] else game['players'][0]
    await update_message(update, context)

async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_id = context.user_data.get('game_id')
    if game_id in games:
        game = games[game_id]
        board = game['board']
        size = context.user_data.get('size', 3)
        await query.message.edit_text(
            "Игра в крестики-нолики\n\n",
            reply_markup=format_keyboard(board, size)
        )

def main():
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("invite", invite_player))
    app.add_handler(CommandHandler("accept", accept_invite))
    app.add_handler(CommandHandler("create_game", create_game))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CallbackQueryHandler(make_move))

    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    app.run_polling()

if __name__ == '__main__':
    main()
        
