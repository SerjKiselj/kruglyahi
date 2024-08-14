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
    keyboard = [
        [InlineKeyboardButton(board[i*3 + j] or str(i*3 + j + 1), callback_data=str(i*3 + j)) for j in range(3)]
        for i in range(3)
    ]
    return InlineKeyboardMarkup(keyboard)

# Простая и сложная стратегии ИИ
def make_ai_move(board, difficulty):
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if difficulty == 'easy':
        move = random.choice(empty_positions)
    else:
        # Сложная стратегия ИИ
        # ИИ пытается выиграть или заблокировать игрока
        for move in empty_positions:
            board[move] = PLAYER_O
            if check_win(board, PLAYER_O):
                return move
            board[move] = EMPTY
        
        for move in empty_positions:
            board[move] = PLAYER_X
            if check_win(board, PLAYER_X):
                board[move] = PLAYER_O
                return move
            board[move] = EMPTY

        move = random.choice(empty_positions)
    
    board[move] = PLAYER_O
    return move

# Обновление сообщения с игровым полем
async def update_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data.get('board')
    if board:
        await update.callback_query.message.edit_text(
            "Игра в крестики-нолики\n\n",
            reply_markup=format_keyboard(board)
        )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['board'] = start_game()
    context.user_data['player_turn'] = True
    context.user_data['difficulty'] = 'easy'  # Уровень сложности ИИ, по умолчанию easy
    await update.message.reply_text(
        "Игра началась! Вы играете за 'X'. Выберите клетку на поле:\n\n" +
        "Уровень сложности ИИ: Easy. Используйте команду /difficulty <easy|hard> для смены сложности.",
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
        await update_message(update, context)
        await query.message.reply_text("Поздравляю, вы выиграли!")
        context.user_data['board'] = None
        return

    if check_draw(board):
        await update_message(update, context)
        await query.message.reply_text("Ничья!")
        context.user_data['board'] = None
        return

    ai_move = make_ai_move(board, context.user_data['difficulty'])

    if check_win(board, PLAYER_O):
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

# Команда /difficulty для изменения уровня сложности
async def difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or context.args[0] not in ['easy', 'hard']:
        await update.message.reply_text("Используйте команду /difficulty <easy|hard> для изменения уровня сложности.")
        return
    
    context.user_data['difficulty'] = context.args[0]
    await update.message.reply_text(f"Уровень сложности ИИ изменен на {context.args[0].capitalize()}.")

async def main():
    # Вставьте сюда свой токен
    TOKEN = "7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("difficulty", difficulty))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот запущен. Нажмите Ctrl+C для завершения.")
    # Запуск бота
    await app.run_polling()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    
