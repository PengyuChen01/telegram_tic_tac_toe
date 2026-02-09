"""Telegram Tic-Tac-Toe Bot."""

from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from game import Cell, Player, TicTacToe, SYMBOLS

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Store active games: key = chat_id, value = TicTacToe instance
games: dict[int, TicTacToe] = {}


# ─── Helpers ────────────────────────────────────────────────


def get_display_name(user) -> str:
    """Get a readable display name for a Telegram user."""
    if user.username:
        return f"@{user.username}"
    return user.first_name


def build_board_keyboard(game: TicTacToe, game_over: bool = False) -> InlineKeyboardMarkup:
    """Build a 3x3 InlineKeyboard representing the board."""
    keyboard = []
    for row in range(3):
        row_buttons = []
        for col in range(3):
            cell = game.board[row][col]
            text = SYMBOLS[cell]
            # If game over or cell taken, callback is a no-op
            if game_over or cell != Cell.EMPTY:
                callback_data = f"noop_{row}_{col}"
            else:
                callback_data = f"move_{row}_{col}"
            row_buttons.append(InlineKeyboardButton(text, callback_data=callback_data))
        keyboard.append(row_buttons)
    return InlineKeyboardMarkup(keyboard)


def build_join_keyboard() -> InlineKeyboardMarkup:
    """Build the 'Join as O' button (shown below the board in group chats)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Join as ⭕", callback_data="join_o")]
    ])


def build_board_with_join(game: TicTacToe) -> InlineKeyboardMarkup:
    """Board grid + join button at the bottom (for waiting state in groups)."""
    keyboard = []
    for row in range(3):
        row_buttons = []
        for col in range(3):
            text = SYMBOLS[Cell.EMPTY]
            callback_data = f"wait_{row}_{col}"
            row_buttons.append(InlineKeyboardButton(text, callback_data=callback_data))
        keyboard.append(row_buttons)
    # Add join button as last row
    keyboard.append([InlineKeyboardButton("Join as ⭕", callback_data="join_o")])
    return InlineKeyboardMarkup(keyboard)


def build_play_again_keyboard() -> InlineKeyboardMarkup:
    """Build the 'Play Again' button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Play Again", callback_data="play_again")]
    ])


def build_game_over_keyboard(game: TicTacToe) -> InlineKeyboardMarkup:
    """Board (disabled) + Play Again button."""
    keyboard = []
    for row in range(3):
        row_buttons = []
        for col in range(3):
            text = SYMBOLS[game.board[row][col]]
            row_buttons.append(InlineKeyboardButton(text, callback_data=f"noop_{row}_{col}"))
        keyboard.append(row_buttons)
    keyboard.append([InlineKeyboardButton("Play Again", callback_data="play_again")])
    return InlineKeyboardMarkup(keyboard)


def status_text(game: TicTacToe) -> str:
    """Generate the status text shown above the board."""
    if game.game_over:
        winner = game.get_winner_player()
        if winner:
            symbol = SYMBOLS[winner.symbol]
            return f"🏆 {symbol} {winner.username} wins!"
        else:
            return "🤝 It's a draw!"

    current = game.get_current_player()
    if current:
        symbol = SYMBOLS[current.symbol]
        return f"Tic-Tac-Toe\n\n{symbol} {current.username}'s turn"
    return "Tic-Tac-Toe\n\nWaiting for opponent..."


# ─── Command Handler ────────────────────────────────────────


async def tictactoe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tictactoe command - start a new game."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    is_private = update.effective_chat.type == "private"

    # Create a new game
    game = TicTacToe()
    game.player_x = Player(
        user_id=user.id,
        username=get_display_name(user),
        symbol=Cell.X,
    )

    if is_private:
        # In private chat, bot plays as O
        game.player_o = Player(
            user_id=0,  # bot
            username="Bot 🤖",
            symbol=Cell.O,
        )
        game.is_vs_bot = True
        games[chat_id] = game

        text = status_text(game)
        keyboard = build_board_keyboard(game)
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        # In group chat, wait for another player to join
        games[chat_id] = game
        text = (
            f"Tic-Tac-Toe\n\n"
            f"❌ {game.player_x.username} wants to play!\n"
            f"Tap 'Join as ⭕' to start the game."
        )
        keyboard = build_board_with_join(game)
        await update.message.reply_text(text, reply_markup=keyboard)


