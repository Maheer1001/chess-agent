# Chess Fragments Agent

A game-playing agent for **Chess Fragments**, a chess variant on a reduced board with custom pieces (including a "Right" piece and queen-only pawn promotion). It plays complete games under a fixed thinking-time budget per move.

> Coursework for the University of Southampton AI module (COMP2321, 2025). This repo contains only my agent (`agent.py`). The game framework (`extension/`, `opponent.py`, `samples.py`, `test_fullgame.py`) was provided by the module and isn't included.

## How the agent searches

- **Minimax with alpha-beta pruning,** written as separate max and min functions
- **Iterative deepening** inside the per-move time budget, so it always has a best move ready
- **Transposition table** keyed by a position hash, storing exact, lower and upper bounds
- **Principal variation table** that tries the previous iteration's best move first
- **Move ordering:** PV move first, then MVV-LVA (most valuable victim, least valuable attacker) for captures
- **Null-move pruning** at depth 3 and below when material allows
- **Evaluation:** material balance plus piece-position terms, with incremental material deltas per move

## Running it

Requires Python 3.11+ and the [`chessmaker`](https://pypi.org/project/chessmaker/) package:

```bash
pip install chessmaker
```

Put `agent.py` into the coursework support package (`CW-COMP2321-fullgame`) and run its `test_fullgame.py`, which plays the agent against the provided opponent.
