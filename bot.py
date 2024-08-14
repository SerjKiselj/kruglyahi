import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

games = {}

def create_board():
    return [[' ' for _ in range(3)] for _ in range(3)]

def render_board(board):
    symbols = {'X': '❌', 'O': '⭕', ' ': '⬜'}
    return '\n'.join([''.join([symbols[cell] for cell in row]) for row in board])

def check_winner(board):
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != ' ':
            return board[i][0]
        if board[0][i] == board[1][i] == board[2][i] != ' ':
            return board[0][i]
    if board[0][0] == board[1][1] == board[2][2] != ' ':
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != ' ':
        return board[0][2]
    return None

def is_draw(board):
    return all(cell != ' ' for row in board for cell in row)

def make_move(board, row, col, player):
    if board[row][col] == ' ':
        board[row][col] = player
        return True
    return False

def create_board_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(3):
        for j in range(3):
            buttons.append(InlineKeyboardButton(f'{i+1},{j+1}', callback_data=f'move_{i}_{j}'))
    keyboard.add(*buttons)
    return keyboard

@dp.message_handler(commands=['start'])
async def start_game(message: types.Message):
    await message.answer("Привет! Это игра 'Крестики-нолики'. Чтобы начать новую игру, введите /newgame.")

@dp.message_handler(commands=['newgame'])
async def new_game(message: types.Message):
    games[message.from_user.id] = {
        'board': create_board(),
        'players': [message.from_user.id, None],
        'turn': 'X'
    }
    await message.answer("Игра создана! Пригласите другого игрока с помощью команды /invite @username.")

@dp.message_handler(commands=['invite'])
async def invite_player(message: types.Message):
    if message.from_user.id not in games:
        await message.answer("Сначала создайте игру с помощью команды /newgame.")
        return
    
    if len(message.text.split()) < 2:
        await message.answer("Пожалуйста, укажите имя пользователя через @, которого вы хотите пригласить.")
        return

    username = message.text.split()[1]
    user_id = await bot.get_chat(username)
    
    if games[message.from_user.id]['players'][1] is None:
        games[message.from_user.id]['players'][1] = user_id.id
        await bot.send_message(user_id.id, f"Вас пригласили в игру 'Крестики-нолики'. Чтобы присоединиться, введите /join.")
        await message.answer(f"Приглашение отправлено пользователю {username}.")
    else:
        await message.answer("Игрок уже присоединился.")

@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    for game in games.values():
        if game['players'][1] == message.from_user.id:
            board = game['board']
            await message.answer("Вы присоединились к игре!")
            await bot.send_message(game['players'][0], "Игрок присоединился, ваш ход.")
            await bot.send_message(game['players'][0], render_board(board), reply_markup=create_board_keyboard())
            await bot.send_message(game['players'][1], "Ожидайте, пока первый игрок сделает ход.")
            return
    await message.answer("Вас не пригласили в игру или игра уже завершена.")

@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def process_move(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    game = None

    for g in games.values():
        if user_id in g['players']:
            game = g
            break

    if not game:
        await callback_query.answer("Вы не участвуете в игре.")
        return

    board = game['board']
    turn = game['turn']
    row, col = map(int, callback_query.data.split('_')[1:])

    if user_id != game['players'][0] and user_id != game['players'][1]:
        await callback_query.answer("Вы не участвуете в игре.")
        return

    if (turn == 'X' and user_id != game['players'][0]) or (turn == 'O' and user_id != game['players'][1]):
        await callback_query.answer("Сейчас не ваш ход.")
        return

    if make_move(board, row, col, turn):
        winner = check_winner(board)
        if winner:
            await bot.send_message(game['players'][0], f"Игрок {turn} выиграл!")
            await bot.send_message(game['players'][1], f"Игрок {turn} выиграл!")
            del games[callback_query.from_user.id]
        elif is_draw(board):
            await bot.send_message(game['players'][0], "Ничья!")
            await bot.send_message(game['players'][1], "Ничья!")
            del games[callback_query.from_user.id]
        else:
            game['turn'] = 'O' if turn == 'X' else 'X'
            await bot.edit_message_text(render_board(board), callback_query.from_user.id, callback_query.message.message_id, reply_markup=create_board_keyboard())
            await bot.send_message(game['players'][0], "Ваш ход!" if game['turn'] == 'X' else "Ожидайте хода второго игрока.")
            await bot.send_message(game['players'][1], "Ваш ход!" if game['turn'] == 'O' else "Ожидайте хода первого игрока.")
    else:
        await callback_query.answer("Этот ход недоступен.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
        
