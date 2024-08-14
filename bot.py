import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Constants
EMPTY = 0
PLAYER_X = 1
PLAYER_O = 2
BOARD_SIZE = 9

def create_board():
    return [EMPTY] * BOARD_SIZE

def display_board(board):
    symbols = {EMPTY: '⬜️', PLAYER_X: '❌', PLAYER_O: '⭕️'}
    return '\n'.join(' '.join(symbols[cell] for cell in board[i:i+3]) for i in range(0, BOARD_SIZE, 3))

def check_win(board, player):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    return any(all(board[pos] == player for pos in condition) for condition in win_conditions)

def check_draw(board):
    return all(cell != EMPTY for cell in board) and not check_win(board, PLAYER_X) and not check_win(board, PLAYER_O)

def block_or_win(board, player):
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    for move in range(BOARD_SIZE):
        if board[move] == EMPTY:
            board[move] = player
            if check_win(board, player):
                board[move] = EMPTY
                return move
            board[move] = EMPTY
    for move in range(BOARD_SIZE):
        if board[move] == EMPTY:
            board[move] = opponent
            if check_win(board, opponent):
                board[move] = EMPTY
                return move
            board[move] = EMPTY
    return None

def minimax(board, player, alpha, beta):
    opponent = PLAYER_X if player == PLAYER_O else PLAYER_O
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if check_win(board, PLAYER_X):
        return (-10, None)
    if check_win(board, PLAYER_O):
        return (10, None)
    if check_draw(board):
        return (0, None)

    best_move = None

    if player == PLAYER_O:
        best_score = float('-inf')
        for move in empty_positions:
            board[move] = PLAYER_O
            score = minimax(board, PLAYER_X, alpha, beta)[0]
            board[move] = EMPTY
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return (best_score, best_move)
    else:
        best_score = float('inf')
        for move in empty_positions:
            board[move] = PLAYER_X
            score = minimax(board, PLAYER_O, alpha, beta)[0]
            board[move] = EMPTY
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return (best_score, best_move)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start Game", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome! Press "Start Game" to begin.', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'start':
        context.user_data['board'] = create_board()
        context.user_data['difficulty'] = 'easy'
        context.user_data['player'] = PLAYER_X
        context.user_data['game_active'] = True
        
        await query.edit_message_text(text="Game started! Your move:", reply_markup=build_board_keyboard(context.user_data['board']))

    elif query.data.startswith('move_'):
        if not context.user_data.get('game_active', False):
            await query.edit_message_text(text="Start a game first by pressing 'Start Game'.")
            return

        move = int(query.data.split('_')[1])
        board = context.user_data['board']

        if board[move] != EMPTY:
            await query.edit_message_text(text="Invalid move. Try again.")
            return

        board[move] = context.user_data['player']
        if check_win(board, context.user_data['player']):
            await query.edit_message_text(text=f"{display_board(board)}\nCongratulations, you won!")
            context.user_data['game_active'] = False
            return
        elif check_draw(board):
            await query.edit_message_text(text=f"{display_board(board)}\nIt's a draw!")
            context.user_data['game_active'] = False
            return

        ai_move = make_ai_move(board, context.user_data['difficulty'])
        if check_win(board, PLAYER_O):
            await query.edit_message_text(text=f"{display_board(board)}\nAI wins! Better luck next time.")
            context.user_data['game_active'] = False
            return
        elif check_draw(board):
            await query.edit_message_text(text=f"{display_board(board)}\nIt's a draw!")
            context.user_data['game_active'] = False
            return

        await query.edit_message_text(text=f"{display_board(board)}\nYour move:", reply_markup=build_board_keyboard(board))

def build_board_keyboard(board):
    keyboard = [[InlineKeyboardButton(f"{'❌' if cell == PLAYER_X else '⭕️' if cell == PLAYER_O else '⬜️'}", callback_data=f'move_{i}') for i, cell in enumerate(board[i:i+3])] for i in range(0, BOARD_SIZE, 3)]
    return InlineKeyboardMarkup(keyboard)

def make_ai_move(board, difficulty):
    empty_positions = [i for i, cell in enumerate(board) if cell == EMPTY]

    if difficulty == 'easy':
        # Improved strategy for easy difficulty
        move = block_or_win(board, PLAYER_O)
        if move is None:
            move = random.choice(empty_positions)
        else:
            return move
    elif difficulty == 'medium':
        move = block_or_win(board, PLAYER_O) or random.choice(empty_positions)
    else:  # 'hard' difficulty
        _, move = minimax(board, PLAYER_O, float('-inf'), float('inf'))

    board[move] = PLAYER_O
    return move

def main():
    application = Application.builder().token('7456873724:AAGUMY7sQm3fPaPH0hJ50PPtfSSHge83O4s').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
