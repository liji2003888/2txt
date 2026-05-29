#!/usr/bin/env python3
"""Build a single thumbnail-grid image of a whole deck for one-glance visual QA.

Input is a deck.json (renders every slide via preview_all.py) or a directory of
slide PNGs. Tiles them into grid.png (multiple grids if the deck is large).

usage: thumbnail.py <deck.json | png_dir> [grid.png] [--cols N]
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cols = 4
    if "--cols" in sys.argv:
        cols = int(sys.argv[sys.argv.index("--cols") + 1])
    if not args:
        print("usage: thumbnail.py <deck.json | png_dir> [grid.png] [--cols N]", file=sys.stderr)
        sys.exit(2)
    src = Path(args[0])
    out = Path(args[1]) if len(args) >= 2 else Path("grid.png")

    if src.is_file() and src.suffix == ".json":
        pngdir = Path(tempfile.mkdtemp(prefix="thumbs_"))
        subprocess.run([sys.executable, str(ROOT / "scripts" / "preview_all.py"), str(src), str(pngdir)], check=True)
    else:
        pngdir = src
    pngs = sorted(pngdir.glob("slide-*.png")) or sorted(pngdir.glob("*.png"))
    if not pngs:
        print("no slide PNGs found", file=sys.stderr)
        sys.exit(1)

    from PIL import Image
    pad, tw = 16, 480
    thumbs = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        th = int(im.height * tw / im.width)
        thumbs.append(im.resize((tw, th)))
    cell_h = max(t.height for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    per_grid_rows = max(1, (1400 // (cell_h + pad)))  # cap grid height; split if needed
    grids, idx, gi = [], 0, 0
    while idx < len(thumbs):
        chunk = thumbs[idx: idx + cols * per_grid_rows]
        r = (len(chunk) + cols - 1) // cols
        W = cols * tw + (cols + 1) * pad
        H = r * cell_h + (r + 1) * pad
        canvas = Image.new("RGB", (W, H), "#FFFFFF")
        for k, t in enumerate(chunk):
            rr, cc = divmod(k, cols)
            canvas.paste(t, (pad + cc * (tw + pad), pad + rr * (cell_h + pad)))
        name = out if len(thumbs) <= cols * per_grid_rows else out.with_name(f"{out.stem}-{gi + 1}{out.suffix}")
        canvas.save(name)
        grids.append(str(name))
        idx += cols * per_grid_rows
        gi += 1
    print("wrote:", ", ".join(grids))


if __name__ == "__main__":
    main()
