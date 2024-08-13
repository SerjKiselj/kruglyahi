from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import asyncio
import random

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

async def show_board(update: Update, context: CallbackContext) -> None:
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
        await context.bot.send_message(chat_id, f"Текущий статус игры:\n{board_str}\n\nСделайте свой ход (введите номер клетки от 1 до 9):")

async def make_move(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in games:
        game = games[chat_id]
        if not game['game_active']:
            await update.message.reply_text('Игра завершена. Используйте /newgame для начала новой.')
            return
        
        move = int(update.message.text) - 1
        if 0 <= move < 9:
            if game['board'][move] == ' ':
                current_player = game['turn']
                if current_player != update.message.from_user.id:
                    await update.message.reply_text('Не ваш ход.')
                    return
                
                game['board'][move] = 'X' if current_player == game['player1'] else 'O'
                winner = check_winner(game['board'])
                
                if winner:
                    await context.bot.send_message(chat_id, f"Игрок {winner} победил! Поздравляю!")
                    game['game_active'] = False
                elif ' ' not in game['board']:
                    await context.bot.send_message(chat_id, "Ничья!")
                    game['game_active'] = False
                else:
                    game['turn'] = game['player2'] if current_player == game['player1'] else game['player1']
                    if game['mode'] == 'single' and game['turn'] == 'AI':
                        await ai_move(update, context)
                    else:
                        await show_board(update, context)
            else:
                await update.message.reply_text('Эта клетка уже занята.')
        else:
            await update.message.reply_text('Неверный ввод. Введите номер клетки от 1 до 9.')
    else:
        await update.message.reply_text('Игра не найдена.')

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, make_move))
    application.run_polling()

if __name__ == '__main__':
    run_bot()
