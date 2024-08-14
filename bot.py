import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import asyncio
import uuid

# Логи для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
EMPTY = ''
PLAYER_X = 'X'
PLAYER_O = 'O'

games = {}  # Словарь для хранения игр по уникальному коду
player_sessions = {}  # Словарь для хранения игровых сессий пользователей

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
        [InlineKeyboardButton("Играть с ИИ", callback_data='start_singleplayer')],
        [InlineKeyboardButton("Мультиплеер", callback_data='start_multiplayer')],
        [InlineKeyboardButton("Выбрать сложность", callback_data='choose_difficulty')],
        [InlineKeyboardButton("Выбрать размер поля", callback_data='choose_size')]
    ])

def multiplayer_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать игру", callback_data='create_multiplayer')],
        [InlineKeyboardButton("Присоединиться к игре", callback_data='join_multiplayer')],
        [InlineKeyboardButton("Отмена", callback_data='cancel')]
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
        "Нажмите кнопку ниже, чтобы выбрать режим игры.",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    board = context.user_data.get('board')
    size = context.user_data.get('size', 3)  # Размер поля по умолчанию 3x3
    win_length = context.user_data.get('win_length', 3)
    difficulty = context.user_data.get('difficulty', 'ordinary')

    if query.data == 'start_singleplayer':
        # Начало игры с ИИ
        context.user_data['board'] = start_game(size, win_length)
        context.user_data['turn'] = PLAYER_X
        await query.message.edit_text(
            "Ваш ход.",
            reply_markup=format_keyboard(context.user_data['board'], size)
        )
    
    elif query.data == 'start_multiplayer':
        # Переход в меню мультиплеера
        await query.message.edit_text(
            "Выберите действие:",
            reply_markup=multiplayer_menu_keyboard()
        )

    elif query.data == 'create_multiplayer':
        # Создание новой мультиплеерной игры
        code = str(uuid.uuid4())[:8]  # Генерация уникального кода
        games[code] = {
            'board': start_game(size, win_length),
            'size': size,
            'win_length': win_length,
            'players': [query.message.chat_id],
            'turn': PLAYER_X
        }
        player_sessions[query.message.chat_id] = code
        await query.message.edit_text(
            f"Игра создана! Ваш код: {code}. Передайте этот код своему другу, чтобы он присоединился."
        )

    elif query.data == 'join_multiplayer':
        await query.message.edit_text(
            "Введите команду /join_game <код> для присоединения к игре."
        )
    
    elif query.data == 'choose_difficulty':
        # Выбор сложности игры
        await query.message.edit_text(
            "Выберите сложность игры:",
            reply_markup=difficulty_keyboard()
        )
    
    elif query.data == 'choose_size':
        # Выбор размера поля
        await query.message.edit_text(
            "Выберите размер поля:",
            reply_markup=size_keyboard()
        )

    elif query.data.startswith('difficulty_'):
        # Установка выбранной сложности
        difficulty = query.data.split('_')[1]
        context.user_data['difficulty'] = difficulty
        await query.message.edit_text(
            f"Сложность установлена на: {'Обычный' if difficulty == 'ordinary' else 'Невозможный'}",
            reply_markup=main_menu_keyboard()
        )

    elif query.data.startswith('size_'):
        # Установка выбранного размера поля
        size = int(query.data.split('_')[1])
        context.user_data['size'] = size
        context.user_data['win_length'] = 3 if size == 3 else 4
        await query.message.edit_text(
            f"Размер поля установлен на: {size}x{size}",
            reply_markup=main_menu_keyboard()
        )
    
    elif board:
        # Логика для одиночной игры
        player_move = int(query.data)
        if board[player_move] != EMPTY:
            await query.answer("Эта клетка уже занята!")
            return

        board[player_move] = PLAYER_X
        if check_win(board, PLAYER_X, size, win_length):
            await query.message.edit_text(
                "Вы выиграли!",
                reply_markup=format_keyboard(board, size)
            )
            return

        if check_draw(board):
            await query.message.edit_text(
                "Ничья.",
                reply_markup=format_keyboard(board, size)
            )
            return

        ai_move = make_ai_move(board, difficulty, size, win_length)
        if check_win(board, PLAYER_O, size, win_length):
            await query.message.edit_text(
                "ИИ выиграл.",
                reply_markup=format_keyboard(board, size)
            )
            return

        if check_draw(board):
            await query.message.edit_text(
                "Ничья.",
                reply_markup=format_keyboard(board, size)
            )
            return

        await query.message.edit_text(
            "Ваш ход.",
            reply_markup=format_keyboard(board, size)
        )
    else:
        # Логика для мультиплеерной игры
        player_id = query.message.chat_id

        if player_id not in player_sessions:
            await query.answer("Вы не находитесь в активной игре.")
            return

        code = player_sessions[player_id]
        game = games[code]
        board = game['board']
        size = game['size']
        win_length = game['win_length']
        current_turn = game['turn']

        if current_turn == PLAYER_X and player_id != game['players'][0]:
            await query.answer("Сейчас ходит другой игрок.")
            return
        elif current_turn == PLAYER_O and player_id != game['players'][1]:
            await query.answer("Сейчас ходит другой игрок.")
            return

        player_move = int(query.data)
        if board[player_move] != EMPTY:
            await query.answer("Эта клетка уже занята!")
            return

        board[player_move] = current_turn
        game['turn'] = PLAYER_O if current_turn == PLAYER_X else PLAYER_X

        if check_win(board, current_turn, size, win_length):
            await query.message.edit_text(
                f"Игра завершена! {'Вы' if current_turn == PLAYER_X else 'Ваш друг'} выиграли.",
                reply_markup=format_keyboard(board, size)
            )
            del games[code]
            return

        if check_draw(board):
            await query.message.edit_text(
                "Игра завершена! Ничья.",
                reply_markup=format_keyboard(board, size)
            )
            del games[code]
            return

        await query.message.edit_text(
            "Игра продолжается...",
            reply_markup=format_keyboard(board, size)
        )

        next_player = game['players'][0] if game['turn'] == PLAYER_X else game['players'][1]
        await context.bot.send_message(
            chat_id=next_player,
            text="Ваш ход.",
            reply_markup=format_keyboard(board, size)
        )

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        code = context.args[0]
        if code in games:
            if len(games[code]['players']) < 2:
                games[code]['players'].append(update.message.chat_id)
                player_sessions[update.message.chat_id] = code

                await update.message.reply_text(
                    f"Вы присоединились к игре с кодом: {code}. Игра начинается!"
                )

                # Сообщение первому игроку
                await context.bot.send_message(
                    chat_id=games[code]['players'][0],
                    text="Ваш друг присоединился к игре! Вы начинаете."
                )

                await context.bot.send_message(
                    chat_id=games[code]['players'][0],
                    text="Ваш ход.",
                    reply_markup=format_keyboard(games[code]['board'], games[code]['size'])
                )
            else:
                await update.message.reply_text("Эта игра уже заполнена.")
        else:
            await update.message.reply_text("Неверный код игры.")
    else:
        await update.message.reply_text("Вы должны ввести код игры. Например, /join_game <код>.")

def main():
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join_game", join_game, pass_args=True))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    app.run_polling()

if __name__ == '__main__':
    main()
    
