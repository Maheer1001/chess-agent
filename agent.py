import time
try:  # inside the official COMP2321 framework
    from extension.board_utils import list_legal_moves_for, copy_piece_move
except ImportError:  # standalone: this repo's reimplementation of the rules
    from fragments.board_utils import list_legal_moves_for, copy_piece_move

infinity = float("inf")
_material_cache = {}
transposition_table = {}
pv_table = {}  # Principal variation table for move ordering
start_time = 0
time_limit = 0

DEBUG = False  # set True to print search progress

# Read-only stats from the most recent agent() call, used by play.py.
search_stats = {"depth": 0, "score": 0.0, "nodes": 0}


def log(message):
    if DEBUG:
        print(message)


# region Utilities
def check_square(board, x, y):
    """
    Returns the piece name at board position (x,y) or None if empty.
    """
    square = board._squares[y][x]
    if square and square.piece:
        return square.piece.name.lower()
    return None


def material_assignment(piece):
    """
    Returns material value for piece type. Cached for performance.
    """
    if piece in _material_cache:
        return _material_cache[piece]

    piece_value = {
        "pawn": 1,
        "knight": 3,
        "bishop": 3,
        "right": 9,
        "queen": 9,
        "king": 0,
        None: 0
    }
    result = piece_value.get(piece, 0)
    _material_cache[piece] = result
    return result


def hash_position(board, player):
    """
    Creates hash key for board position. Used for transposition table lookups.
    """
    pieces = []
    for y in range(5):
        for x in range(5):
            square = board._squares[y][x]
            if square and square.piece:
                piece = square.piece
                pieces.append((x, y, piece.name.lower(), piece.player.name))
    return hash((tuple(pieces), player.name))


def time_check():
    """
    Returns True if time remaining is less than 10% of time limit.
    """
    elapsed = time.time() - start_time
    return elapsed > time_limit * 0.9


# endregion

# region Material Evaluation
def evaluate_material(board, player):
    """
    Calculates total material advantage for player. Positive means player is ahead.
    """
    player_material_score = 0
    opponent_material_score = 0
    opponent_name = board.players[1] if player.name == "white" else \
        board.players[0]

    for piece in board.get_player_pieces(player):
        player_material_score += material_assignment(piece.name.lower())
    for piece in board.get_player_pieces(opponent_name):
        opponent_material_score += material_assignment(piece.name.lower())

    return player_material_score - opponent_material_score


def calculate_material_change(board, piece, move, player, captured_piece=None):
    """
    Calculates incremental material change from making a move.
    Must be called before making the move on the board.
    """
    material_change = 0

    if captured_piece:
        captured_value = material_assignment(captured_piece.name.lower())
    elif hasattr(move, 'extra') and move.extra and move.extra.get(
            'en_passant'):
        captured_value = material_assignment('pawn')
    else:
        captured_piece_name = check_square(board, move.position.x,
                                           move.position.y)
        captured_value = material_assignment(captured_piece_name)

    if piece.player.name == player.name:
        material_change += captured_value
    else:
        material_change -= captured_value

    if hasattr(move, 'extra') and move.extra and move.extra.get('promote'):
        promoted_to = move.extra['promote'].lower()
        promote_value = material_assignment(promoted_to) - material_assignment(
            'pawn')
        if piece.player.name == player.name:
            material_change += promote_value
        else:
            material_change -= promote_value

    return material_change


# endregion

# region Position Evaluation System
def evaluate_position(board, player):
    """
    Evaluates positional factors and returns score from player's perspective.
    Scaled by 0.1 to keep values small relative to material.
    """
    score = 0
    opponent = board.players[1] if player.name == "white" else board.players[0]
    score = evaluate_piece_positions(board, player, opponent)
    return score * 0.1


