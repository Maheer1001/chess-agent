"""Differential test: this repo's rules engine vs the official COMP2321 framework.

Needs the official framework files (``extension/``, ``samples.py``) next to
``agent.py``; they are not part of this repo. Nothing from them is copied
here - they are only imported and called.

For many random playouts from each starting position it plays the same
moves on two boards (one built by the official ``samples`` module, one by
``fragments.new_board``) and checks after every move that

* the legal moves (piece, from, to, captures, promotion/en passant) are the
  same list in the same order,
* the game result reported by the official ``get_result`` matches ours,
* the helper functions return equivalent answers.

Usage:  python tools/difftest.py [--playouts 300] [--seed 1] [--max-plies 150]
"""

import argparse
import os
import random
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import samples as official_samples
    from extension import board_rules as official_rules
    from extension import board_utils as official_utils
except ImportError:
    sys.exit("difftest needs the official coursework framework next to agent.py")

from chessmaker.chess.base import Board  # noqa: E402
from itertools import cycle  # noqa: E402

import fragments  # noqa: E402
from fragments import board_utils as ours_utils  # noqa: E402
from fragments.rules import ResultTracker, winner_of  # noqa: E402


def official_board(sample_name):
    """A fresh official board for ``sample0``/``sample1``.

    The official sample lists hold Square objects, which a Board takes
    ownership of, so build once and hand out clones.
    """
    if sample_name not in official_board.cache:
        players = [official_samples.white, official_samples.black]
        squares = getattr(official_samples, sample_name)
        official_board.cache[sample_name] = Board(
            squares=squares, players=players, turn_iterator=cycle(players))
    return official_board.cache[sample_name].clone()


official_board.cache = {}


def move_key(piece, move):
    return (
        piece.name.lower(),
        piece.player.name,
        (piece.position.x, piece.position.y),
        (move.position.x, move.position.y),
        tuple(sorted((c.x, c.y) for c in move.captures)),
        tuple(sorted((k, str(v)) for k, v in (move.extra or {}).items())),
    )


def legal_keys(utils, board):
    return [move_key(p, m) for p, m in utils.list_legal_moves_for(board, board.current_player)]


def outcome(result):
    """Collapse a result string to (kind, winner) so wording can differ."""
    if result is None:
        return None
    text = result.lower()
    for kind in ("repetition", "no kings", "checkmate", "stalemate", "only 2 kings"):
        if kind in text:
            return kind, winner_of(result)
    return "other:" + result, winner_of(result)


def rows(board):
    return ours_utils.board_rows(board)


def choose(rng, keys, style, history):
    """Pick a move index.

    'capture' playouts prefer captures to reach endgames quickly;
    'shuffle' playouts often undo the side's previous move, which
    produces repeated positions.
    """
    if style == "capture":
        captures = [i for i, k in enumerate(keys) if k[4]]
        if captures and rng.random() < 0.8:
            return rng.choice(captures)
    if style == "shuffle" and len(history) >= 2 and rng.random() < 0.9:
        prev = history[-2]  # this side's last move
        for i, k in enumerate(keys):
            if k[0] == prev[0] and k[2] == prev[3] and k[3] == prev[2] and not k[4]:
                return i
    return rng.randrange(len(keys))


def run(playouts, seed, max_plies):
    rng = random.Random(seed)
    stats = Counter()
    results = Counter()
    failures = []

    for n in range(playouts):
        sample = ("sample0", "sample1")[n % 2]
        style = ("uniform", "capture", "shuffle")[n % 3]
        off = official_board(sample)
        ours = fragments.new_board(sample)
        tracker = ResultTracker()
        history = []
        stats["playouts"] += 1

        if rows(off) != rows(ours):
            failures.append((n, 0, "start position differs"))
            continue

        for ply in range(max_plies):
            off_keys = legal_keys(official_utils, off)
            our_keys = legal_keys(ours_utils, ours)
            stats["positions"] += 1
            stats["moves_compared"] += len(off_keys)
            if off_keys != our_keys:
                if sorted(off_keys) == sorted(our_keys):
                    stats["order_only_mismatch"] += 1
                else:
                    failures.append((n, ply, "legal moves differ", rows(off),
                                     set(off_keys) ^ set(our_keys)))
                    break
            if not off_keys:
                break

            i = choose(rng, off_keys, style, history)
            history.append(off_keys[i])
            off_piece, off_move = official_utils.list_legal_moves_for(off, off.current_player)[i]
            our_piece, our_move = ours_utils.list_legal_moves_for(ours, ours.current_player)[i]

            # Helpers: translating a move onto a clone must give the same move.
            clone = ours.clone()
            _, cp, cm = ours_utils.copy_piece_move(clone, our_piece, our_move)
            _, op, om = official_utils.copy_piece_move(clone, our_piece, our_move)
            if cp is None or move_key(cp, cm) != move_key(op, om):
                failures.append((n, ply, "copy_piece_move differs", rows(ours)))
                break
            stats["copy_checks"] += 1

            off_piece.move(off_move)
            our_piece.move(our_move)
            if rows(off) != rows(ours) or off.current_player.name != ours.current_player.name:
                failures.append((n, ply, "boards diverged after move", rows(off), rows(ours)))
                break

            off_res = official_rules.get_result(off)
            our_res = tracker(ours)
            stats["results_compared"] += 1
            if outcome(off_res) != outcome(our_res):
                failures.append((n, ply, "result differs", rows(off), off_res, our_res))
                break
            if off_res:
                results[outcome(off_res)] += 1
                break
        else:
            results[("ply cap", None)] += 1

        if (n + 1) % 50 == 0:
            print(f"  {n + 1}/{playouts} playouts, {stats['positions']} positions, "
                  f"{len(failures)} failures", flush=True)

    return stats, results, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playouts", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-plies", type=int, default=150)
    args = ap.parse_args()

    stats, results, failures = run(args.playouts, args.seed, args.max_plies)
    print()
    for k, v in stats.items():
        print(f"{k:>22}: {v}")
    print("terminal results seen:")
    for k, v in sorted(results.items(), key=lambda kv: -kv[1]):
        print(f"    {k}: {v}")
    print(f"failures: {len(failures)}")
    for f in failures[:10]:
        print("   ", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
