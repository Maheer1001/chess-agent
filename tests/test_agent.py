"""The agent should take an immediate win when one exists, and return legal moves."""

import pytest

from fragments import copy_piece_move, new_board, static_result, winner_of
from play import load_agent_module, play_game

THINK = 1.0  # seconds per move; mate-in-1 is found at depth 1


@pytest.mark.parametrize("name, rows, to_move", [
    ("right slides to the back row", ["..k..", ".ppp.", ".....", ".....", "R...K"], "white"),
    ("smothered knight mate", ["kr...", "pp...", ".....", "...N.", "....K"], "white"),
    ("queen supported by king", ["k....", "..K..", "....Q", ".....", "....."], "white"),
    ("pawn promotes with mate", ["...k.", ".P.p.", "...K.", ".....", "....."], "white"),
    ("black right mates", ["k...r", ".....", ".....", "PPP..", ".K..."], "black"),
])
def test_agent_wins_in_one(name, rows, to_move):
    board = new_board(rows, to_move=to_move)
    agent = load_agent_module()
    piece, move = agent.agent(board.clone(), board.current_player, [30, THINK])
    _, piece, move = copy_piece_move(board, piece, move)
    assert piece is not None and move is not None, name
    piece.move(move)
    result = static_result(board)
    assert winner_of(result) == to_move, f"{name}: {result}"


def test_agent_reports_search_stats():
    board = new_board("sample0")
    agent = load_agent_module()
    piece, move = agent.agent(board.clone(), board.current_player, [1, 0.5])
    assert piece is not None and move is not None
    assert agent.search_stats["depth"] >= 1
    assert agent.search_stats["nodes"] > 0


def test_full_game_runs_to_a_result():
    game = play_game("agent", "random", start="sample0", move_time=0.2, max_plies=60, seed=1)
    assert game["result"]
    assert game["plies"] >= 1