# ─── Callback Query Handler ─────────────────────────────────


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all inline keyboard button presses."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    user = query.from_user
    data = query.data

    # ── Play Again ──
    if data == "play_again":
        await query.answer()
        # Start a new game with this user as X
        game = TicTacToe()
        game.player_x = Player(
            user_id=user.id,
            username=get_display_name(user),
            symbol=Cell.X,
        )
        is_private = update.effective_chat.type == "private"

        if is_private:
            game.player_o = Player(
                user_id=0,
                username="Bot 🤖",
                symbol=Cell.O,
            )
            game.is_vs_bot = True
            games[chat_id] = game
            text = status_text(game)
            keyboard = build_board_keyboard(game)
        else:
            games[chat_id] = game
            text = (
                f"Tic-Tac-Toe\n\n"
                f"❌ {game.player_x.username} wants to play!\n"
                f"Tap 'Join as ⭕' to start the game."
            )
            keyboard = build_board_with_join(game)

        await query.edit_message_text(text, reply_markup=keyboard)
        return

    # ── Join as O ──
    if data == "join_o":
        game = games.get(chat_id)
        if not game:
            await query.answer("No active game. Use /tictactoe to start one.", show_alert=True)
            return
        if game.player_o is not None:
            await query.answer("Game already has two players!", show_alert=True)
            return
        if user.id == game.player_x.user_id:
            await query.answer("You can't play against yourself! Ask someone else to join.", show_alert=True)
            return

        # Register player O
        game.player_o = Player(
            user_id=user.id,
            username=get_display_name(user),
            symbol=Cell.O,
        )
        await query.answer(f"You joined as ⭕!")

        text = status_text(game)
        keyboard = build_board_keyboard(game)
        await query.edit_message_text(text, reply_markup=keyboard)
        return

    # ── Waiting cells (before player O joins) ──
    if data.startswith("wait_"):
        await query.answer("Waiting for an opponent to join...", show_alert=True)
        return

    # ── No-op cells (game over or already taken) ──
    if data.startswith("noop_"):
        await query.answer()
        return

    # ── Move ──
    if data.startswith("move_"):
        game = games.get(chat_id)
        if not game:
            await query.answer("No active game. Use /tictactoe to start one.", show_alert=True)
            return

        if game.player_o is None:
            await query.answer("Waiting for an opponent to join...", show_alert=True)
            return

        _, row_str, col_str = data.split("_")
        row, col = int(row_str), int(col_str)

        # Determine which cell this user should place
        if user.id == game.player_x.user_id:
            player_cell = Cell.X
        elif user.id == game.player_o.user_id:
            player_cell = Cell.O
        else:
            await query.answer("You're not in this game!", show_alert=True)
            return

        # Validate it's this player's turn
        if player_cell != game.current_turn:
            await query.answer("Not your turn!", show_alert=True)
            return

        # Make the move
        if not game.make_move(row, col, player_cell):
            await query.answer("Invalid move!", show_alert=True)
            return

        await query.answer()

        # If game over, show result
        if game.game_over:
            text = status_text(game)
            keyboard = build_game_over_keyboard(game)
            await query.edit_message_text(text, reply_markup=keyboard)
            return

        # Bot's turn (private chat)
        if game.is_vs_bot and game.current_turn == Cell.O:
            bot_pos = game.bot_move()
            if bot_pos:
                game.make_move(bot_pos[0], bot_pos[1], Cell.O)

            if game.game_over:
                text = status_text(game)
                keyboard = build_game_over_keyboard(game)
                await query.edit_message_text(text, reply_markup=keyboard)
                return

        # Update board
        text = status_text(game)
        keyboard = build_board_keyboard(game)
        await query.edit_message_text(text, reply_markup=keyboard)


# ─── Main ───────────────────────────────────────────────────


def main() -> None:
    """Start the bot."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not found! Set it in .env file.")
        return

    app = Application.builder().token(token).build()

    # Register handlers
    app.add_handler(CommandHandler("tictactoe", tictactoe_command))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
