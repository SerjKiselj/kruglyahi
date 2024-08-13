from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

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

def start_game(update: Update, context: CallbackContext, player1, player2):
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
    context.bot.send_message(chat_id=player1, text="Игра началась! Вы играете за X. Ваш ход.", reply_markup=reply_markup)
    context.bot.send_message(chat_id=player2, text="Игра началась! Вы играете за O. Ждите своего хода.")

def lobby(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Использование: /lobby <ID пользователя для приглашения>")
        return

    player1 = update.message.from_user.id
    player2 = int(context.args[0])

    context.bot.send_message(chat_id=player2, text=f"Вас пригласили в игру крестики-нолики. Нажмите /join {player1}, чтобы принять приглашение.")

def join(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Использование: /join <ID пользователя создавшего лобби>")
        return

    player1 = int(context.args[0])
    player2 = update.message.from_user.id

    start_game(update, context, player1, player2)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    game_id, row, col = query.data.split("_")
    row, col = int(row), int(col)

    game = games[game_id]
    board = game["board"]
    current_player = game["current_player"]

    if query.from_user.id != current_player or board[row][col] != " ":
        return

    board[row][col] = game["players"][current_player]

    if check_win(board, game["players"][current_player]):
        query.edit_message_text(text=f"Игрок {game['players'][current_player]} победил!\n\n{board_to_string(board)}")
        context.bot.send_message(chat_id=game_id.split("_")[0], text=f"Игра окончена. Вы победили!")
        context.bot.send_message(chat_id=game_id.split("_")[1], text=f"Игра окончена. Вы проиграли.")
        del games[game_id]
        return

    if all(all(cell != " " for cell in row) for row in board):
        query.edit_message_text(text=f"Ничья!\n\n{board_to_string(board)}")
        context.bot.send_message(chat_id=game_id.split("_")[0], text=f"Игра окончена. Ничья.")
        context.bot.send_message(chat_id=game_id.split("_")[1], text=f"Игра окончена. Ничья.")
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

    query.edit_message_text(text=f"Ходит игрок {game['players'][game['current_player']]}. \n\n{board_to_string(board)}", reply_markup=InlineKeyboardMarkup(buttons))

def main():
    updater = Updater("7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s", use_context=True)

    updater.dispatcher.add_handler(CommandHandler("lobby", lobby))
    updater.dispatcher.add_handler(CommandHandler("join", join))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
    