def evaluate_piece_positions(board, player, opponent):
    """
    Scores piece positions based on center control, king safety, and pawn advancement.
    """
    score = 0
    for piece in board.get_player_pieces(player):
        x, y = piece.position.x, piece.position.y
        piece_type = piece.name.lower()
        if piece_type in ['knight', 'bishop', 'queen', 'right']:
            distance = abs(x - 2) + abs(y - 2)
            score += (4 - distance) * 0.1
        elif piece_type == 'king':
            edge_distance = min(x, 4 - x, y, 4 - y)
            score += edge_distance * 0.05
        elif piece_type == 'pawn':
            if player.name == "white":
                score += (4 - y) * 0.15
            else:
                score += y * 0.15
    for piece in board.get_player_pieces(opponent):
        x, y = piece.position.x, piece.position.y
        piece_type = piece.name.lower()
        if piece_type in ['knight', 'bishop', 'queen', 'right']:
            distance = abs(x - 2) + abs(y - 2)
            score -= (4 - distance) * 0.1
        elif piece_type == 'king':
            edge_distance = min(x, 4 - x, y, 4 - y)
            score -= edge_distance * 0.05
        elif piece_type == 'pawn':
            if opponent.name == "white":
                score -= (4 - y) * 0.15
            else:
                score -= y * 0.15
    return score


# endregion

# region Move Ordering
def score_move(player, board, piece, move, ply, pv_move=None):
    """
    Assigns score to move for ordering. Higher score means move is searched first.
    Considers MVV-LVA, promotions, early piece development penalties, center control, and PV move.
    """
    if player.name == 'white':
        turn = (ply + 1) / 2
    else:
        turn = ply / 2
    score = 0

    # PV move from previous iteration gets highest priority
    if pv_move and piece.position.x == pv_move[0] and piece.position.y == \
            pv_move[1] \
            and move.position.x == pv_move[2] and move.position.y == pv_move[
        3]:
        score += 10000

    # MVV-LVA: prioritize capturing high-value pieces with low-value attackers
    captured = check_square(board, move.position.x, move.position.y)
    if captured:
        victim_value = material_assignment(captured)
        attacker_value = material_assignment(piece.name.lower())
        score += victim_value * 100 - attacker_value

    # Promotions are high priority
    if hasattr(move, 'extra') and move.extra and move.extra.get('promote'):
        score += 800

    # Penalize moving valuable pieces early
    if turn < 5:
        if piece.name.lower() in ["knight", "right"]:
            score -= 500
        if piece.name.lower() == "king":
            score -= 250
        if piece.name.lower() in ["queen", "bishop"]:
            score -= 50

    # Reward center control
    dest_x, dest_y = move.position.x, move.position.y
    center_distance = abs(dest_x - 2) + abs(dest_y - 2)
    score += (4 - center_distance) * 3

    # Reward pawn advancement
    if piece.name.lower() == "pawn":
        if player.name == "white":
            score += (4 - dest_y) * 10
        else:
            score += dest_y * 10

    return score


def order_moves(player, board, moves, ply, pv_move=None):
    """
    Sorts moves by descending score. PV move searched first if provided.
    """
    moves.sort(
        key=lambda pm: -score_move(player, board, pm[0], pm[1], ply, pv_move))
    return moves


# endregion

# region Board Manipulation
class MoveState:
    """
    Stores information needed to unmake a move.
    """

    def __init__(self, piece, orig_pos, dest_pos, captured_piece):
        self.piece = piece
        self.orig_pos = orig_pos
        self.dest_pos = dest_pos
        self.captured_piece = captured_piece


def make_move(board, piece, move):
    """
    Executes move on board. Returns MoveState for undoing.
    """
    orig_pos = (piece.position.x, piece.position.y)
    dest_pos = (move.position.x, move.position.y)
    original_square = board._squares[orig_pos[1]][orig_pos[0]]
    dest_square = board._squares[dest_pos[1]][dest_pos[0]]
    captured_piece = None
    if dest_square and dest_square.piece:
        captured_piece = dest_square.piece
    state = MoveState(piece, orig_pos, dest_pos, captured_piece)
    original_square.piece = None
    dest_square.piece = piece
    return state


def unmake_move(board, state):
    """
    Reverts move using MoveState. Restores captured piece if any.
    """
    piece = state.piece
    original_square = board._squares[state.orig_pos[1]][state.orig_pos[0]]
    dest_square = board._squares[state.dest_pos[1]][state.dest_pos[0]]
    dest_square.piece = None
    original_square.piece = piece
    if state.captured_piece:
        dest_square.piece = state.captured_piece


# endregion

