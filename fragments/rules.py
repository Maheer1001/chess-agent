"""Game-over detection for Chess Fragments.

Checked after every move, from the point of view of the side to move:

1. the same position (pieces + side to move) has now occurred for the
   fifth time -> draw;
2. a player has no king -> that player loses;
3. the side to move has no legal move and is in check -> checkmate, it loses;
4. the side to move has no legal move but is not in check -> it also
   loses (stalemate is a loss in this variant, not a draw);
5. only the two kings are left -> draw.
"""

from chessmaker.chess.pieces import King

REPETITION_LIMIT = 5


def position_key(board):
    """Hashable identity of a position: every piece plus the side to move."""
    pieces = sorted(
        (piece.name.lower(), piece.player.name, piece.position.x, piece.position.y)
        for piece in board.get_pieces()
    )
    return tuple(pieces), board.current_player.name


def _has_any_move(board, player):
    return any(piece.get_move_options()
               for piece in list(board.get_player_pieces(player)))


def static_result(board):
    """Result of the current position ignoring repetition, or ``None``."""
    for player in board.players:
        if not any(isinstance(p, King) for p in board.get_player_pieces(player)):
            return f"No kings left - {player.name} loses"

    mover = board.current_player
    if not _has_any_move(board, mover):
        kings = [p for p in board.get_player_pieces(mover) if isinstance(p, King)]
        if all(king.is_attacked() for king in kings):
            return f"Checkmate - {mover.name} loses"
        return f"Stalemate (no legal moves) - {mover.name} loses"

    pieces = list(board.get_pieces())
    if len(pieces) == 2 and all(isinstance(p, King) for p in pieces):
        return "Draw - only 2 kings left"
    return None


class ResultTracker:
    """Stateful result checker for one game; call it once after every move."""

    def __init__(self, repetition_limit=REPETITION_LIMIT):
        self.repetition_limit = repetition_limit
        self.seen = {}

    def __call__(self, board):
        key = position_key(board)
        self.seen[key] = self.seen.get(key, 0) + 1
        if self.seen[key] >= self.repetition_limit:
            return "Draw - fivefold repetition"
        return static_result(board)


def winner_of(result):
    """``'white'``, ``'black'`` or ``None`` (draw / no result) for a result string."""
    if result is None:
        return None
    if result.endswith("white loses"):
        return "black"
    if result.endswith("black loses"):
        return "white"
    return None
