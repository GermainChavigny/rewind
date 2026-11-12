"""Cuts the two 3x3 channel logo boards into 18 backgrounds.

Usage: python scripts/cut-channel-logos.py   (needs Pillow)
Reads assets/channel-logos/board-{1,2}.webp, writes
frontend/public/img/channels/v{1,2}/{1..9}.webp. The cells are thirds of the
board; a small inset drops the seams between them.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
INSET = 6
SIZE = 320

for variant in (1, 2):
    board = Image.open(ROOT / f"assets/channel-logos/board-{variant}.webp").convert("RGB")
    w, h = board.size
    out = ROOT / f"frontend/public/img/channels/v{variant}"
    out.mkdir(parents=True, exist_ok=True)
    for n in range(9):
        row, col = divmod(n, 3)
        x0, x1 = round(col * w / 3), round((col + 1) * w / 3)
        y0, y1 = round(row * h / 3), round((row + 1) * h / 3)
        cell = board.crop((x0 + INSET, y0 + INSET, x1 - INSET, y1 - INSET))
        cell = cell.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        cell.save(out / f"{n + 1}.webp", quality=88, method=6)
        print(out / f"{n + 1}.webp")
