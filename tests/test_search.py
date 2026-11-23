"""The search: always returns a legal move, finds short forced mates and
behaves the same way on repeated runs."""

import pytest

from fragments import copy_piece_move, list_legal_moves_for, new_board, static_result, winner_of
from fragments.board_utils import board_rows
from play import load_agent_module, play_game


def apply(board, piece, move):
    """Play ``(piece, move)`` (from any board) on a clone of ``board``."""
    after = board.clone()
    _, piece, move = copy_piece_move(after, piece, move)
    assert piece is not None and move is not None, "move is not legal here"
    piece.move(move)
    return after


def wins_in_one(board, winner):
    """True if the side to move has a move that ends the game in ``winner``'s favour."""
    return any(winner_of(static_result(apply(board, p, m))) == winner
               for p, m in list_legal_moves_for(board, board.current_player))


def test_moves_from_random_positions_are_legal(helpers):
    agent = load_agent_module()
    for start in ("sample0", "sample1"):
        for board in helpers.random_positions(6, seed=21, max_plies=30, start=start):
            piece, move = agent.agent(board.clone(), board.current_player, [10, 0.15])
            assert piece is not None and move is not None
            assert helpers.move_key(piece, move) in helpers.legal_keys(board)


def test_zero_time_budget_still_returns_a_legal_move(helpers):
    agent = load_agent_module()
    board = new_board("sample1")
    piece, move = agent.agent(board.clone(), board.current_player, [1, 0.0])
    assert helpers.move_key(piece, move) in helpers.legal_keys(board)


def test_returned_move_does_not_touch_the_callers_board(helpers):
    agent = load_agent_module()
    board = new_board("sample0")
    rows = board_rows(board)
    agent.agent(board, board.current_player, [1, 0.3])
    assert board_rows(board) == rows
    assert board.current_player.name == "white"


@pytest.mark.parametrize("rows, to_move", [
    (["....k", ".....", "..K..", ".....", "R...."], "white"),
    (["r....", ".....", "..k..", ".....", "....K"], "black"),
])
def test_finds_mate_in_two(rows, to_move):
    board = new_board(rows, to_move=to_move)
    assert not wins_in_one(board, to_move), "position should need two moves"
    agent = load_agent_module()
    piece, move = agent.agent(board.clone(), board.current_player, [20, 3.0])
    assert agent.search_stats["score"] > 1000, agent.search_stats  # it saw the mate

    after = apply(board, piece, move)
    assert static_result(after) is None
    replies = list_legal_moves_for(after, after.current_player)
    assert replies
    for reply_piece, reply in replies:  # every defence still loses next move
        assert wins_in_one(apply(after, reply_piece, reply), to_move)


def test_takes_a_hanging_queen():
    board = new_board(["....k", ".....", "..q..", ".....", "Q...K"])
    agent = load_agent_module()
    piece, move = agent.agent(board.clone(), board.current_player, [20, 1.0])
    assert piece.name == "Queen" and (move.position.x, move.position.y) == (2, 2)


def test_mate_choice_is_repeatable():
    board = new_board(["....k", ".....", "..K..", ".....", "R...."])
    choices = set()
    for _ in range(3):
        agent = load_agent_module()
        piece, move = agent.agent(board.clone(), board.current_player, [20, 3.0])
        choices.add(((piece.position.x, piece.position.y), (move.position.x, move.position.y)))
    assert len(choices) == 1


def test_seeded_baseline_games_are_reproducible():
    """Opponents are seeded, so a game between them replays exactly."""
    first = play_game("random", "greedy", start="sample1", max_plies=60, seed=42)
    second = play_game("random", "greedy", start="sample1", max_plies=60, seed=42)
    other = play_game("random", "greedy", start="sample1", max_plies=60, seed=43)
    assert first["frames"] == second["frames"]
    assert first["result"] == second["result"]
    assert other["frames"] != first["frames"]
