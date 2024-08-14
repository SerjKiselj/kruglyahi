import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.utils.exceptions import MessageNotModified

# Устанавливаем токен вашего бота
API_TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Храним текущие игры и их состояния
games = {}

# Генерация пустого игрового поля
def create_board():
    return [' '] * 9

# Отрисовка игрового поля в виде строки
def render_board(board):
    return (f"{board[0]} | {board[1]} | {board[2]}\n"
            f"---------\n"
            f"{board[3]} | {board[4]} | {board[5]}\n"
            f"---------\n"
            f"{board[6]} | {board[7]} | {board[8]}")

# Создание кнопок для игрового поля
def create_board_markup(board):
    markup = InlineKeyboardMarkup()
    for i in range(0, 9, 3):
        markup.row(
            InlineKeyboardButton(board[i], callback_data=f"move_{i}"),
            InlineKeyboardButton(board[i+1], callback_data=f"move_{i+1}"),
            InlineKeyboardButton(board[i+2], callback_data=f"move_{i+2}"),
        )
    return markup

# Проверка на победу
def check_winner(board, player):
    win_positions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for positions in win_positions:
        if all(board[i] == player for i in positions):
            return True
    return False

# Обработка старта игры
@dp.message_handler(commands=['start', 'newgame'])
async def send_welcome(message: types.Message):
    games[message.chat.id] = {
        'board': create_board(),
        'current_player': 'X',
        'players': [message.from_user.id, None]
    }
    await message.answer("Игра началась! Ждем второго игрока. Пригласите его командой /join")

# Подключение второго игрока
@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    if message.chat.id in games and games[message.chat.id]['players'][1] is None:
        games[message.chat.id]['players'][1] = message.from_user.id
        await message.answer("Второй игрок подключился! Игрок X начинает.")
        board = games[message.chat.id]['board']
        await message.answer(render_board(board), reply_markup=create_board_markup(board))
    else:
        await message.answer("Игра уже идет или вы не можете присоединиться.")

# Обработка ходов
@dp.callback_query_handler(lambda c: c.data.startswith('move_'))
async def process_callback(callback_query: types.CallbackQuery):
    game = games.get(callback_query.message.chat.id)
    if not game:
        return
    
    player = 'X' if callback_query.from_user.id == game['players'][0] else 'O'
    if player != game['current_player']:
        await callback_query.answer("Не ваш ход!")
        return
    
    move = int(callback_query.data.split('_')[1])
    if game['board'][move] == ' ':
        game['board'][move] = player
        if check_winner(game['board'], player):
            await bot.edit_message_text(f"Игрок {player} победил!\n{render_board(game['board'])}",
                                        callback_query.message.chat.id,
                                        callback_query.message.message_id)
            del games[callback_query.message.chat.id]
            return
        elif ' ' not in game['board']:
            await bot.edit_message_text(f"Ничья!\n{render_board(game['board'])}",
                                        callback_query.message.chat.id,
                                        callback_query.message.message_id)
            del games[callback_query.message.chat.id]
            return
        else:
            game['current_player'] = 'O' if game['current_player'] == 'X' else 'X'
            try:
                await bot.edit_message_text(render_board(game['board']),
                                            callback_query.message.chat.id,
                                            callback_query.message.message_id,
                                            reply_markup=create_board_markup(game['board']))
            except MessageNotModified:
                pass
    else:
        await callback_query.answer("Эта клетка уже занята!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    
