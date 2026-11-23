"""Setup check: proves a fresh clone is wired together.

Run on its own with ``python -m pytest -m setup``. It checks the Python
version and dependencies, that every module of the repo imports, that the
agent is running on this repo's rules engine (not the coursework
framework), and that whole games run headlessly to a proper result with
legal moves only.
"""

import importlib
import importlib.metadata
import importlib.util
import os
import sys

import pytest

from play import ROOT, load_agent_module, main, play_game

pytestmark = pytest.mark.setup


def test_python_version_is_supported():
    assert (3, 11) <= sys.version_info[:2] <= (3, 12), (
        "ChessMaker 0.5.0 needs Python 3.11 or 3.12")


def test_dependencies_installed():
    assert importlib.metadata.version("chessmaker") == "0.5.0"
    importlib.import_module("PIL")
    importlib.import_module("chessmaker.chess.base")


@pytest.mark.parametrize("module", [
    "fragments", "fragments.board_utils", "fragments.opponents", "fragments.pieces",
    "fragments.rules", "fragments.setup", "play",
])
def test_repo_modules_import(module):
    importlib.import_module(module)


@pytest.mark.parametrize("script", ["benchmark.py", "render_gif.py"])
def test_tools_import(script):
    # difftest.py is left out on purpose: it needs the coursework framework.
    spec = importlib.util.spec_from_file_location(
        f"_tool_{script[:-3]}", os.path.join(ROOT, "tools", script))
    spec.loader.exec_module(importlib.util.module_from_spec(spec))


def test_agent_uses_this_repos_rules_engine():
    agent = load_agent_module()
    assert agent.list_legal_moves_for.__module__ == "fragments.board_utils"
    assert agent.copy_piece_move.__module__ == "fragments.board_utils"


@pytest.mark.parametrize("white, black, start", [
    ("agent", "greedy", "sample0"),
    ("greedy", "agent", "sample1"),
    ("agent", "random", "sample1"),
])
def test_full_game_completes_with_legal_moves(white, black, start):
    log = []
    game = play_game(white, black, start=start, move_time=0.15, max_plies=80,
                     seed=7, out=log.append)
    # play_game ends the game as a loss on any illegal move or crash.
    assert not game["result"].startswith(("Illegal move", "Resigned")), game["result"]
    assert not any("raised" in line for line in log), log
    assert game["plies"] == len(game["frames"]) - 1 >= 1
    assert all(m["depth"] >= 1 for m in game["agent_moves"])
    if game["winner"] is not None:  # a decisive game ended by the rules engine
        assert game["result"].split(" - ")[0] in {
            "Checkmate", "Stalemate (no legal moves)", "No kings left"}


def test_cli_plays_records_and_renders(tmp_path, capsys):
    """play.py's command line, its JSON recording and the GIF renderer end to end."""
    record = tmp_path / "games.json"
    games = main(["--white", "agent", "--black", "greedy", "--games", "2",
                  "--time", "0.1", "--max-plies", "30", "--seed", "1",
                  "--record", str(record)])
    assert len(games) == 2
    assert "agent:" in capsys.readouterr().out
    assert record.stat().st_size > 0

    spec = importlib.util.spec_from_file_location(
        "_tool_render_gif", os.path.join(ROOT, "tools", "render_gif.py"))
    render_gif = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render_gif)
    gif = tmp_path / "game.gif"
    render_gif.render(games[0], str(gif))
    assert gif.read_bytes()[:3] == b"GIF"
