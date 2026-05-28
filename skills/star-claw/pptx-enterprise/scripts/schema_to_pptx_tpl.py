#!/usr/bin/env python3
"""Render a deck JSON onto an existing .pptx master/layouts (python-pptx), so brand chrome
(corner badge, logo, cover background) comes pixel-perfect from the master and titles sit where
the template puts them. Body content is composed from the deck JSON.

usage: schema_to_pptx_tpl.py <deck.json> <out.pptx>
The deck's theme must set: baseTemplate, and optionally contentLayout / coverLayout / fullLayout (layout names).
"""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parent.parent
import json

SHAPE_MAP = {
    "rect": MSO_SHAPE.RECTANGLE,
    "roundRect": MSO_SHAPE.ROUNDED_RECTANGLE,
    "ellipse": MSO_SHAPE.OVAL,
    "triangle": MSO_SHAPE.ISOSCELES_TRIANGLE,
    "diamond": MSO_SHAPE.DIAMOND,
    "arrow": MSO_SHAPE.RIGHT_ARROW,
    "star": MSO_SHAPE.STAR_5_POINT,
}
ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
VALIGN = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}


def _rgb(c):
    return RGBColor.from_string(str(c).replace("#", "").upper()[:6])


def _strip_html(s):
    import re
    s = re.sub(r"<br\s*/?>", "\n", str(s), flags=re.I)
    s = re.sub(r"</(p|li|div)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("&nbsp;", " ").replace("&amp;", "&").strip()


def _bullets(html):
    import re
    items = [_strip_html(m) for m in re.findall(r"<li[^>]*>([\s\S]*?)</li>", str(html), flags=re.I)]
    return items or None


def find_layout(prs, name):
    for layout in prs.slide_layouts:
        if layout.name == name:
            return layout
    return None


def render_text(slide, el, W, H, sx, sy):
    box = slide.shapes.add_textbox(Emu(int(el["left"] * sx)), Emu(int(el["top"] * sy)),
                                   Emu(int(el["width"] * sx)), Emu(int(el["height"] * sy)))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = VALIGN.get(el.get("valign", "top"), MSO_ANCHOR.TOP)
    size = el.get("fontSize", 18)
    color = el.get("defaultColor", "#000000")
    font = el.get("defaultFontName") or ""
    bullets = _bullets(el.get("content", ""))
    lines = bullets if bullets else _strip_html(el.get("content", "")).split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = ALIGN.get(el.get("align", "left"), PP_ALIGN.LEFT)
        run = p.add_run()
        run.text = ("• " + ln) if bullets else ln
        run.font.size = Pt(size)
        run.font.bold = bool(el.get("bold"))
        run.font.italic = bool(el.get("italic"))
        run.font.color.rgb = _rgb(color)
        if font:
            run.font.name = font


def render_shape(slide, el, sx, sy):
    st = SHAPE_MAP.get(el.get("shapeType", "rect"), MSO_SHAPE.RECTANGLE)
    shp = slide.shapes.add_shape(st, Emu(int(el["left"] * sx)), Emu(int(el["top"] * sy)),
                                 Emu(int(max(el["width"], 1) * sx)), Emu(int(max(el["height"], 1) * sy)))
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(el.get("fill", "#CCCCCC"))
    shp.line.fill.background()
    if el.get("text", {}).get("content"):
        tf = shp.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = _strip_html(el["text"]["content"])
        r.font.size = Pt(16); r.font.color.rgb = _rgb(el["text"].get("defaultColor", "#FFFFFF"))


def render_table(slide, el, sx, sy):
    data = el.get("data", [])
    if not data:
        return
    rows, cols = len(data), len(data[0])
    gf = slide.shapes.add_table(rows, cols, Emu(int(el["left"] * sx)), Emu(int(el["top"] * sy)),
                                Emu(int(el["width"] * sx)), Emu(int(el["height"] * sy)))
    tbl = gf.table
    for r in range(rows):
        for c in range(cols):
            cell = data[r][c] or {}
            tc = tbl.cell(r, c)
            tc.text = str(cell.get("text", ""))
            para = tc.text_frame.paragraphs[0]
            if para.runs:
                para.runs[0].font.size = Pt(12)
                para.runs[0].font.bold = bool(cell.get("bold"))
                if cell.get("color"):
                    para.runs[0].font.color.rgb = _rgb(cell["color"])
            if cell.get("fill"):
                tc.fill.solid(); tc.fill.fore_color.rgb = _rgb(cell["fill"])


def render_line(slide, el, sx, sy):
    x1 = (el["left"] + (el.get("start", [0, 0])[0])) * sx
    y1 = (el["top"] + (el.get("start", [0, 0])[1])) * sy
    x2 = (el["left"] + (el.get("end", [el["width"], 0])[0])) * sx
    y2 = (el["top"] + (el.get("end", [el["width"], 0])[1])) * sy
    conn = slide.shapes.add_connector(2, Emu(int(x1)), Emu(int(y1)), Emu(int(x2)), Emu(int(y2)))
    conn.line.color.rgb = _rgb(el.get("color", "#000000"))
    conn.line.width = Pt(el.get("width", 1))


def render_image(slide, el, sx, sy):
    src = el.get("src", "")
    if not src or src.startswith("icon:"):
        return
    p = Path(src)
    if not p.is_absolute():
        p = ROOT / src
    if p.exists():
        slide.shapes.add_picture(str(p), Emu(int(el["left"] * sx)), Emu(int(el["top"] * sy)),
                                 Emu(int(el["width"] * sx)), Emu(int(el["height"] * sy)))


def main():
    if len(sys.argv) < 3:
        print("usage: schema_to_pptx_tpl.py <deck.json> <out.pptx>", file=sys.stderr)
        sys.exit(2)
    deck = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    theme = (deck.get("meta", {}).get("theme") or {})
    base = theme.get("baseTemplate")
    if not base:
        sys.exit("error: theme.baseTemplate not set; this renderer needs a master template")
    bp = Path(base)
    if not bp.is_absolute():
        bp = ROOT / base
    prs = Presentation(str(bp))
    # remove any example slides, keep masters/layouts
    lst = prs.slides._sldIdLst
    for el in list(lst):
        rId = el.get(qn("r:id"))
        try:
            prs.part.drop_rel(rId)
        except Exception:
            pass
        lst.remove(el)

    W = deck["meta"].get("width", 960)
    H = deck["meta"].get("height", 540)
    sx = prs.slide_width / W
    sy = prs.slide_height / H

    names = {
        "content": theme.get("contentLayout", "标题幻灯片"),
        "cover": theme.get("coverLayout", "空白"),
        "full": theme.get("fullLayout", theme.get("contentLayout", "标题幻灯片")),
    }
    blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
    skip_roles = {"chrome", "coverbg"}

    for s in deck["slides"]:
        role = s.get("role", "content")
        layout = find_layout(prs, names.get(role, names["content"])) or blank
        slide = prs.slides.add_slide(layout)
        # full-bleed colored slides (section/quote/closing) still need their solid bg painted
        if role == "full" and s.get("background", {}).get("type") == "solid":
            bg = s["background"]["color"]
            shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
            shp.fill.solid(); shp.fill.fore_color.rgb = _rgb(bg); shp.line.fill.background()
        for el in s.get("elements", []):
            if el.get("role") in skip_roles:
                continue
            t = el.get("type")
            if t == "text":
                render_text(slide, el, W, H, sx, sy)
            elif t == "shape":
                render_shape(slide, el, sx, sy)
            elif t == "table":
                render_table(slide, el, sx, sy)
            elif t == "line":
                render_line(slide, el, sx, sy)
            elif t == "image":
                render_image(slide, el, sx, sy)
            # chart: rendered only by the PptxGenJS path; skipped here
    prs.save(sys.argv[2])
    print(f"wrote {sys.argv[2]} ({len(deck['slides'])} slides on master '{Path(base).name}')")


if __name__ == "__main__":
    main()
