"""Rules engine tests. Expected move lists are worked out by hand."""

import pytest
from chessmaker.chess.pieces import Queen

from fragments import ResultTracker, copy_piece_move, list_legal_moves_for, new_board, static_result
from fragments.board_utils import board_rows


def moves_of(board, player=None):
    """{(piece letter, (from), (to)), ...} for the side to move."""
    player = player or board.current_player
    return {(p.name, (p.position.x, p.position.y), (m.position.x, m.position.y))
            for p, m in list_legal_moves_for(board, player)}


def destinations(board, square):
    x, y = square
    piece = board[board_pos(x, y)].piece
    return {(m.position.x, m.position.y) for m in piece.get_move_options()}


def board_pos(x, y):
    from chessmaker.chess.base import Position
    return Position(x, y)


def play(board, src, dst):
    piece = board[board_pos(*src)].piece
    for option in piece.get_move_options():
        if (option.position.x, option.position.y) == dst:
            piece.move(option)
            return option
    raise AssertionError(f"{src}->{dst} is not legal")


# --- starting positions ---------------------------------------------------

def test_sample0_layout():
    assert board_rows(new_board("sample0")) == ["nqkbr", "ppppp", ".....", "PPPPP", "RBKQN"]


def test_sample0_white_opening_moves():
    pawn_pushes = {("Pawn", (x, 3), (x, 2)) for x in range(5)}  # row 1 is occupied: no double step
    assert moves_of(new_board("sample0")) == pawn_pushes | {
        ("Right", (0, 4), (1, 2)),
        ("Knight", (4, 4), (3, 2)),
    }


def test_sample0_black_opening_moves():
    pawn_pushes = {("Pawn", (x, 1), (x, 2)) for x in range(5)}
    assert moves_of(new_board("sample0", to_move="black")) == pawn_pushes | {
        ("Knight", (0, 0), (1, 2)),
        ("Right", (4, 0), (3, 2)),
    }


def test_sample1_white_opening_moves():
    pawn_pushes = {("Pawn", (x, 3), (x, 2)) for x in range(5)}
    assert moves_of(new_board("sample1")) == pawn_pushes | {
        ("Knight", (1, 4), (0, 2)),
        ("Knight", (1, 4), (2, 2)),
        ("Right", (4, 4), (3, 2)),
    }


def test_players_and_turns():
    board = new_board("sample0")
    assert [p.name for p in board.players] == ["white", "black"]
    assert board.current_player.name == "white"
    play(board, (2, 3), (2, 2))
    assert board.current_player.name == "black"


# --- individual pieces ----------------------------------------------------

def test_right_moves_like_rook_plus_knight():
    board = new_board(["k....", ".....", "..R..", ".....", "....K"])
    knight_jumps = {(3, 4), (4, 3), (4, 1), (3, 0), (1, 0), (0, 1), (0, 3), (1, 4)}
    slides = {(0, 2), (1, 2), (3, 2), (4, 2), (2, 0), (2, 1), (2, 3), (2, 4)}
    assert destinations(board, (2, 2)) == knight_jumps | slides


def test_right_is_blocked_and_captures():
    board = new_board(["k.p..", ".....", "P.R.p", ".....", "....K"])
    knight_jumps = {(3, 4), (4, 3), (4, 1), (3, 0), (1, 0), (0, 1), (0, 3), (1, 4)}
    slides = {(1, 2), (3, 2), (4, 2), (2, 1), (2, 0), (2, 3), (2, 4)}  # (0,2) is own pawn
    assert destinations(board, (2, 2)) == knight_jumps | slides
    captures = {(m.position.x, m.position.y) for m in board[board_pos(2, 2)].piece.get_move_options()
                if m.captures}
    assert captures == {(4, 2), (2, 0)}


def test_knight():
    board = new_board(["k....", ".....", "..N..", ".....", "....K"])
    assert destinations(board, (2, 2)) == {(3, 4), (4, 3), (4, 1), (3, 0), (1, 0), (0, 1), (0, 3), (1, 4)}


def test_bishop():
    board = new_board([".k...", ".....", "..B..", ".....", "....K"])
    assert destinations(board, (2, 2)) == {(3, 3), (1, 1), (0, 0), (3, 1), (4, 0), (1, 3), (0, 4)}


def test_queen():
    board = new_board([".k...", ".....", "..Q..", ".....", "....K"])
    diagonals = {(3, 3), (1, 1), (0, 0), (3, 1), (4, 0), (1, 3), (0, 4)}
    straight = {(0, 2), (1, 2), (3, 2), (4, 2), (2, 0), (2, 1), (2, 3), (2, 4)}
    assert destinations(board, (2, 2)) == diagonals | straight


def test_king_cannot_step_next_to_enemy_king():
    board = new_board(["k....", ".....", "..K..", ".....", "....."])
    around = {(x, y) for x in (1, 2, 3) for y in (1, 2, 3)} - {(2, 2)}
    assert destinations(board, (2, 2)) == around - {(1, 1)}


