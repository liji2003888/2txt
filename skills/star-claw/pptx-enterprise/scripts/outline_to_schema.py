#!/usr/bin/env python3
"""Map a designed outline (per-slide layout + content) into slide JSON conforming to slide_schema.json."""
import json
import subprocess
import sys
from pathlib import Path

from layouts import LAYOUTS, CONTENT_LAYOUTS, palette, footer, chrome_elements

ROOT = Path(__file__).resolve().parent.parent
CANVAS_W, CANVAS_H = 960, 540
DEFAULT_THEME = ROOT / "assets" / "themes" / "tcl_feishu.json"
ICON_CACHE = ROOT / "assets" / ".icon_cache"


def resolve_icons(deck: dict) -> None:
    refs, manifest = [], {}
    for slide in deck["slides"]:
        for el in slide["elements"]:
            src = el.get("src")
            if el.get("type") == "image" and isinstance(src, str) and src.startswith("icon:"):
                set_, _, name = src[5:].partition("/")
                color = (el.pop("iconColor", None) or "#FFFFFF").replace("#", "")
                size = max(64, int(el.get("width", 32)) * 3)
                key = f"{set_}__{name}__{color}__{size}".replace("/", "_")
                out = ICON_CACHE / f"{key}.png"
                manifest[key] = {"set": set_, "name": name, "color": f"#{color}", "size": size, "out": str(out)}
                refs.append((el, out))
    if not refs:
        return
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    todo = [v for v in manifest.values() if not Path(v["out"]).exists()]
    if todo:
        mf = ICON_CACHE / "_manifest.json"
        mf.write_text(json.dumps(todo), encoding="utf-8")
        r = subprocess.run(["node", str(ROOT / "scripts" / "icon.js"), str(mf)], capture_output=True, text=True)
        if r.returncode != 0 or r.stderr:
            print(r.stdout + r.stderr, file=sys.stderr)
    for el, out in refs:
        if out.exists():
            el["src"] = str(out)
        else:
            el["_drop"] = True
    for slide in deck["slides"]:
        slide["elements"] = [e for e in slide["elements"] if not e.get("_drop")]


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
        slide.setdefault("background", {"type": "solid", "color": pal["bg"]})
        if slide["background"].get("color") == pal["bg"] and spec.get("chrome", True):
            slide["elements"].extend(chrome_elements(theme))
        if layout in CONTENT_LAYOUTS:
            page += 1
            slide["elements"].extend(footer(pal, page))
        slides.append(slide)
    deck = {
        "meta": {
            "title": outline.get("title", "Untitled"),
            "width": CANVAS_W,
            "height": CANVAS_H,
            "theme": theme,
        },
        "slides": slides,
    }
    resolve_icons(deck)
    return deck


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: outline_to_schema.py <outline.json> [branding.json]", file=sys.stderr)
        sys.exit(2)
    outline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    theme_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_THEME
    theme = json.loads(theme_path.read_text(encoding="utf-8")) if theme_path.exists() else {}
    deck = build(outline, theme)
    json.dump(deck, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
