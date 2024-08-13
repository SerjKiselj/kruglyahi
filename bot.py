import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters

TOKEN = '7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s'

games = {}  # Словарь для хранения данных о текущих играх

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Используйте /newgame для начала новой игры или /singlegame для игры с AI.')

async def new_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    game_id = str(random.randint(1000, 9999))  # Генерация уникального ID игры
    games[game_id] = {
        'player1': chat_id,
        'player2': None,
        'board': [' '] * 9,
        'turn': chat_id,
        'game_active': True,
        'mode': 'multiplayer',
        'message_id': None
    }
    await update.message.reply_text(f'Новая игра начата! Пригласите друга, используя его ID, отправив команду /invite {game_id} <ID_друга>')

async def single_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    game_id = str(random.randint(1000, 9999))
    games[game_id] = {
        'player1': chat_id,
        'player2': 'AI',
        'board': [' '] * 9,
        'turn': chat_id,
        'game_active': True,
        'mode': 'single',
        'message_id': None
    }
    msg = await update.message.reply_text('Вы начали игру против AI. ИИ инициализирует игру.')
    games[game_id]['message_id'] = msg.message_id
    await determine_first_move(update, context)

async def invite(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    args = context.args
    if len(args) != 2:
        await update.message.reply_text('Используйте команду /invite <game_id> <user_id>')
        return

    game_id = args[0]
    friend_id = int(args[1])

    if game_id in games:
        game = games[game_id]
        if game['player2'] is None:
            if game['player1'] != friend_id:
                game['player2'] = friend_id
                await context.bot.send_message(friend_id, f'Вас пригласили в игру! Введите /join {game_id} для присоединения.')
                await update.message.reply_text(f'Приглашение отправлено пользователю с ID {friend_id}.')
            else:
                await update.message.reply_text('Нельзя пригласить себя.')
        else:
            await update.message.reply_text('Игра уже имеет двух игроков или завершена.')
    else:
        await update.message.reply_text('Игра не найдена.')

async def join(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    args = context.args
    if len(args) != 1:
        await update.message.reply_text('Используйте команду /join <game_id>')
        return

    game_id = args[0]

    if game_id in games:
        game = games[game_id]
        if game['player2'] == chat_id:
            game['game_active'] = True
            await update.message.reply_text('Вы присоединились к игре! Инициализация...')
            await determine_first_move(update, context)
        else:
            await update.message.reply_text('Вы не можете присоединиться к этой игре.')
    else:
        await update.message.reply_text('Игра не найдена.')

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
                await show_board(update, context)
        else:
            await query.answer('Эта клетка уже занята.')
    else:
        await query.answer('Игра не найдена.')

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
    application.run_polling()

if __name__ == '__main__':
    run_bot()
