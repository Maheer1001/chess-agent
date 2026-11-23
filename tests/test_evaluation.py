"""agent.py's own board logic: material, positional evaluation, check
detection, hashing and make/unmake. Checked against fragments' rules
engine on hand-built and seeded random positions."""

import pytest
from chessmaker.chess.base import Position

from fragments import BLACK, WHITE, copy_piece_move, list_legal_moves_for, new_board
from fragments.board_utils import board_rows
from play import load_agent_module


@pytest.fixture(scope="module")
def agent():
    return load_agent_module()


def test_piece_values(agent):
    values = {name: agent.material_assignment(name)
              for name in ("pawn", "knight", "bishop", "queen", "right", "king", None)}
    assert values == {"pawn": 1, "knight": 3, "bishop": 3, "queen": 9,
                      "right": 9, "king": 0, None: 0}


@pytest.mark.parametrize("layout", ["sample0", "sample1"])
def test_start_positions_are_balanced(agent, layout):
    board = new_board(layout)
    for player in (WHITE, BLACK):
        assert agent.evaluate_material(board, player) == 0
        assert agent.evaluate_position(board, player) == pytest.approx(0)


def test_material_counts_from_both_sides(agent):
    board = new_board(["k....", "p....", ".....", ".....", "Q.R.K"])
    assert agent.evaluate_material(board, WHITE) == 18 - 1
    assert agent.evaluate_material(board, BLACK) == -(18 - 1)


def test_evaluation_is_zero_sum(agent, helpers):
    for board in helpers.random_positions(15, seed=11):
        assert agent.evaluate_material(board, WHITE) == -agent.evaluate_material(board, BLACK)
        assert agent.evaluate_position(board, WHITE) == pytest.approx(
            -agent.evaluate_position(board, BLACK))


def test_pawn_advance_scores_higher(agent):
    back = new_board(["k....", ".....", ".....", "P....", "....K"])
    forward = new_board(["k....", "P....", ".....", ".....", "....K"])
    assert agent.evaluate_position(forward, WHITE) > agent.evaluate_position(back, WHITE)


def test_incremental_material_matches_full_recount(agent, helpers):
    """calculate_material_change must agree with recounting after the move."""
    checked = 0
    for start in ("sample0", "sample1"):
        for board in helpers.random_positions(6, seed=5, max_plies=40, start=start):
            player = board.current_player
            before = agent.evaluate_material(board, player)
            for piece, move in list_legal_moves_for(board, player):
                delta = agent.calculate_material_change(board, piece, move, player)
                after_board = board.clone()
                _, p2, m2 = copy_piece_move(after_board, piece, move)
                p2.move(m2)
                assert agent.evaluate_material(after_board, player) - before == delta
                checked += 1
    assert checked > 100


def test_promotion_is_worth_eight(agent):
    board = new_board(["k....", "...P.", ".....", ".....", "....K"])
    pawn = board[Position(3, 1)].piece
    promo = [m for m in pawn.get_move_options() if (m.extra or {}).get("promote")]
    assert promo, "pawn on the 7th row should be able to promote"
    assert agent.calculate_material_change(board, pawn, promo[0], WHITE) == 8
    assert agent.calculate_material_change(board, pawn, promo[0], BLACK) == -8


@pytest.mark.parametrize("rows, white_in_check, black_in_check", [
    (["k....", ".....", ".....", ".....", "R...K"], False, True),   # Right along the file
    (["k....", "..R..", ".....", ".....", "....K"], False, True),   # Right knight jump
    (["k....", "P....", ".....", ".....", "R...K"], False, False),  # blocked file
    (["....k", ".....", ".....", ".....", "Q...K"], False, True),   # queen diagonal
    (["....k", ".....", "..b..", ".....", "....K"], True, False),   # bishop diagonal
    (["....k", ".....", ".....", "...p.", "....K"], True, False),   # pawn attacks diagonally
    (["....k", ".....", ".....", "....p", "....K"], False, False),  # pawn does not attack forward
    (["....k", ".....", ".....", "..n..", "....K"], True, False),   # knight
])
def test_in_check_geometry(agent, rows, white_in_check, black_in_check):
    board = new_board(rows)
    assert agent.in_check(board, WHITE) is white_in_check
    assert agent.in_check(board, BLACK) is black_in_check


def test_in_check_agrees_with_rules_engine(agent, helpers):
    """The agent's fast check test must match ChessMaker's attack detection."""
    from chessmaker.chess.pieces import King

    for start in ("sample0", "sample1"):
        for board in helpers.random_positions(10, seed=7, max_plies=40, start=start):
            for player in board.players:
                kings = [p for p in board.get_player_pieces(player) if isinstance(p, King)]
                expected = bool(kings) and kings[0].is_attacked()
                assert agent.in_check(board, player) == expected, board_rows(board)


def test_hash_depends_on_position_and_side_to_move(agent):
    a = new_board("sample0")
    b = new_board("sample0")
    assert agent.hash_position(a, WHITE, WHITE) == agent.hash_position(b, WHITE, WHITE)
    assert agent.hash_position(a, WHITE, WHITE) != agent.hash_position(a, WHITE, BLACK)
    assert agent.hash_position(a, WHITE, WHITE) != agent.hash_position(
        new_board("sample1"), WHITE, WHITE)


def test_make_unmake_restores_the_board(agent, helpers):
    restored = 0
    for board in helpers.random_positions(12, seed=3, max_plies=30):
        player = board.current_player
        rows = board_rows(board)
        legal = helpers.legal_keys(board, player)
        for piece, move in list_legal_moves_for(board, player):
            extra = move.extra or {}
            if extra.get("promote") or extra.get("en_passant"):
                continue  # the agent clones the board for these
            state = agent.make_move(board, piece, move)
            assert board_rows(board) != rows
            agent.unmake_move(board, state)
            assert board_rows(board) == rows
            restored += 1
        assert helpers.legal_keys(board, player) == legal
    assert restored > 50


def test_move_ordering_puts_big_captures_first(agent):
    # The queen can take the black queen or push to an empty square.
    board = new_board(["k...q", ".....", ".....", ".....", "Q...K"])
    moves = agent.order_moves(WHITE, board, list_legal_moves_for(board, WHITE), ply=20)
    piece, move = moves[0]
    assert (move.position.x, move.position.y) == (4, 0)
