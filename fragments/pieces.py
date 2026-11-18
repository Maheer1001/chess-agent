"""Fragment-specific pieces built on ChessMaker.

Chess Fragments uses ChessMaker's King, Queen, Bishop and Knight unchanged.
It adds two things of its own:

* ``Right`` - a piece that combines the rook's sliding moves with the
  knight's jumps (known elsewhere as a chancellor or marshal).
* pawns that may only promote to a queen.
"""

from chessmaker.chess.base.piece import Piece
from chessmaker.chess.piece_utils import (
    filter_uncapturable_positions,
    is_in_board,
    iterate_until_blocked,
    positions_to_move_options,
)
from chessmaker.chess.pieces import Pawn, Queen
from chessmaker.chess.pieces.knight import MOVE_OFFSETS as KNIGHT_JUMPS

ORTHOGONAL_RAYS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Right(Piece):
    """Rook + knight. Jumps like a knight or slides along rows and columns."""

    # A plain class attribute behaves like ChessMaker's ``name`` class
    # property for every caller (``piece.name`` and ``Right.name``).
    name = "Right"

    def _get_move_options(self):
        origin = self.position
        board = self.board

        targets = [origin.offset(dx, dy) for dx, dy in KNIGHT_JUMPS]
        targets = [square for square in targets if is_in_board(board, square)]
        for ray in ORTHOGONAL_RAYS:
            targets.extend(iterate_until_blocked(self, ray))

        targets = filter_uncapturable_positions(self, targets)
        return list(positions_to_move_options(board, targets))

    def clone(self):
        return Right(self.player)


def queen_pawn(player, moved=False):
    """Create a pawn for ``player`` that promotes only to a queen.

    White pawns advance towards row 0, black pawns towards row 4.
    ``moved=True`` gives a pawn that has already moved, so it has no
    two-square advance (used when building arbitrary test positions).
    """
    if player.name == "white":
        direction = Pawn.Direction.UP
    elif player.name == "black":
        direction = Pawn.Direction.DOWN
    else:
        raise ValueError(f"unknown player colour: {player.name!r}")
    # moved_turns_ago=-1 marks a pawn that has never moved. Any larger
    # value disables the double step and is too old for en passant.
    return Pawn(player, direction, promotions=[Queen],
                moved_turns_ago=5 if moved else -1)
