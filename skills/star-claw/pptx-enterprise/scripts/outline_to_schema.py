#!/usr/bin/env python3
"""Map a designed outline (per-slide layout + content) into slide JSON conforming to slide_schema.json."""
import json
import subprocess
import sys
from pathlib import Path

from layouts import LAYOUTS, CONTENT_LAYOUTS, palette, footer, chrome_elements, banner_elements, header
from compose import compose_slide

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


def resolve_charts(deck: dict) -> None:
    """Rasterize ONLY custom chart types that have no native equivalent (gauge) to PNG.
    Real charts (column/bar/line/area/pie/donut/radar) stay as native, editable chart
    elements — both renderers emit them via PptxGenJS / python-pptx add_chart."""
    import hashlib
    NATIVE = {"column", "bar", "line", "area", "pie", "donut", "doughnut", "radar", "scatter"}
    theme = deck.get("meta", {}).get("theme") or {}
    font = theme.get("fontName") or "sans-serif"
    todo, refs = [], []
    for slide in deck["slides"]:
        for el in slide["elements"]:
            if el.get("type") != "chart":
                continue
            if el.get("chartType", "column") in NATIVE:
                continue  # keep native/editable
            spec = {
                "type": el.get("chartType", "column"),
                "labels": (el.get("data") or {}).get("labels", []),
                "series": (el.get("data") or {}).get("series", []),
                "colors": el.get("themeColors"),
                "width": int(el.get("width", 840)),
                "height": int(el.get("height", 350)),
                "font": font,
            }
            key = hashlib.md5(json.dumps(spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
            out = ICON_CACHE / f"chart_{key}.png"
            spec["out"] = str(out)
            todo.append(spec)
            refs.append((el, out))
    if not refs:
        return
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    pending = [s for s in todo if not Path(s["out"]).exists()]
    if pending:
        mf = ICON_CACHE / "_charts.json"
        mf.write_text(json.dumps(pending, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["node", str(ROOT / "scripts" / "chart_img.js"), str(mf)], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout + r.stderr, file=sys.stderr)
    for el, out in refs:
        if out.exists():
            for k in ("chartType", "data", "themeColors"):
                el.pop(k, None)
            el["type"] = "image"
            el["src"] = str(out)


def resolve_gradients(deck: dict) -> None:
    """Rasterize shapes that carry fillGrad into transparent gradient PNGs (with optional glow),
    keeping all text native/editable. Premium look without native-gradient support."""
    import hashlib
    todo, refs = [], []
    for slide in deck["slides"]:
        for el in slide["elements"]:
            if el.get("type") != "shape" or not el.get("fillGrad"):
                continue
            w, h = int(el["width"]), int(el["height"])
            glow = bool(el.get("glow"))
            pad = round(min(w, h) * 0.12) if glow else 2
            spec = {"shape": el.get("shapeType", "roundRect"), "w": w, "h": h,
                    "c1": el["fillGrad"][0], "c2": el["fillGrad"][1],
                    "angle": el.get("gradAngle", 120), "glow": glow,
                    "radius": round(min(w, h) * 0.12) if el.get("shapeType") == "roundRect" else 0}
            key = hashlib.md5(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:14]
            out = ICON_CACHE / f"grad_{key}.png"
            spec["out"] = str(out)
            todo.append(spec)
            refs.append((el, out, pad, w, h))
    if not refs:
        return
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    pending = [s for s in todo if not Path(s["out"]).exists()]
    if pending:
        mf = ICON_CACHE / "_grads.json"
        mf.write_text(json.dumps(pending, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["node", str(ROOT / "scripts" / "shape_img.js"), str(mf)], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout + r.stderr, file=sys.stderr)
    for el, out, pad, w, h in refs:
        if not out.exists():
            continue
        # expand bounds to include glow/anti-alias padding, keep shape centered
        el["left"] = el["left"] - pad
        el["top"] = el["top"] - pad
        el["width"] = w + pad * 2
        el["height"] = h + pad * 2
        for k in ("shapeType", "fill", "fillGrad", "gradAngle", "glow", "shadow", "outline"):
            el.pop(k, None)
        el["type"] = "image"
        el["src"] = str(out)


def build(outline: dict, theme: dict) -> dict:
    pal = palette(theme)
    specs = outline.get("slides", [])
    if not specs:
        specs = [{"layout": "title", "title": outline.get("title", "Untitled"), "subtitle": outline.get("subtitle")}]
    slides = []
    page = 0
    for spec in specs:
        layout = spec.get("layout", "bullets")
        # Auto-layout path: a slide with a "body" tree is composed by the layout engine.
        if spec.get("body") is not None:
            content_bottom = 474 if spec.get("banner") else 500
            els = list(header(spec.get("title", ""), pal)) if spec.get("title") else []
            try:
                els += compose_slide(spec, pal, (60, 120, 900, content_bottom))
                slide = {"id": __import__("uuid").uuid4().hex[:10], "elements": els}
            except Exception as exc:
                print(f"warning: compose failed ({exc}); falling back to bullets", file=sys.stderr)
                slide = LAYOUTS["bullets"]({"title": spec.get("title", ""), "points": []}, pal)
                layout = "bullets"
            else:
                layout = "auto"
        else:
            fn = LAYOUTS.get(layout, LAYOUTS["bullets"])
            try:
                slide = fn(spec, pal)
            except Exception as exc:  # one malformed slide must not abort the whole deck
                print(f"warning: layout '{layout}' failed ({exc}); falling back to bullets", file=sys.stderr)
                fallback = {"title": spec.get("title", ""), "points": spec.get("points") or spec.get("bullets") or spec.get("items") or []}
                slide = LAYOUTS["bullets"](fallback, pal)
                layout = "bullets"
        slide.setdefault("background", {"type": "solid", "color": pal["bg"]})
        # role drives the template renderer's master-layout choice; full=full-bleed colored slide
        if layout == "cover":
            slide["role"] = "cover"
        elif layout in ("section", "quote", "closing"):
            slide["role"] = "full"
        else:
            slide["role"] = "content"
        chrome_ok = layout != "cover" and spec.get("chrome", True)
        if chrome_ok and slide["background"].get("color") == pal["bg"]:
            slide["elements"].extend(chrome_elements(theme))
        if spec.get("banner"):
            b = spec["banner"]
            if isinstance(b, dict):
                slide["elements"].extend(banner_elements(b.get("text", ""), palette(theme), sub=b.get("sub")))
            else:
                slide["elements"].extend(banner_elements(str(b), palette(theme)))
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
    resolve_gradients(deck)
    resolve_charts(deck)
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
