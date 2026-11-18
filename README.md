# chess-agent

A game-playing agent for **Chess Fragments**, a chess variant on a reduced board with custom pieces (including a "Right" piece and queen-only pawn promotion). It plays complete games under a fixed thinking-time budget per move.

> Coursework for the University of Southampton AI module (COMP2321, 2025). This repo contains only my agent (`agent.py`). The game framework (`extension/`, `opponent.py`, `samples.py`, `test_fullgame.py`) was provided by the module and isn't included.

## How the agent searches

- **Minimax with alpha-beta pruning,** written as separate max and min functions
- **Iterative deepening** inside the per-move time budget, so it always has a best move ready
- **Aspiration windows** that search a narrow score range around the previous depth's result and re-search with a full window if the score falls outside it
- **Transposition table** keyed by a position hash, storing exact, lower and upper bounds
- **Principal variation table** that tries the previous iteration's best move first
- **Move ordering:** PV move first, then MVV-LVA (most valuable victim, least valuable attacker) for captures
- **Null-move pruning** at depth 3 and below when material allows
- **Evaluation:** material balance plus piece-position terms, with incremental material deltas per move

## Prerequisites

`agent.py` is not standalone. It imports `list_legal_moves_for` and `copy_piece_move` from `extension.board_utils`, which is part of the module's coursework support package (`CW-COMP2321-fullgame`), not this repo. That package defines the Chess Fragments board and pieces and provides the game runner. You need:

- **Python 3.11 or 3.12, not 3.13 or newer.** ChessMaker defines `Piece.name` with `@classmethod` stacked on `@property`, which Python 3.13 removed. On 3.13 the first board print fails with `AttributeError: 'property' object has no attribute 'lower'`.
- [ChessMaker](https://github.com/WolfDWyc/ChessMaker) by WolfDWyc (`pip install chessmaker`, tested with 0.5.0). This is the open-source, AGPL-3.0 chess engine the coursework framework is built on.
- The COMP2321 coursework support package `CW-COMP2321-fullgame`, which contains `extension/`, `opponent.py`, `samples.py` and `test_fullgame.py`. It was distributed to students taking the module. The same `extension/` files are used by [Fragment Arena](https://github.com/Seggys116/chess-fragments-platform), a student-built tournament platform for this coursework that also runs agents on Python 3.12.

No API keys are needed.

## Run

Copy the support package's `extension/`, `opponent.py`, `samples.py` and `test_fullgame.py` into this folder, next to `agent.py`. `.gitignore` already excludes them. Then:

```bash
py -3.12 -m venv .venv             # or: uv venv --python 3.12 .venv
source .venv/Scripts/activate      # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install chessmaker
python test_fullgame.py
```

Expected end of output: `=== Game ended: Checkmate - black loses ===`. The agent plays white against the module's opponent on `sample0`.

`test_fullgame.py` plays the agent against the provided opponent. The framework calls `agent(board, player, var)`, where `var` is `[ply, thinking_time_seconds]`, and expects a `(piece, move)` pair back. Set `DEBUG = True` at the top of `agent.py` to print the search depth and score for each move.

## Test

The repo has no tests of its own. Without the support package the agent can only be syntax-checked:

```bash
python -m py_compile agent.py
```

Importing it (`python -c "import agent"`) fails with `ModuleNotFoundError: No module named 'extension'` unless the support package is present. Full games run through the package's `test_fullgame.py`, as above.
