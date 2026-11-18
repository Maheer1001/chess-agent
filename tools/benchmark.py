"""Benchmark the agent against the baseline opponents and print a Markdown table.

    python tools/benchmark.py --games 20 --time 0.5 --seed 1

Plays ``--games`` games per opponent per colour, alternating the two
starting positions. Search speed depends on the machine; results also vary
a little between runs because the agent's search is time-limited.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from play import play_game  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20, help="games per opponent per colour")
    ap.add_argument("--time", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-plies", type=int, default=200)
    ap.add_argument("--opponents", default="random,greedy")
    args = ap.parse_args()

    rows = []
    t_start = time.perf_counter()
    for opponent in args.opponents.split(","):
        for colour in ("white", "black"):
            w = d = l = 0
            depths, nodes, seconds, plies = [], 0, 0.0, 0
            for n in range(args.games):
                start = ("sample0", "sample1")[n % 2]
                white, black = ("agent", opponent) if colour == "white" else (opponent, "agent")
                g = play_game(white, black, start=start, move_time=args.time,
                              max_plies=args.max_plies,
                              seed=args.seed * 100000 + len(rows) * 1000 + n)
                if g["winner"] is None:
                    d += 1
                elif g["winner"] == colour:
                    w += 1
                else:
                    l += 1
                plies += g["plies"]
                for m in g["agent_moves"]:
                    depths.append(m["depth"])
                    nodes += m["nodes"]
                    seconds += m["time"]
                print(f"  {opponent} / agent as {colour} game {n + 1}: {g['result']} "
                      f"({g['plies']} plies)", flush=True)
            rows.append((opponent, colour, args.games, w, d, l,
                         sum(depths) / max(len(depths), 1), max(depths, default=0),
                         nodes / seconds if seconds else 0.0, plies / args.games))

    print(f"\nfinished in {time.perf_counter() - t_start:.0f}s\n")
    print("| Opponent | Agent plays | Games | Win | Draw | Loss | Avg depth | Max depth | Nodes/s | Avg plies |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for opp, colour, n, w, d, l, avg_d, max_d, nps, avg_p in rows:
        print(f"| {opp} | {colour} | {n} | {w} | {d} | {l} | {avg_d:.2f} | {max_d} | "
              f"{nps:,.0f} | {avg_p:.1f} |")


if __name__ == "__main__":
    main()
