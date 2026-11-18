"""Render a recorded game as an animated GIF.

    python play.py --white agent --black greedy --games 1 --seed 4 --record game.json
    python tools/render_gif.py game.json media/agent_win.gif

Pieces are drawn as discs with their letter (K Q B N R P, R = Right).
"""

import argparse
import json
import re

from PIL import Image, ImageDraw, ImageFont

CELL = 72
MARGIN = 24
CAPTION = 56
LIGHT, DARK = (238, 228, 206), (176, 141, 105)
HIGHLIGHT = (246, 214, 92)
WHITE_FILL, WHITE_EDGE = (250, 250, 250), (40, 40, 40)
BLACK_FILL, BLACK_EDGE = (35, 35, 35), (220, 220, 220)
BACKGROUND = (48, 46, 43)
TEXT = (235, 235, 235)

MOVE_RE = re.compile(r"(\d),(\d) -> (\d),(\d)")


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def draw_frame(rows, caption, last_move, fonts):
    size = 5 * CELL
    img = Image.new("RGB", (size + 2 * MARGIN, size + 2 * MARGIN + CAPTION), BACKGROUND)
    d = ImageDraw.Draw(img)
    piece_font, coord_font, caption_font = fonts

    marked = set()
    if last_move:
        m = MOVE_RE.search(last_move)
        if m:
            x0, y0, x1, y1 = map(int, m.groups())
            marked = {(x0, y0), (x1, y1)}

    for y in range(5):
        for x in range(5):
            left, top = MARGIN + x * CELL, MARGIN + y * CELL
            colour = HIGHLIGHT if (x, y) in marked else (LIGHT if (x + y) % 2 == 0 else DARK)
            d.rectangle([left, top, left + CELL - 1, top + CELL - 1], fill=colour)
            symbol = rows[y][x]
            if symbol == ".":
                continue
            white = symbol.isupper()
            pad = 9
            d.ellipse([left + pad, top + pad, left + CELL - pad, top + CELL - pad],
                      fill=WHITE_FILL if white else BLACK_FILL,
                      outline=WHITE_EDGE if white else BLACK_EDGE, width=3)
            d.text((left + CELL / 2, top + CELL / 2 + 1), symbol.upper(), anchor="mm",
                   font=piece_font, fill=WHITE_EDGE if white else BLACK_EDGE)

    for i in range(5):
        d.text((MARGIN + i * CELL + CELL / 2, MARGIN / 2), str(i), anchor="mm",
               font=coord_font, fill=TEXT)
        d.text((MARGIN / 2, MARGIN + i * CELL + CELL / 2), str(i), anchor="mm",
               font=coord_font, fill=TEXT)

    d.text((img.width / 2, size + 2 * MARGIN + CAPTION / 2 - 4), caption, anchor="mm",
           font=caption_font, fill=TEXT)
    return img


def caption_for(frame, ply, game):
    if frame["move"] is None:
        return f"agent = {'white' if game['white'] == 'agent' else 'black'} vs {game['black'] if game['white'] == 'agent' else game['white']}"
    text = f"{ply}. {frame['by']}: {frame['move']}"
    stats = frame.get("stats")
    if stats:
        score = stats["score"]
        shown = "mate" if abs(score) > 1000 else f"{score:+.1f}"
        text += f"  (depth {stats['depth']}, {shown})"
    return text


def render(game, out_path, frame_ms=900, end_ms=3000):
    fonts = (font(34), font(14), font(17))
    frames, durations = [], []
    for ply, frame in enumerate(game["frames"]):
        frames.append(draw_frame(frame["rows"], caption_for(frame, ply, game), frame["move"], fonts))
        durations.append(frame_ms)
    final = draw_frame(game["frames"][-1]["rows"], game["result"], game["frames"][-1]["move"], fonts)
    frames.append(final)
    durations.append(end_ms)
    durations[0] = 1500
    frames = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=64) for f in frames]
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record", help="JSON file written by play.py --record")
    ap.add_argument("out", help="output .gif path")
    ap.add_argument("--game", type=int, default=0, help="index of the game in the record")
    args = ap.parse_args()
    with open(args.record, encoding="utf-8") as f:
        games = json.load(f)
    render(games[args.game], args.out)
    print(f"wrote {args.out}: {games[args.game]['result']}, {games[args.game]['plies']} plies")


if __name__ == "__main__":
    main()
