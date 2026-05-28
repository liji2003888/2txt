#!/usr/bin/env python3
"""Map a designed outline (per-slide layout + content) into slide JSON conforming to slide_schema.json."""
import json
import sys
from pathlib import Path

from layouts import LAYOUTS, CONTENT_LAYOUTS, palette, footer

CANVAS_W, CANVAS_H = 960, 540


def build(outline: dict, theme: dict) -> dict:
    pal = palette(theme)
    specs = outline.get("slides", [])
    if not specs:
        specs = [{"layout": "title", "title": outline.get("title", "Untitled"), "subtitle": outline.get("subtitle")}]
    slides = []
    page = 0
    for spec in specs:
        layout = spec.get("layout", "bullets")
        fn = LAYOUTS.get(layout, LAYOUTS["bullets"])
        slide = fn(spec, pal)
        if layout in CONTENT_LAYOUTS:
            page += 1
            slide["elements"].extend(footer(pal, page))
        slides.append(slide)
    return {
        "meta": {
            "title": outline.get("title", "Untitled"),
            "width": CANVAS_W,
            "height": CANVAS_H,
            "theme": theme,
        },
        "slides": slides,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: outline_to_schema.py <outline.json> [branding.json]", file=sys.stderr)
        sys.exit(2)
    outline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    theme: dict = {}
    if len(sys.argv) >= 3:
        branding = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        theme = {
            "fontName": branding.get("fontName"),
            "fontColor": branding.get("fontColor"),
            "backgroundColor": branding.get("backgroundColor"),
            "themeColors": branding.get("themeColors", []),
        }
    deck = build(outline, theme)
    json.dump(deck, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