# region Tree Search
def max_tree_value(board, ply, player, alpha, beta, depth, material_evaluation,
                   is_root):
    """
    Maximizing player search. Uses alpha-beta pruning, null move pruning,
    late move reduction, and transposition tables.
    """
    search_stats["nodes"] += 1
    if time_check():
        return alpha, None, None

    if not is_root:
        position_key = hash_position(board, player)
        if position_key in transposition_table:
            cached_depth, cached_score, cached_type = transposition_table[
                position_key]
            if cached_depth >= depth:
                if cached_type == 'exact':
                    return cached_score, None, None
                elif cached_type == 'lower' and cached_score >= beta:
                    return cached_score, None, None
                elif cached_type == 'upper' and cached_score <= alpha:
                    return cached_score, None, None

    if depth == 0:
        position_score = evaluate_position(board, player)
        return material_evaluation + position_score, None, None

    # Null move pruning: if passing gives beta cutoff, position is too good
    if not is_root and depth >= 3 and material_evaluation > -2 and beta < infinity - 100:
        null_score, _, _ = min_tree_value(board, ply + 1, player, -beta,
                                          -beta + 1,
                                          depth - 3, material_evaluation,
                                          False)
        null_score = -null_score
        if null_score >= beta:
            return beta, None, None

    best_piece, best_move = None, None
    moves = list_legal_moves_for(board, player)

    # Get PV move for this position if it exists
    position_key = hash_position(board, player)
    pv_move = pv_table.get(position_key)
    moves = order_moves(player, board, moves, ply, pv_move)

    original_alpha = alpha

    for i, (piece, move) in enumerate(moves):
        is_special = hasattr(move, "extra") and move.extra
        if is_special:
            material_change = calculate_material_change(board, piece, move,
                                                        player)
            new_material_evaluation = material_evaluation + material_change

            temp_board = board.clone()
            temp_board, temp_piece, temp_move = copy_piece_move(temp_board,
                                                                piece, move)
            if temp_piece and temp_move:
                temp_piece.move(temp_move)
                score, _, _ = min_tree_value(temp_board, ply + 1, player,
                                             alpha, beta, depth - 1,
                                             new_material_evaluation, False)
            else:
                continue
        else:
            state = make_move(board, piece, move)
            if not state:
                continue
            try:
                material_change = calculate_material_change(board, piece, move,
                                                            player,
                                                            state.captured_piece)
                new_material_evaluation = material_evaluation + material_change

                search_depth = depth - 1
                is_capture = state.captured_piece is not None

                # Late move reduction: search later moves at reduced depth
                if i >= 4 and depth >= 3 and not is_capture:
                    search_depth = depth - 2

                score, _, _ = min_tree_value(board, ply + 1, player, alpha,
                                             beta, search_depth,
                                             new_material_evaluation, False)
            finally:
                unmake_move(board, state)

        if score > alpha:
            alpha = score
            if is_root:
                best_piece, best_move = piece, move
                # Store PV move for next iteration
                pv_table[position_key] = (piece.position.x, piece.position.y,
                                          move.position.x, move.position.y)
        if alpha >= beta:
            break

    if not is_root:
        position_key = hash_position(board, player)
        if alpha <= original_alpha:
            cache_type = 'upper'
        elif alpha >= beta:
            cache_type = 'lower'
        else:
            cache_type = 'exact'
        transposition_table[position_key] = (depth, alpha, cache_type)

    return alpha, best_piece, best_move


