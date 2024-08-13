import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

games = {}

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Используй /newgame, чтобы начать новую игру или /singlegame для игры с AI.')

async def new_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    games[chat_id] = {
        'player1': update.message.from_user.id,
        'player2': None,
        'board': [' '] * 9,
        'turn': None,
        'game_active': True,
        'mode': 'multiplayer',
        'message_id': None
    }
    msg = await update.message.reply_text('Новая игра начата! Отправьте команду /invite, чтобы пригласить друга.')
    games[chat_id]['message_id'] = msg.message_id

async def single_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    games[chat_id] = {
        'player1': update.message.from_user.id,
        'player2': 'AI',
        'board': [' '] * 9,
        'turn': None,
        'game_active': True,
        'mode': 'single',
        'message_id': None
    }
    msg = await update.message.reply_text('Вы начали игру против AI. ИИ инициализирует игру.')
    games[chat_id]['message_id'] = msg.message_id
    await determine_first_move(update, context)

async def invite(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] is None:
        await context.bot.send_message(chat_id, 'Пересылайте сообщение вашего друга для приглашения.')
        return
    else:
        await update.message.reply_text('Игра уже начата или уже есть два игрока.')

async def handle_forwarded_message(update: Update, context: CallbackContext) -> None:
    message: Message = update.message
    if message.forward_from or message.forward_from_chat:
        chat_id = message.chat_id
        forwarded_user_id = message.forward_from.id if message.forward_from else None
        if chat_id in games and games[chat_id]['player2'] is None:
            if forwarded_user_id and forwarded_user_id != games[chat_id]['player1']:
                games[chat_id]['player2'] = forwarded_user_id
                await context.bot.send_message(
                    forwarded_user_id,
                    'Вас пригласили сыграть в крестики-нолики. Введите /join для начала игры.'
                )
                await message.reply_text(f'Приглашение отправлено пользователю с ID {forwarded_user_id}.')
                await determine_first_move(update, context)
            else:
                await message.reply_text('Нельзя пригласить себя или не найдено игрока.')
        else:
            await message.reply_text('Игра не найдена или уже начата.')
    else:
        await message.reply_text('Сообщение не является пересланным.')

async def join(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games and games[chat_id]['player2'] == update.message.from_user.id:
        games[chat_id]['game_active'] = True
        await context.bot.send_message(update.message.from_user.id, 'Вы присоединились к игре. Инициализация...')
        await determine_first_move(update, context)
    else:
        await update.message.reply_text('Вы не можете присоединиться к этой игре.')

def create_board_keyboard(board):
    keyboard = [[InlineKeyboardButton(text=board[i] if board[i] != ' ' else ' ', callback_data=str(i)) for i in range(3)],
                [InlineKeyboardButton(text=board[i] if board[i] != ' ' else ' ', callback_data=str(i)) for i in range(3, 6)],
                [InlineKeyboardButton(text=board[i] if board[i] != ' ' else ' ', callback_data=str(i)) for i in range(6, 9)]]
    return InlineKeyboardMarkup(keyboard)

async def show_board(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    if chat_id in games:
        game = games[chat_id]
        board = game['board']
        board_markup = create_board_keyboard(board)
        message_id = game['message_id']
        
        if message_id:
            try:
                await context.bot.edit_message_text(
                    text='Текущий статус игры:',
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=board_markup
                )
            except Exception as e:
                msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text='Текущий статус игры:',
                    reply_markup=board_markup
                )
                game['message_id'] = msg.message_id
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text='Текущий статус игры:',
                reply_markup=board_markup
            )
            game['message_id'] = msg.message_id

async def handle_button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    if data.startswith('invite_'):
        invited_user_id = int(data.split('_')[1])
        if chat_id in games and games[chat_id]['player2'] is None:
            if invited_user_id != games[chat_id]['player1']:
                games[chat_id]['player2'] = invited_user_id
                await context.bot.send_message(
                    invited_user_id,
                    'Вас пригласили сыграть в крестики-нолики. Введите /join для начала игры.'
                )
                await query.message.reply_text(f'Приглашение отправлено пользователю с ID {invited_user_id}.')
            else:
                await query.message.reply_text('Нельзя пригласить себя.')
        else:
            await query.message.reply_text('Игра не найдена или уже начата.')
        return

    move = int(data)
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
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    if chat_id in games and games[chat_id]['mode'] == 'single':
        game = games[chat_id]
        best_move = find_best_move(game['board'])
        game['board'][best_move] = 'O'
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

def find_best_move(board):
    best_move = -1
    best_score = -float('inf')
    for move in range(9):
        if board[move] == ' ':
            board[move] = 'O'
            score = minimax(board, False)
            board[move] = ' '
            if score > best_score:
                best_score = score
                best_move = move
    return best_move

def minimax(board, is_maximizing):
    winner = check_winner(board)
    if winner == 'AI':
        return 1
    elif winner == 'Player1':
        return -1
    elif ' ' not in board:
        return 0

    if is_maximizing:
        best_score = -float('inf')
        for move in range(9):
            if board[move] == ' ':
                board[move] = 'O'
                score = minimax(board, False)
                board[move] = ' '
                best_score = max(score, best_score)
        return best_score
    else:
        best_score = float('inf')
        for move in range(9):
            if board[move] == ' ':
                board[move] = 'X'
                score = minimax(board, True)
                board[move] = ' '
                best_score = min(score, best_score)
        return best_score

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

async def determine_first_move(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games:
        game = games[chat_id]
        if game['mode'] == 'single' and game['turn'] is None:
            game['turn'] = random.choice([game['player1'], 'AI'])
            if game['turn'] == 'AI':
                await ai_move(update, context)
            else:
                await show_board(update, context)
        elif game['turn'] is None:
            game['turn'] = game['player1']
            await show_board(update, context)

def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('newgame', new_game))
    application.add_handler(CommandHandler('singlegame', single_game))
    application.add_handler(CommandHandler('invite', invite))
    application.add_handler(CommandHandler('join', join))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_forwarded_message))
    application.run_polling()

if __name__ == '__main__':
    run_bot()
