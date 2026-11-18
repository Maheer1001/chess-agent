"""Play Chess Fragments games between the agent and baseline opponents.

Examples
--------
    python play.py --white agent --black random --games 1 --show
    python play.py --white greedy --black agent --games 10 --time 0.5 --seed 3
    python play.py --white agent --black agent --start sample1 --show

Players: ``agent`` (agent.py), ``random`` (uniform random legal move) and
``greedy`` (best immediate material gain, random tie-break).
"""

import argparse
import importlib.util
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict

from fragments import ResultTracker, board_to_text, copy_piece_move, new_board, winner_of
from fragments.board_utils import board_rows, describe_move
from fragments.opponents import make_greedy, make_random

ROOT = os.path.dirname(os.path.abspath(__file__))
PLAYER_TYPES = ("agent", "random", "greedy")


def load_agent_module():
    """Import a private copy of agent.py.

    agent.py keeps its transposition and PV tables in module globals, so
    each side of each game gets a fresh copy: no state leaks between
    games, and agent-vs-agent games don't share tables.
    """
    load_agent_module.count += 1
    name = f"_agent_instance_{load_agent_module.count}"
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "agent.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


load_agent_module.count = 0


class Side:
    """One player in a game: its move function plus optional search stats."""

    def __init__(self, kind, seed):
        self.kind = kind
        self.module = None
        if kind == "agent":
            self.module = load_agent_module()
            self.fn = self.module.agent
        elif kind == "random":
            self.fn = make_random(seed)
        elif kind == "greedy":
            self.fn = make_greedy(seed)
        else:
            raise ValueError(kind)

    def stats(self):
        if self.module is None:
            return None
        return dict(getattr(self.module, "search_stats", {}))


def fmt_score(score):
    """Agent scores are material units; +/-inf means it has seen a forced mate."""
    if score == float("inf") or score > 1000:
        return "mate"
    if score == float("-inf") or score < -1000:
        return "-mate"
    return f"{score:+.2f}"


def play_game(white, black, start="sample0", move_time=1.0, max_plies=200,
              seed=None, show=False, out=print):
    """Play one game and return a dict describing it.

    ``white``/``black`` are player type names. The result is decided by
    ``fragments.rules`` after every move; a game that reaches
    ``max_plies`` is scored as a draw.
    """
    rng = random.Random(seed)
    sides = {"white": Side(white, rng.random()), "black": Side(black, rng.random())}
    board = new_board(start)
    tracker = ResultTracker()
    frames = [{"rows": board_rows(board), "move": None}]
    agent_moves = []
    result = None

    if show:
        out(f"=== {white} (white) vs {black} (black), start {start} ===")
        out(board_to_text(board))

    ply = 1
    while ply <= max_plies:
        mover = board.current_player
        side = sides[mover.name]
        t0 = time.perf_counter()
        try:
            chosen_piece, chosen_move = side.fn(board.clone(), mover, [ply, move_time])
        except Exception as exc:  # a crashing player forfeits
            chosen_piece, chosen_move = None, None
            out(f"{mover.name} ({side.kind}) raised {exc!r}")
        elapsed = time.perf_counter() - t0
        _, piece, move = copy_piece_move(board, chosen_piece, chosen_move)
        if piece is None or move is None:
            # Same outcome as the coursework runner: no legal move returned
            # means the game is lost. agent.py returns no move when every
            # legal move leads to a forced mate it has already seen.
            if chosen_piece is None and chosen_move is None:
                result = f"Resigned (no move returned) - {mover.name} loses"
            else:
                result = f"Illegal move - {mover.name} loses"
            break

        stats = side.stats()
        note = describe_move(piece, move)
        if stats is not None:
            stats["time"] = elapsed
            agent_moves.append(stats)
        piece.move(move)
        frames.append({"rows": board_rows(board), "move": note, "by": mover.name,
                       "stats": stats})

        if show:
            line = f"ply {ply:3d}  {mover.name:5s} ({side.kind}): {note}"
            if stats is not None:
                line += (f"   [depth {stats['depth']}, score {fmt_score(stats['score'])}, "
                         f"{stats['nodes']} nodes, {elapsed:.2f}s]")
            out(line)
            out(board_to_text(board))

        result = tracker(board)
        if result:
            break
        ply += 1
    else:
        result = f"Draw - {max_plies} ply limit"

    if show:
        out(f"=== Game ended: {result} ===")
    return {
        "white": white, "black": black, "start": start, "result": result,
        "winner": winner_of(result), "plies": len(frames) - 1,
        "agent_moves": agent_moves, "frames": frames,
    }


def summarise(games, out=print):
    """Print W/D/L from the agent's point of view (or from white's if no agent)."""
    tally = Counter()
    per_colour = defaultdict(Counter)
    depths, nodes, seconds = [], 0, 0.0
    for g in games:
        for colour in ("white", "black"):
            if g[colour] == "agent":
                outcome = ("draw" if g["winner"] is None
                           else "win" if g["winner"] == colour else "loss")
                tally[outcome] += 1
                per_colour[colour][outcome] += 1
        for m in g["agent_moves"]:
            depths.append(m["depth"])
            nodes += m["nodes"]
            seconds += m["time"]

    if not tally:
        winners = Counter(g["winner"] or "draw" for g in games)
        out(f"results: {dict(winners)}")
        return
    out(f"agent: {tally['win']} W / {tally['draw']} D / {tally['loss']} L "
        f"over {sum(tally.values())} agent-games")
    for colour, c in per_colour.items():
        out(f"  as {colour}: {c['win']} W / {c['draw']} D / {c['loss']} L")
    if depths:
        out(f"  average search depth {sum(depths) / len(depths):.2f} "
            f"(max {max(depths)}), {nodes / seconds:,.0f} nodes/s "
            f"over {len(depths)} moves")
    reasons = Counter(g["result"].split(" - ")[0] for g in games)
    out("  endings: " + ", ".join(f"{k} x{v}" for k, v in reasons.most_common()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--white", choices=PLAYER_TYPES, default="agent")
    ap.add_argument("--black", choices=PLAYER_TYPES, default="random")
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--time", type=float, default=1.0,
                    help="agent thinking time per move in seconds (default 1.0)")
    ap.add_argument("--start", choices=("sample0", "sample1", "alternate"),
                    default="alternate",
                    help="starting position; 'alternate' switches every game")
    ap.add_argument("--max-plies", type=int, default=200,
                    help="game is a draw after this many plies (default 200)")
    ap.add_argument("--show", action="store_true", help="print the board every ply")
    ap.add_argument("--record", metavar="FILE",
                    help="save the games (positions + moves) as JSON")
    args = ap.parse_args(argv)

    games = []
    for n in range(args.games):
        start = args.start if args.start != "alternate" else ("sample0", "sample1")[n % 2]
        game = play_game(args.white, args.black, start=start, move_time=args.time,
                         max_plies=args.max_plies, seed=args.seed * 1000 + n,
                         show=args.show)
        games.append(game)
        print(f"game {n + 1}/{args.games}: {args.white} (white) vs {args.black} "
              f"(black), {start}: {game['result']} after {game['plies']} plies",
              flush=True)

    summarise(games)
    if args.record:
        with open(args.record, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=1)
    return games


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
