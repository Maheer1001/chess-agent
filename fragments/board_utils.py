"""Helpers with the same call signatures the coursework agent expects."""

SYMBOLS = {"king": "K", "queen": "Q", "bishop": "B", "knight": "N",
           "right": "R", "pawn": "P"}


def list_legal_moves_for(board, player):
    """Every legal move for ``player`` as a list of ``(piece, move_option)``.

    Moves that would leave the player's own king attacked are already
    removed by ChessMaker's King, so everything returned is playable.
    """
    return [(piece, option)
            for piece in list(board.get_player_pieces(player))
            for option in piece.get_move_options()]


def copy_piece_move(board, piece, move):
    """Translate a ``(piece, move)`` chosen on one board onto ``board``.

    Agents usually search on a clone, so the objects they return belong to
    a different board. This finds the piece of the same type and owner on
    the same square of ``board`` and its move option with the same
    destination (and the same promotion, if any).

    Returns ``(board, piece_on_board, move_on_board)``; either of the last
    two is ``None`` when no match exists.
    """
    if piece is None or move is None:
        return board, None, None
    try:
        origin = piece.position
        target = move.position
        wanted_extra = getattr(move, "extra", None) or {}
    except Exception:
        return board, None, None

    match = None
    for candidate in board.get_player_pieces(piece.player):
        if type(candidate) is type(piece) and candidate.position == origin:
            match = candidate
            break
    if match is None:
        return board, None, None

    fallback = None
    for option in match.get_move_options():
        if option.position != target:
            continue
        if (option.extra or {}) == wanted_extra:
            return board, match, option
        if fallback is None:
            fallback = option
    return board, match, fallback


def piece_symbol(piece):
    letter = SYMBOLS.get(piece.name.lower(), "?")
    return letter if piece.player.name == "white" else letter.lower()


def board_rows(board):
    """The board as five strings in layout notation (see ``setup``)."""
    width, height = board.size
    grid = [["."] * width for _ in range(height)]
    for piece in board.get_pieces():
        pos = piece.position
        grid[pos.y][pos.x] = piece_symbol(piece)
    return ["".join(row) for row in grid]


def board_to_text(board):
    """ASCII diagram with x coordinates across the top, y down the side."""
    rows = board_rows(board)
    width = len(rows[0])
    border = "   +" + "-" * (2 * width + 1) + "+"
    lines = ["     " + " ".join(str(x) for x in range(width)), border]
    for y, row in enumerate(rows):
        lines.append(f" {y} | " + " ".join(row) + " |")
    lines.append(border)
    return "\n".join(lines)


def describe_move(piece, move):
    """Short readable form, e.g. ``Q 3,4 -> 1,2 x`` or ``P 0,1 -> 0,0 =Q``."""
    src, dst = piece.position, move.position
    text = f"{piece_symbol(piece)} {src.x},{src.y} -> {dst.x},{dst.y}"
    if move.captures:
        text += " x"
    extra = move.extra or {}
    if "promote" in extra:
        text += " =" + SYMBOLS.get(str(extra["promote"]).lower(), "?")
    if extra.get("en_passant"):
        text += " e.p."
    return text
