"""Players, starting layouts and board construction.

Layouts are written as five strings, one per row, from row 0 (black's
back rank) down to row 4 (white's back rank). Upper case is white, lower
case is black, ``.`` is an empty square:

    K king   Q queen   B bishop   N knight   R right   P pawn
"""

from itertools import cycle

from chessmaker.chess.base import Board, Player, Square
from chessmaker.chess.pieces import Bishop, King, Knight, Queen

from .pieces import Right, queen_pawn

WHITE = Player("white")
BLACK = Player("black")

SIZE = 5

# The two starting positions used in the COMP2321 coursework.
LAYOUTS = {
    "sample0": (
        "nqkbr",
        "ppppp",
        ".....",
        "PPPPP",
        "RBKQN",
    ),
    "sample1": (
        "rqknb",
        "ppppp",
        ".....",
        "PPPPP",
        "BNKQR",
    ),
}

_PIECE_TYPES = {"k": King, "q": Queen, "b": Bishop, "n": Knight, "r": Right}
_HOME_PAWN_ROW = {"white": 3, "black": 1}


def _make_piece(symbol, row, pawns_moved):
    player = WHITE if symbol.isupper() else BLACK
    kind = symbol.lower()
    if kind == "p":
        moved = pawns_moved or row != _HOME_PAWN_ROW[player.name]
        return queen_pawn(player, moved=moved)
    if kind not in _PIECE_TYPES:
        raise ValueError(f"unknown piece symbol {symbol!r}")
    return _PIECE_TYPES[kind](player)


def new_board(layout="sample0", to_move="white", pawns_moved=False):
    """Build a ChessMaker ``Board`` for a Chess Fragments position.

    ``layout`` is either a key of ``LAYOUTS`` or a sequence of five row
    strings. ``to_move`` picks the side that plays first. Pawns standing
    on their home row get their two-square first move; pawns anywhere
    else are treated as already moved (pass ``pawns_moved=True`` to make
    every pawn count as moved).

    ``board.players`` is always ``[white, black]``.
    """
    rows = LAYOUTS[layout] if isinstance(layout, str) else tuple(layout)
    if len(rows) != SIZE or any(len(r) != SIZE for r in rows):
        raise ValueError("a layout needs 5 rows of 5 characters")

    squares = []
    for y, row in enumerate(rows):
        squares.append([
            Square() if ch == "." else Square(_make_piece(ch, y, pawns_moved))
            for ch in row
        ])

    order = [WHITE, BLACK] if to_move == "white" else [BLACK, WHITE]
    return Board(squares=squares, players=[WHITE, BLACK],
                 turn_iterator=cycle(order))


def opponent_of(board, player):
    """The other player on ``board``."""
    return board.players[1] if board.players[0] == player else board.players[0]