def min_tree_value(board, ply, player, alpha, beta, depth, material_evaluation,
                   is_root):
    """
    Minimizing player search. Uses alpha-beta pruning, null move pruning,
    late move reduction, and transposition tables.
    """
    search_stats["nodes"] += 1
    if time_check():
        return beta, None, None

    if not is_root:
        position_key = hash_position(board, player)
        if position_key in transposition_table:
            cached_depth, cached_score, cached_type = transposition_table[
                position_key]
            if cached_depth >= depth:
                if cached_type == 'exact':
                    return cached_score, None, None
                elif cached_type == 'lower' and cached_score >= beta:
                    return cached_score, None, None
                elif cached_type == 'upper' and cached_score <= alpha:
                    return cached_score, None, None

    if depth == 0:
        position_score = evaluate_position(board, player)
        return material_evaluation + position_score, None, None

    # Null move pruning: if passing gives alpha cutoff, position is too bad
    if not is_root and depth >= 3 and material_evaluation < 2 and alpha > -infinity + 100:
        null_score, _, _ = max_tree_value(board, ply + 1, player, -beta,
                                          -beta + 1,
                                          depth - 3, material_evaluation,
                                          False)
        null_score = -null_score
        if null_score <= alpha:
            return alpha, None, None

    best_piece, best_move = None, None
    opponent = board.players[1] if player.name == "white" else board.players[0]
    moves = list_legal_moves_for(board, opponent)

    # Get PV move for this position if it exists
    position_key = hash_position(board, player)
    pv_move = pv_table.get(position_key)
    moves = order_moves(opponent, board, moves, ply, pv_move)

    original_beta = beta

    for i, (piece, move) in enumerate(moves):
        is_special = hasattr(move, "extra") and move.extra
        if is_special:
            material_change = calculate_material_change(board, piece, move,
                                                        player)
            new_material_evaluation = material_evaluation + material_change

            temp_board = board.clone()
            temp_board, temp_piece, temp_move = copy_piece_move(temp_board,
                                                                piece, move)
            if temp_piece and temp_move:
                temp_piece.move(temp_move)
                score, _, _ = max_tree_value(temp_board, ply + 1, player,
                                             alpha, beta, depth - 1,
                                             new_material_evaluation, False)
            else:
                continue
        else:
            state = make_move(board, piece, move)
            if not state:
                continue
            try:
                material_change = calculate_material_change(board, piece, move,
                                                            player,
                                                            state.captured_piece)
                new_material_evaluation = material_evaluation + material_change

                search_depth = depth - 1
                is_capture = state.captured_piece is not None

                # Late move reduction: search later moves at reduced depth
                if i >= 4 and depth >= 3 and not is_capture:
                    search_depth = depth - 2

                score, _, _ = max_tree_value(board, ply + 1, player, alpha,
                                             beta, search_depth,
                                             new_material_evaluation, False)
            finally:
                unmake_move(board, state)

        if score < beta:
            beta = score
            if is_root:
                best_piece, best_move = piece, move
                # Store PV move for next iteration
                pv_table[position_key] = (piece.position.x, piece.position.y,
                                          move.position.x, move.position.y)
        if beta <= alpha:
            break

    if not is_root:
        position_key = hash_position(board, player)
        if beta >= original_beta:
            cache_type = 'lower'
        elif beta <= alpha:
            cache_type = 'upper'
        else:
            cache_type = 'exact'
        transposition_table[position_key] = (depth, beta, cache_type)

    return beta, best_piece, best_move


# endregion

# region Agent
def agent(board, player, var):
    """
    Main agent function. Uses iterative deepening with aspiration windows.
    Searches progressively deeper until time limit approached.
    """
    global start_time, time_limit

    ply, thinking_time = var[0], var[1]
    start_time = time.time()
    time_limit = thinking_time
    search_stats.update(depth=0, score=0.0, nodes=0)

    log(f"Ply: {ply}, Time: {thinking_time}s, Turn: {player.name}")

    my_board = board.clone()

    best_piece, best_move = None, None
    best_score = 0
    initial_material = evaluate_material(my_board, player)

    # Iterative deepening: start shallow, increase depth each iteration
    for depth in range(1, 20):
        if time_check():
            break

        alpha, beta = -infinity, infinity

        # Aspiration window: narrow search around previous score after depth 2
        if depth > 2:
            window = 0.5
            alpha = best_score - window
            beta = best_score + window

        score, piece, move = max_tree_value(
            my_board, ply, player, alpha, beta, depth,
            initial_material, is_root=True
        )

        # Re-search with full window if score outside aspiration window
        if (score <= alpha or score >= beta) and not time_check():
            score, piece, move = max_tree_value(
                my_board, ply, player, -infinity, infinity, depth,
                initial_material, is_root=True
            )

        # Update best move if search completed successfully
        if piece and move:
            best_piece, best_move = piece, move
            best_score = score
            search_stats.update(depth=depth, score=score)
            log(f"Depth {depth}: score={score:.3f}, "
                f"nodes_cached={len(transposition_table)}")

        # Stop if checkmate found
        if abs(score) > 1000:
            break

    log(f"Final: material={initial_material}, score={best_score:.3f}")
    return best_piece, best_move
# endregion