def test_pinned_piece_cannot_move():
    # The bishop shields its king from the black Right on column 2.
    board = new_board(["k.r..", ".....", ".....", "..B..", "..K.."])
    assert destinations(board, (2, 3)) == set()


def test_king_must_escape_check():
    # Black Right on (2,0) checks the king on (2,4) down the empty column.
    board = new_board(["k.r..", ".....", ".....", "P....", "..K.."])
    legal = moves_of(board)
    assert {piece for piece, _, _ in legal} == {"King"}
    assert all(dst[0] != 2 for _, _, dst in legal)


# --- pawns ----------------------------------------------------------------

def test_pawn_double_step_from_home_row():
    board = new_board(["k....", ".....", ".....", "..P..", "....K"])
    assert destinations(board, (2, 3)) == {(2, 2), (2, 1)}


def test_pawn_off_home_row_single_step():
    board = new_board(["k....", ".....", "..P..", ".....", "....K"])
    assert destinations(board, (2, 2)) == {(2, 1)}


def test_pawn_blocked_and_diagonal_captures():
    board = new_board(["k....", "..n..", ".n.n.", "..P.K", "....."])
    # (2,2) free but (2,1) occupied, so only the single step plus two captures
    assert destinations(board, (2, 3)) == {(2, 2), (1, 2), (3, 2)}


def test_black_pawn_moves_down():
    board = new_board(["k....", "..p..", ".....", ".....", "....K"], to_move="black")
    assert destinations(board, (2, 1)) == {(2, 2), (2, 3)}


@pytest.mark.parametrize("colour, rows, src, dst", [
    ("white", ["k....", "..P..", ".....", ".....", "....K"], (2, 1), (2, 0)),
    ("black", ["k....", ".....", ".....", "..p..", "....K"], (2, 3), (2, 4)),
])
def test_promotion_is_queen_only(colour, rows, src, dst):
    board = new_board(rows, to_move=colour)
    pawn = board[board_pos(*src)].piece
    options = [m for m in pawn.get_move_options() if (m.position.x, m.position.y) == dst]
    assert len(options) == 1
    assert options[0].extra == {"promote": "Queen"}
    pawn.move(options[0])
    promoted = board[board_pos(*dst)].piece
    assert isinstance(promoted, Queen) and promoted.player.name == colour


def test_en_passant():
    board = new_board(["....k", "p....", ".....", ".P...", "....K"])
    play(board, (1, 3), (1, 1))  # white double step past the black pawn
    ep = [m for m in board[board_pos(0, 1)].piece.get_move_options() if m.extra.get("en_passant")]
    assert len(ep) == 1
    assert (ep[0].position.x, ep[0].position.y) == (1, 2)
    board[board_pos(0, 1)].piece.move(ep[0])
    assert board_rows(board) == ["....k", ".....", ".p...", ".....", "....K"]


# --- game results ---------------------------------------------------------

def test_no_result_at_start():
    assert static_result(new_board("sample0")) is None
    assert static_result(new_board("sample1")) is None


def test_checkmate():
    board = new_board(["kr...", "pp...", ".....", "...N.", "....K"])
    play(board, (3, 3), (2, 1))  # smothered mate
    assert static_result(board) == "Checkmate - black loses"


def test_stalemate_is_a_loss():
    board = new_board(["k....", ".....", ".Q...", ".....", "....K"], to_move="black")
    assert static_result(board) == "Stalemate (no legal moves) - black loses"


def test_only_two_kings_is_a_draw():
    assert static_result(new_board(["k....", ".....", ".....", ".....", "....K"])) == "Draw - only 2 kings left"


def test_missing_king_loses():
    assert static_result(new_board([".....", ".....", "..q..", ".....", "....K"])) == "No kings left - black loses"


def test_fivefold_repetition():
    board = new_board(["k....", "..p..", ".....", "..P..", "....K"])
    tracker = ResultTracker()
    shuffle = [((4, 4), (4, 3)), ((0, 0), (1, 0)), ((4, 3), (4, 4)), ((1, 0), (0, 0))]
    for ply in range(1, 18):
        src, dst = shuffle[(ply - 1) % 4]
        play(board, src, dst)
        result = tracker(board)
        if ply < 17:
            assert result is None, ply
    # the position after ply 1 recurs after plies 5, 9, 13 and 17
    assert result == "Draw - fivefold repetition"


# --- helpers used by agent.py ---------------------------------------------

def test_copy_piece_move_translates_to_clone():
    board = new_board("sample0")
    piece, move = list_legal_moves_for(board, board.current_player)[0]
    clone = board.clone()
    same_board, cp, cm = copy_piece_move(clone, piece, move)
    assert same_board is clone
    assert cp is not piece and cp.position == piece.position and type(cp) is type(piece)
    assert cm.position == move.position


def test_copy_piece_move_missing():
    board = new_board("sample0")
    assert copy_piece_move(board, None, None) == (board, None, None)
    other = new_board(["k....", "..P..", ".....", ".....", "....K"])
    pawn, promo = list_legal_moves_for(other, other.current_player)[0]
    assert copy_piece_move(board, pawn, promo)[1:] == (None, None)
