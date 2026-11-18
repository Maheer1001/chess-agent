"""Simple baseline opponents.

Every player is a callable ``player_fn(board, player, var) -> (piece, move)``,
the same interface the coursework agent uses (``var`` is ``[ply, seconds]``).
"""

import random

from .board_utils import list_legal_moves_for

VALUES = {"pawn": 1, "knight": 3, "bishop": 3, "right": 9, "queen": 9, "king": 0}


def make_random(seed=None):
    """Plays a uniformly random legal move."""
    rng = random.Random(seed)

    def random_player(board, player, var):
        moves = list_legal_moves_for(board, player)
        return rng.choice(moves) if moves else (None, None)

    return random_player


def material_gain(board, move):
    """Material won by ``move`` for the side making it (captures + promotion)."""
    gain = 0
    for square in move.captures:
        victim = board[square].piece
        if victim is not None:
            gain += VALUES.get(victim.name.lower(), 0)
    promoted = (move.extra or {}).get("promote")
    if promoted:
        gain += VALUES.get(str(promoted).lower(), 0) - VALUES["pawn"]
    return gain


def make_greedy(seed=None):
    """One-ply material search: takes the biggest capture or promotion
    available, choosing randomly among equally good moves."""
    rng = random.Random(seed)

    def greedy_player(board, player, var):
        moves = list_legal_moves_for(board, player)
        if not moves:
            return None, None
        scored = [(material_gain(board, move), piece, move) for piece, move in moves]
        best = max(score for score, _, _ in scored)
        _, piece, move = rng.choice([s for s in scored if s[0] == best])
        return piece, move

    return greedy_player
