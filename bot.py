import random
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import asyncio

nest_asyncio.apply()  # Патч для asyncio

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

# Форматирование клавиатуры
def format_keyboard(board):
    keyboard = [[InlineKeyboardButton(board[i*3 + j] or str(i*3 + j + 1), callback_data=str(i*3 + j)) for j in range(3)] for i in range(3)]
    return InlineKeyboardMarkup(keyboard)

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

# Обновление сообщения
async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE, board):
    await update.callback_query.message.edit_text(
        "Игра в крестики-нолики\n\n" + format_board(board),
        reply_markup=format_keyboard(board)
    )

# Отображение игрового поля
def format_board(board):
    return "\n".join([" | ".join(board[i:i+3]) for i in range(0, 9, 3)])

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['board'] = start_game()
    context.user_data['player_turn'] = True
    await update.message.reply_text(
        "Игра началась! Вы играете за 'X'. Выберите клетку (1-9):",
        reply_markup=format_keyboard(context.user_data['board'])
    )

# Обработка кликов на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    board = context.user_data.get('board')
    
    if not board:
        await query.message.reply_text("Начните новую игру командой /start")
        return
    
    player_move = int(query.data)

    if board[player_move] != EMPTY:
        await query.answer("Эта клетка уже занята!")
        return
    
    if not context.user_data['player_turn']:
        await query.answer("Сейчас ход ИИ!")
        return

    board[player_move] = PLAYER_X
    context.user_data['player_turn'] = False

    if check_win(board, PLAYER_X):
        await update_message(update, context, board)
        await query.message.reply_text("Поздравляю, вы выиграли!")
        context.user_data['board'] = None
        return
    
    if check_draw(board):
        await update_message(update, context, board)
        await query.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return

    make_ai_move(board)

    if check_win(board, PLAYER_O):
        await update_message(update, context, board)
        await query.message.reply_text("Вы проиграли!")
        context.user_data['board'] = None
        return
    
    if check_draw(board):
        await update_message(update, context, board)
        await query.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return
    
    context.user_data['player_turn'] = True
    await update_message(update, context, board)

async def main():
    # Вставьте сюда свой токен
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    # Запуск бота
    await app.run_polling()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
