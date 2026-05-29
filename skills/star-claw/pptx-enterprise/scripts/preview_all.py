#!/usr/bin/env python3
"""Render EVERY slide of a deck JSON to PNGs for visual QA (uses preview.js per slide).
Produces <outdir>/slide-01.png ... so the whole deck can be eyeballed in one go.

usage: preview_all.py <deck.json> [outdir]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 2:
        print("usage: preview_all.py <deck.json> [outdir]", file=sys.stderr)
        sys.exit(2)
    deck_path = Path(sys.argv[1])
    deck = json.loads(deck_path.read_text(encoding="utf-8"))
    n = len(deck.get("slides", []))
    outdir = Path(sys.argv[2]) if len(sys.argv) >= 3 else deck_path.parent / f"{deck_path.stem}.preview"
    outdir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i in range(n):
        out = outdir / f"slide-{i + 1:02d}.png"
        r = subprocess.run(["node", str(ROOT / "scripts" / "preview.js"), str(deck_path), str(i), str(out)],
                           capture_output=True, text=True)
        if out.exists():
            ok += 1
        else:
            print(f"slide {i + 1} failed: {r.stderr.strip()[:120]}", file=sys.stderr)
    print(f"rendered {ok}/{n} slides -> {outdir}")
    print("Visual QA: open each PNG and hunt for overlap / overflow / clipping / low-contrast / uneven gaps. Assume there ARE issues.")


if __name__ == "__main__":
    main()
