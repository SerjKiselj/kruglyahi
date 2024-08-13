from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

games = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Привет! Используй /newgame, чтобы начать новую игру.')

def new_game(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    games[chat_id] = {
        'player1': update.message.from_user.id,
        'player2': None,
        'board': [' '] * 9,
        'turn': update.message.from_user.id,
        'game_active': True
    }
    update.message.reply_text('Новая игра начата! Отправьте команду /invite, чтобы пригласить друга.')

def invite(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] is None:
        context.bot.send_message(chat_id, 'Введите @username вашего друга для приглашения:')
        return
    else:
        update.message.reply_text('Игра уже начата или уже есть два игрока.')

def handle_invite(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] is None:
        user = update.message.text.split('@')[1]
        try:
            user_id = context.bot.get_chat(username=user).id
            if user_id != games[chat_id]['player1']:
                games[chat_id]['player2'] = user_id
                context.bot.send_message(user_id, 'Вас пригласили сыграть в крестики-нолики. Введите /join для начала игры.')
                update.message.reply_text(f'Приглашение отправлено игроку @{user}.')
            else:
                update.message.reply_text('Нельзя пригласить себя.')
        except:
            update.message.reply_text('Не удалось найти пользователя с этим username.')
    else:
        update.message.reply_text('Игра не найдена или уже начата.')

def join(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] == update.message.from_user.id:
        games[chat_id]['game_active'] = True
        context.bot.send_message(update.message.from_user.id, 'Вы присоединились к игре. Ваш ход!')
        show_board(update, context)
    else:
        update.message.reply_text('Вы не можете присоединиться к этой игре.')

def show_board(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in games:
        game = games[chat_id]
        board = game['board']
        board_str = '\n'.join([
            f"{board[0]} | {board[1]} | {board[2]}",
            "--+---+--",
            f"{board[3]} | {board[4]} | {board[5]}",
            "--+---+--",
            f"{board[6]} | {board[7]} | {board[8]}"
        ])
        context.bot.send_message(chat_id, f"Текущий статус игры:\n{board_str}\n\nСделайте свой ход (введите номер клетки от 1 до 9):")

def make_move(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in games:
        game = games[chat_id]
        if not game['game_active']:
            update.message.reply_text('Игра завершена. Используйте /newgame для начала новой.')
            return
        
        move = int(update.message.text) - 1
        if 0 <= move < 9:
            if game['board'][move] == ' ':
                current_player = game['turn']
                if current_player != update.message.from_user.id:
                    update.message.reply_text('Не ваш ход.')
                    return
                
                game['board'][move] = 'X' if current_player == game['player1'] else 'O'
                winner = check_winner(game['board'])
                
                if winner:
                    context.bot.send_message(chat_id, f"Игрок {winner} победил! Поздравляю!")
                    game['game_active'] = False
                elif ' ' not in game['board']:
                    context.bot.send_message(chat_id, "Ничья!")
                    game['game_active'] = False
                else:
                    game['turn'] = game['player2'] if current_player == game['player1'] else game['player1']
                    show_board(update, context)
            else:
                update.message.reply_text('Эта клетка уже занята.')
        else:
            update.message.reply_text('Неверный ввод. Введите номер клетки от 1 до 9.')
    else:
        update.message.reply_text('Игра не найдена.')

def check_winner(board):
    winning_combinations = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8), # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8), # columns
        (0, 4, 8), (2, 4, 6)  # diagonals
    ]
    for a, b, c in winning_combinations:
        if board[a] == board[b] == board[c] and board[a] != ' ':
            return 'Player1' if board[a] == 'X' else 'Player2'
    return None

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('newgame', new_game))
    dp.add_handler(CommandHandler('invite', invite))
    dp.add_handler(CommandHandler('join', join))
    dp.add_handler(MessageHandler(None, make_move))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
