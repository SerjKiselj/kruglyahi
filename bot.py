from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
import random

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

games = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Используй /newgame, чтобы начать новую игру или /singlegame для игры с AI.')

async def new_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    games[chat_id] = {
        'player1': update.message.from_user.id,
        'player2': None,
        'board': [' '] * 9,
        'turn': update.message.from_user.id,
        'game_active': True,
        'mode': 'multiplayer'
    }
    await update.message.reply_text('Новая игра начата! Отправьте команду /invite, чтобы пригласить друга.')

async def single_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    games[chat_id] = {
        'player1': update.message.from_user.id,
        'player2': 'AI',
        'board': [' '] * 9,
        'turn': update.message.from_user.id,
        'game_active': True,
        'mode': 'single'
    }
    await update.message.reply_text('Вы начали игру против AI. Ваш ход!')
    await show_board(update, context)

async def invite(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] is None:
        await context.bot.send_message(chat_id, 'Введите @username вашего друга для приглашения:')
        return
    else:
        await update.message.reply_text('Игра уже начата или уже есть два игрока.')

async def handle_invite(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] is None:
        user = update.message.text.split('@')[1]
        try:
            user_id = (await context.bot.get_chat(username=user)).id
            if user_id != games[chat_id]['player1']:
                games[chat_id]['player2'] = user_id
                await context.bot.send_message(user_id, 'Вас пригласили сыграть в крестики-нолики. Введите /join для начала игры.')
                await update.message.reply_text(f'Приглашение отправлено игроку @{user}.')
            else:
                await update.message.reply_text('Нельзя пригласить себя.')
        except:
            await update.message.reply_text('Не удалось найти пользователя с этим username.')
    else:
        await update.message.reply_text('Игра не найдена или уже начата.')

async def join(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] == update.message.from_user.id:
        games[chat_id]['game_active'] = True
        await context.bot.send_message(update.message.from_user.id, 'Вы присоединились к игре. Ваш ход!')
        await show_board(update, context)
    else:
        await update.message.reply_text('Вы не можете присоединиться к этой игре.')

def create_board_keyboard(board):
    keyboard = [[InlineKeyboardButton(text=board[i] if board[i] != ' ' else f'{i+1}', callback_data=str(i)) for i in range(3)],
                [InlineKeyboardButton(text=board[i] if board[i] != ' ' else f'{i+1}', callback_data=str(i)) for i in range(3, 6)],
                [InlineKeyboardButton(text=board[i] if board[i] != ' ' else f'{i+1}', callback_data=str(i)) for i in range(6, 9)]]
    return InlineKeyboardMarkup(keyboard)

async def show_board(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games:
        game = games[chat_id]
        board = game['board']
        board_markup = create_board_keyboard(board)
        await context.bot.send_message(chat_id, 'Текущий статус игры:', reply_markup=board_markup)

async def handle_button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    move = int(query.data)
    if chat_id in games:
        game = games[chat_id]
        if not game['game_active']:
            await query.answer('Игра завершена. Используйте /newgame для начала новой.')
            return
        
        if game['board'][move] == ' ':
            current_player = game['turn']
            if current_player != query.from_user.id:
                await query.answer('Не ваш ход.')
                return

            game['board'][move] = 'X' if current_player == game['player1'] else 'O'
            winner = check_winner(game['board'])
            
            if winner:
                await query.message.edit_text(f"Игрок {winner} победил! Поздравляю!")
                game['game_active'] = False
            elif ' ' not in game['board']:
                await query.message.edit_text("Ничья!")
                game['game_active'] = False
            else:
                game['turn'] = game['player2'] if current_player == game['player1'] else game['player1']
                if game['mode'] == 'single' and game['turn'] == 'AI':
                    await ai_move(update, context)
                else:
                    await show_board(update, context)
        else:
            await query.answer('Эта клетка уже занята.')
    else:
        await query.answer('Игра не найдена.')

async def ai_move(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['mode'] == 'single':
        game = games[chat_id]
        available_moves = [i for i, spot in enumerate(game['board']) if spot == ' ']
        move = random.choice(available_moves)
        game['board'][move] = 'O'
        winner = check_winner(game['board'])
        
        if winner:
            await context.bot.send_message(chat_id, f"AI победил! Поздравляю AI!")
            game['game_active'] = False
        elif ' ' not in game['board']:
            await context.bot.send_message(chat_id, "Ничья!")
            game['game_active'] = False
        else:
            game['turn'] = game['player1']
            await show_board(update, context)

def check_winner(board):
    winning_combinations = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8), # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8), # columns
        (0, 4, 8), (2, 4, 6)  # diagonals
    ]
    for a, b, c in winning_combinations:
        if board[a] == board[b] == board[c] and board[a] != ' ':
            return 'Player1' if board[a] == 'X' else 'AI'
    return None

def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('newgame', new_game))
    application.add_handler(CommandHandler('singlegame', single_game))
    application.add_handler(CommandHandler('invite', invite))
    application.add_handler(CommandHandler('join', join))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.run_polling()

if __name__ == '__main__':
    run_bot()
