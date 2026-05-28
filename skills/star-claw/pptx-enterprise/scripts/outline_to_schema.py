#!/usr/bin/env python3
"""Template a structured outline into slide JSON conforming to slide_schema.json."""
import json
import sys
import uuid
from pathlib import Path

CANVAS_W = 960
CANVAS_H = 540


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def title_slide(title: str, subtitle: str | None, theme: dict) -> dict:
    elements = [{
        "id": new_id(),
        "type": "text",
        "left": 80, "top": 200, "width": 800, "height": 80,
        "content": f"<p style='text-align:center'><strong>{title}</strong></p>",
        "fontSize": 44,
        "defaultColor": theme.get("fontColor", "#111111"),
        "defaultFontName": theme.get("fontName", ""),
    }]
    if subtitle:
        elements.append({
            "id": new_id(),
            "type": "text",
            "left": 80, "top": 300, "width": 800, "height": 50,
            "content": f"<p style='text-align:center'>{subtitle}</p>",
            "fontSize": 20,
            "defaultColor": "#666666",
            "defaultFontName": theme.get("fontName", ""),
        })
    return {"id": new_id(), "elements": elements}


def section_divider(label: str, theme: dict) -> dict:
    color = (theme.get("themeColors") or ["#0F4C81"])[0]
    return {
        "id": new_id(),
        "background": {"type": "solid", "color": color},
        "elements": [{
            "id": new_id(),
            "type": "text",
            "left": 60, "top": 230, "width": 840, "height": 80,
            "content": f"<p style='text-align:center'><strong>{label}</strong></p>",
            "fontSize": 40,
            "defaultColor": "#FFFFFF",
            "defaultFontName": theme.get("fontName", ""),
        }],
    }


def content_slide(title: str, bullets: list[str], theme: dict) -> dict:
    elements = [{
        "id": new_id(),
        "type": "text",
        "left": 60, "top": 50, "width": 840, "height": 60,
        "content": f"<p><strong>{title}</strong></p>",
        "fontSize": 28,
        "defaultColor": theme.get("fontColor", "#111111"),
        "defaultFontName": theme.get("fontName", ""),
    }]
    body_html = "".join(f"<li>{b}</li>" for b in bullets)
    elements.append({
        "id": new_id(),
        "type": "text",
        "left": 60, "top": 130, "width": 840, "height": 360,
        "content": f"<ul>{body_html}</ul>",
        "fontSize": 18,
        "defaultColor": "#333333",
        "defaultFontName": theme.get("fontName", ""),
    })
    return {"id": new_id(), "elements": elements}


def build(outline: dict, theme: dict) -> dict:
    slides = [title_slide(outline.get("title", "Untitled"), outline.get("subtitle"), theme)]
    for section in outline.get("sections", []):
        if section.get("divider", True):
            slides.append(section_divider(section["title"], theme))
        for slide in section.get("slides", []):
            slides.append(content_slide(slide["title"], slide.get("bullets", []), theme))
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
