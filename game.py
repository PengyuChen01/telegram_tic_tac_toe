"""Tic-Tac-Toe game logic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class Cell(Enum):
    EMPTY = 0
    X = 1
    O = 2


# Display symbols
SYMBOLS = {
    Cell.EMPTY: "·",
    Cell.X: "❌",
    Cell.O: "⭕",
}

# All winning lines: rows, columns, diagonals (indices into the 3x3 board)
WIN_LINES = [
    # Rows
    [(0, 0), (0, 1), (0, 2)],
    [(1, 0), (1, 1), (1, 2)],
    [(2, 0), (2, 1), (2, 2)],
    # Columns
    [(0, 0), (1, 0), (2, 0)],
    [(0, 1), (1, 1), (2, 1)],
    [(0, 2), (1, 2), (2, 2)],
    # Diagonals
    [(0, 0), (1, 1), (2, 2)],
    [(0, 2), (1, 1), (2, 0)],
]


@dataclass
class Player:
    user_id: int
    username: str  # display name (first_name or @username)
    symbol: Cell  # Cell.X or Cell.O


@dataclass
class TicTacToe:
    """A single tic-tac-toe game instance."""

    board: list = field(default_factory=lambda: [[Cell.EMPTY] * 3 for _ in range(3)])
    player_x: Optional[Player] = None
    player_o: Optional[Player] = None
    current_turn: Cell = Cell.X  # X always goes first
    is_vs_bot: bool = False  # True when playing against the bot in private chat
    game_over: bool = False
    winner: Optional[Cell] = None  # None = draw or ongoing, Cell.X/O = winner

    def make_move(self, row: int, col: int, player_cell: Cell) -> bool:
        """Place a mark on the board. Returns True if the move was valid."""
        if self.game_over:
            return False
        if self.board[row][col] != Cell.EMPTY:
            return False
        if player_cell != self.current_turn:
            return False

        self.board[row][col] = player_cell
        # Check for win or draw
        if self._check_winner(player_cell):
            self.game_over = True
            self.winner = player_cell
        elif self._check_draw():
            self.game_over = True
            self.winner = None
        else:
            # Switch turn
            self.current_turn = Cell.O if self.current_turn == Cell.X else Cell.X

        return True

    def _check_winner(self, cell: Cell) -> bool:
        """Check if the given cell type has three in a row."""
        for line in WIN_LINES:
            if all(self.board[r][c] == cell for r, c in line):
                return True
        return False

    def _check_draw(self) -> bool:
        """Check if all cells are filled (no winner)."""
        return all(self.board[r][c] != Cell.EMPTY for r in range(3) for c in range(3))

    def get_current_player(self) -> Optional[Player]:
        """Return the Player whose turn it is."""
        if self.current_turn == Cell.X:
            return self.player_x
        return self.player_o

    def get_winner_player(self) -> Optional[Player]:
        """Return the winning Player, or None if draw/ongoing."""
        if self.winner == Cell.X:
            return self.player_x
        elif self.winner == Cell.O:
            return self.player_o
        return None

    def get_cell_display(self, row: int, col: int) -> str:
        """Return the display string for a cell."""
        return SYMBOLS[self.board[row][col]]

    # ─── Simple AI for private-chat mode ───

    def bot_move(self) -> Optional[Tuple[int, int]]:
        """Compute a move for the bot (playing as O). Returns (row, col) or None."""
        if self.game_over or self.current_turn != Cell.O:
            return None

        # 1. Try to win
        move = self._find_winning_move(Cell.O)
        if move:
            return move

        # 2. Block opponent from winning
        move = self._find_winning_move(Cell.X)
        if move:
            return move

        # 3. Take center
        if self.board[1][1] == Cell.EMPTY:
            return (1, 1)

        # 4. Take a corner
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        random.shuffle(corners)
        for r, c in corners:
            if self.board[r][c] == Cell.EMPTY:
                return (r, c)

        # 5. Take any edge
        edges = [(0, 1), (1, 0), (1, 2), (2, 1)]
        random.shuffle(edges)
        for r, c in edges:
            if self.board[r][c] == Cell.EMPTY:
                return (r, c)

        return None

    def _find_winning_move(self, cell: Cell) -> Optional[Tuple[int, int]]:
        """Find a move that completes a line of three for the given cell type."""
        for line in WIN_LINES:
            cells_in_line = [self.board[r][c] for r, c in line]
            if cells_in_line.count(cell) == 2 and cells_in_line.count(Cell.EMPTY) == 1:
                idx = cells_in_line.index(Cell.EMPTY)
                return line[idx]
        return None
