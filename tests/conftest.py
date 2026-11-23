"""Shared pytest setup.

agent.py prefers the official coursework helpers (``extension.board_utils``)
when they are importable and falls back to this repo's ``fragments`` engine.
The framework is not part of this repo, so the tests hide it even if a copy
happens to sit in the working tree: every test exercises the same code a
fresh clone runs.
"""

import random
import sys

import pytest

# A None entry in sys.modules makes ``import extension`` raise ImportError.
sys.modules["extension"] = None
sys.modules["extension.board_utils"] = None


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "setup: end-to-end checks that a fresh clone is wired together "
        "(run alone with `python -m pytest -m setup`)",
    )


def legal_keys(board, player=None):
    """Every legal move as a hashable ``(piece, from, to, promote)`` tuple."""
    from fragments import list_legal_moves_for

    player = player or board.current_player
    return {move_key(p, m) for p, m in list_legal_moves_for(board, player)}


def move_key(piece, move):
    extra = getattr(move, "extra", None) or {}
    return (piece.name, (piece.position.x, piece.position.y),
            (move.position.x, move.position.y), extra.get("promote"))


def random_positions(count, seed, max_plies=24, start="sample0"):
    """Positions reached by seeded random playouts, game-over positions skipped."""
    from fragments import ResultTracker, list_legal_moves_for, new_board

    rng = random.Random(seed)
    positions = []
    while len(positions) < count:
        board = new_board(start)
        tracker = ResultTracker()
        for _ in range(rng.randint(0, max_plies)):
            moves = list_legal_moves_for(board, board.current_player)
            piece, move = rng.choice(moves)
            piece.move(move)
            if tracker(board):
                break
        else:
            positions.append(board)
    return positions


@pytest.fixture
def helpers():
    """The helper functions above, for tests that want them."""
    class H:
        pass

    H.legal_keys = staticmethod(legal_keys)
    H.move_key = staticmethod(move_key)
    H.random_positions = staticmethod(random_positions)
    return H
