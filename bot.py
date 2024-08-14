import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import asyncio

# Символы
EMPTY, PLAYER_X, PLAYER_O = ' ', 'X', 'O'

# Выигрышные комбинации
WIN_COMBOS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],  # горизонтальные линии
    [0, 3, 6], [1, 4, 7], [2, 5, 8],  # вертикальные линии
    [0, 4, 8], [2, 4, 6]  # диагональные линии
]

# Начальное состояние игры
def start_game():
    return [EMPTY] * 9

# Проверка победы
def check_win(board, player):
    for combo in WIN_COMBOS:
        if all(board[pos] == player for pos in combo):
            return True
    return False

# Проверка на ничью
def check_draw(board):
    return all(cell != EMPTY for cell in board)

# Отображение игрового поля
def format_board(board):
    return "\n".join([" | ".join(board[i:i+3]) for i in range(0, 9, 3)])

# Ход ИИ
def make_ai_move(board):
    # ИИ пытается сначала выиграть
    for move in range(9):
        if board[move] == EMPTY:
            board[move] = PLAYER_O
            if check_win(board, PLAYER_O):
                return
            board[move] = EMPTY
    
    # Если выиграть не получилось, пытается блокировать игрока
    for move in range(9):
        if board[move] == EMPTY:
            board[move] = PLAYER_X
            if check_win(board, PLAYER_X):
                board[move] = PLAYER_O
                return
            board[move] = EMPTY
    
    # Если и блокировать не надо, выбирает случайный ход
    while True:
        move = random.randint(0, 8)
        if board[move] == EMPTY:
            board[move] = PLAYER_O
            break

# Старт игры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['board'] = start_game()
    await update.message.reply_text("Игра началась! Вы играете за 'X'. Выберите клетку (1-9):")
    await update.message.reply_text(format_board(context.user_data['board']))

# Ход игрока
async def move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data.get('board')
    if not board:
        await update.message.reply_text("Начните новую игру командой /start")
        return

    try:
        player_move = int(update.message.text) - 1
        if board[player_move] != EMPTY:
            await update.message.reply_text("Эта клетка уже занята!")
            return
    except (ValueError, IndexError):
        await update.message.reply_text("Введите номер клетки от 1 до 9.")
        return
    
    board[player_move] = PLAYER_X

    if check_win(board, PLAYER_X):
        await update.message.reply_text(format_board(board))
        await update.message.reply_text("Поздравляю, вы выиграли!")
        context.user_data['board'] = None
        return
    
    if check_draw(board):
        await update.message.reply_text(format_board(board))
        await update.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return
    
    make_ai_move(board)

    if check_win(board, PLAYER_O):
        await update.message.reply_text(format_board(board))
        await update.message.reply_text("Вы проиграли!")
        context.user_data['board'] = None
        return
    
    if check_draw(board):
        await update.message.reply_text(format_board(board))
        await update.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return
    
    await update.message.reply_text(format_board(board))
    await update.message.reply_text("Ваш ход! Выберите клетку (1-9):")

async def main():
    # Вставьте сюда свой токен
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, move))

    # Запуск бота без создания нового цикла событий
    await app.initialize()
    await app.start()
    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == '__main__':
    # Запуск main без asyncio.run
    asyncio.get_event_loop().run_until_complete(main())
