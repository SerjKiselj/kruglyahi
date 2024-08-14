import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor

API_TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

games = {}

def render_board(board):
    return '\n'.join([' | '.join(row) for row in board])

def check_winner(board):
    # Check rows, columns and diagonals for a winner
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

def check_draw(board):
    return all(cell != ' ' for row in board for cell in row)

async def start_game(game_id):
    game = games[game_id]
    player = game['players'][game['turn']]
    board = render_board(game['board'])
    await bot.send_message(player, f"Ваш ход!\n\n{board}")

@dp.message_handler(commands=['newgame'])
async def new_game(message: types.Message):
    if message.from_user.id in games:
        await message.answer("Вы уже начали игру. Сначала завершите текущую игру.")
        return
    
    games[message.from_user.id] = {
        'board': [[' ' for _ in range(3)] for _ in range(3)],
        'players': [message.from_user.id, None],
        'turn': 0,
    }
    await message.answer("Игра создана! Пригласите игрока с помощью команды /invite @username")

@dp.message_handler(commands=['invite'])
async def invite_player(message: types.Message):
    if message.from_user.id not in games:
        await message.answer("Сначала создайте игру с помощью команды /newgame.")
        return
    
    if len(message.text.split()) < 2:
        await message.answer("Пожалуйста, укажите имя пользователя через @, которого вы хотите пригласить.")
        return

    username = message.text.split()[1]
    
    try:
        user = await bot.get_chat(username)
    except Exception as e:
        await message.answer(f"Не удалось найти пользователя {username}. Проверьте правильность ввода или убедитесь, что пользователь активировал бота.")
        return

    if games[message.from_user.id]['players'][1] is None:
        games[message.from_user.id]['players'][1] = user.id
        await bot.send_message(user.id, f"Вас пригласили в игру 'Крестики-нолики'. Чтобы присоединиться, введите /join.")
        await message.answer(f"Приглашение отправлено пользователю {username}.")
    else:
        await message.answer("Игрок уже присоединился.")

@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    for game_id, game in games.items():
        if game['players'][1] == message.from_user.id and game['turn'] == 0:
            await message.answer("Вы успешно присоединились к игре! Первый ход делает создатель игры.")
            await bot.send_message(game['players'][0], f"Игрок присоединился к игре! Вы делаете первый ход.")
            await start_game(game_id)
            return
    await message.answer("У вас нет активных приглашений.")

@dp.message_handler(commands=['move'])
async def make_move(message: types.Message):
    if message.from_user.id not in games:
        await message.answer("Вы не участвуете в активной игре.")
        return
    
    game = games[message.from_user.id]
    
    if game['players'][game['turn']] != message.from_user.id:
        await message.answer("Сейчас не ваш ход.")
        return
    
    try:
        move = int(message.text.split()[1]) - 1
        row, col = divmod(move, 3)
    except:
        await message.answer("Пожалуйста, введите правильный номер клетки (1-9).")
        return
    
    if not (0 <= move <= 8) or game['board'][row][col] != ' ':
        await message.answer("Недопустимый ход. Выберите пустую клетку.")
        return
    
    game['board'][row][col] = 'X' if game['turn'] == 0 else 'O'
    winner = check_winner(game['board'])
    if winner:
        await bot.send_message(game['players'][0], f"Игра окончена! Победитель: {winner}")
        await bot.send_message(game['players'][1], f"Игра окончена! Победитель: {winner}")
        del games[message.from_user.id]
        return
    
    if check_draw(game['board']):
        await bot.send_message(game['players'][0], "Игра окончена! Ничья!")
        await bot.send_message(game['players'][1], "Игра окончена! Ничья!")
        del games[message.from_user.id]
        return
    
    game['turn'] = 1 - game['turn']
    await start_game(message.from_user.id)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
    
