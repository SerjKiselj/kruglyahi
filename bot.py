from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Хранилище для всех текущих игр
games = {}

def create_board():
    return [[" " for _ in range(3)] for _ in range(3)]

def board_to_string(board):
    return "\n".join([" | ".join(row) for row in board])

def check_win(board, player):
    win_conditions = [
        [board[0][0], board[0][1], board[0][2]],
        [board[1][0], board[1][1], board[1][2]],
        [board[2][0], board[2][1], board[2][2]],
        [board[0][0], board[1][0], board[2][0]],
        [board[0][1], board[1][1], board[2][1]],
        [board[0][2], board[1][2], board[2][2]],
        [board[0][0], board[1][1], board[2][2]],
        [board[0][2], board[1][1], board[2][0]],
    ]
    return [player, player, player] in win_conditions

async def start_game(context: ContextTypes.DEFAULT_TYPE, player1, player2):
    game_id = f"{player1}_{player2}"
    games[game_id] = {
        "board": create_board(),
        "turn": "X",
        "players": {player1: "X", player2: "O"},
        "current_player": player1,
    }
    board = games[game_id]["board"]

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

    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=player1, text="Игра началась! Вы играете за X. Ваш ход.", reply_markup=reply_markup)
    await context.bot.send_message(chat_id=player2, text="Игра началась! Вы играете за O. Ждите своего хода.")

async def lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /lobby <ID пользователя для приглашения>")
        return

    player1 = update.message.from_user.id
    player2 = int(context.args[0])

    await context.bot.send_message(chat_id=player2, text=f"Вас пригласили в игру крестики-нолики. Нажмите /join {player1}, чтобы принять приглашение.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /join <ID пользователя создавшего лобби>")
        return

    player1 = int(context.args[0])
    player2 = update.message.from_user.id

    await start_game(context, player1, player2)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_id, row, col = query.data.split("_")
    row, col = int(row), int(col)

    game = games[game_id]
    board = game["board"]
    current_player = game["current_player"]

    if query.from_user.id != current_player or board[row][col] != " ":
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

async def main():
    application = Application.builder().token("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s").build()

    application.add_handler(CommandHandler("lobby", lobby))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CallbackQueryHandler(button))

    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    # Если цикл событий уже запущен, используем run_polling() без asyncio.run()
    try:
        asyncio.run(main())
    except RuntimeError:  # В случае ошибки запускаем run_polling() напрямую
        application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
        application.run_polling()
        
