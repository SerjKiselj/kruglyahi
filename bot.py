import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from uuid import uuid4

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Хранилище игр
games = {}

# Функция для проверки победы
def check_win(board, player):
    win_conditions = [
        # Проверка строк
        [board[0][0], board[0][1], board[0][2]],
        [board[1][0], board[1][1], board[1][2]],
        [board[2][0], board[2][1], board[2][2]],
        # Проверка колонок
        [board[0][0], board[1][0], board[2][0]],
        [board[0][1], board[1][1], board[2][1]],
        [board[0][2], board[1][2], board[2][2]],
        # Проверка диагоналей
        [board[0][0], board[1][1], board[2][2]],
        [board[2][0], board[1][1], board[0][2]],
    ]
    return [player, player, player] in win_conditions

# Функция для преобразования доски в строку
def board_to_string(board):
    return "\n".join([" | ".join(row) for row in board])

# Функция обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Используйте команды /lobby для создания лобби и /join для присоединения.')

# Функция для создания нового лобби
async def lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    game_id = str(uuid4())
    board = [[" " for _ in range(3)] for _ in range(3)]
    games[game_id] = {
        "players": {user_id: "X"},
        "current_player": user_id,
        "board": board
    }
    await update.message.reply_text(
        "Лобби создано. Дождитесь, пока ваш друг присоединится. Скопируйте этот ID лобби для вашего друга: " + game_id
    )

# Функция для присоединения к лобби
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    game_id = context.args[0] if context.args else None
    
    if game_id not in games:
        await update.message.reply_text("Лобби не найдено.")
        return
    
    game = games[game_id]
    
    if len(game["players"]) == 2:
        await update.message.reply_text("Лобби уже заполнено.")
        return

    if user_id in game["players"]:
        await update.message.reply_text("Вы уже в этой игре.")
        return

    game["players"][user_id] = "O"
    await update.message.reply_text(f"Вы присоединились к лобби {game_id}.")
    
    # Создаем клавиатуру для текущего состояния игры
    buttons = [
        [InlineKeyboardButton(board[0][0], callback_data=f"{game_id}_0_0"),
         InlineKeyboardButton(board[0][1], callback_data=f"{game_id}_0_1"),
         InlineKeyboardButton(board[0][2], callback_data=f"{game_id}_0_2")],
        [InlineKeyboardButton(board[1][0], callback_data=f"{game_id}_1_0"),
         InlineKeyboardButton(board[1][1], callback_data=f"{game_id}_1_1"),
         InlineKeyboardButton(board[1][2], callback_data=f"{game_id}_1_2")],
        [InlineKeyboardButton(board[2][0], callback_data=f"{game_id}_2_0"),
         InlineKeyboardButton(board[2][1], callback_data=f"{game_id}_2_1"),
         InlineKeyboardButton(board[2][2], callback_data=f"{game_id}_2_2")],
    ]

    await update.message.reply_text(
        f"Игра началась! Ваш ход.\n\n{board_to_string(board)}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Функция обработки нажатий кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        parts = query.data.split("_")
        logging.info(f"Полученные данные из callback_data: {parts}")

        if len(parts) != 3:
            logging.error(f"Некорректные данные в callback_data: {query.data}")
            await query.edit_message_text(text="Некорректные данные в callback_data.")
            return

        game_id, row, col = parts
        row, col = int(row), int(col)

        if game_id not in games:
            await query.edit_message_text(text="Игра не найдена.")
            return

        game = games[game_id]
        board = game["board"]
        current_player = game["current_player"]

        if query.from_user.id != current_player:
            await query.answer("Не ваш ход.")
            return

        if board[row][col] != " ":
            await query.answer("Эта клетка уже занята.")
            return

        board[row][col] = game["players"][current_player]

        if check_win(board, game["players"][current_player]):
            await query.edit_message_text(text=f"Игрок {game['players'][current_player]} победил!\n\n{board_to_string(board)}")
            await context.bot.send_message(chat_id=game_id.split("_")[0], text=f"Игра окончена. Вы победили!")
            await context.bot.send_message(chat_id=game_id.split("_")[1], text=f"Игра окончена. Вы проиграли.")
            del games[game_id]
            return

        if all(all(cell != " " for cell in row) for row in board):
            await query.edit_message_text(text=f"Ничья!\n\n{board_to_string(board)}")
            await context.bot.send_message(chat_id=game_id.split("_")[0], text=f"Игра окончена. Ничья.")
            await context.bot.send_message(chat_id=game_id.split("_")[1], text=f"Игра окончена. Ничья.")
            del games[game_id]
            return

        game["current_player"] = game_id.split("_")[1] if current_player == int(game_id.split("_")[0]) else int(game_id.split("_")[0])

        buttons = [
            [InlineKeyboardButton(board[0][0], callback_data=f"{game_id}_0_0"),
             InlineKeyboardButton(board[0][1], callback_data=f"{game_id}_0_1"),
             InlineKeyboardButton(board[0][2], callback_data=f"{game_id}_0_2")],
            [InlineKeyboardButton(board[1][0], callback_data=f"{game_id}_1_0"),
             InlineKeyboardButton(board[1][1], callback_data=f"{game_id}_1_1"),
             InlineKeyboardButton(board[1][2], callback_data=f"{game_id}_1_2")],
            [InlineKeyboardButton(board[2][0], callback_data=f"{game_id}_2_0"),
             InlineKeyboardButton(board[2][1], callback_data=f"{game_id}_2_1"),
             InlineKeyboardButton(board[2][2], callback_data=f"{game_id}_2_2")],
        ]

        await query.edit_message_text(text=f"Ходит игрок {game['players'][game['current_player']]}. \n\n{board_to_string(board)}", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logging.error(f"Ошибка обработки нажатия кнопки: {e}")
        await query.edit_message_text(text="Ошибка обработки нажатия кнопки.")

# Основная функция для запуска бота
async def main():
    application = Application.builder().token("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lobby", lobby))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CallbackQueryHandler(button))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
    
