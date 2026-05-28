#!/usr/bin/env python3
"""Designed slide layouts: compose shapes + text + accents into professional slides (not bullet dumps)."""
import html as _html
import uuid

W, H = 960, 540
MARGIN = 60


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def palette(theme: dict) -> dict:
    colors = theme.get("themeColors") or ["#E60012", "#0F4C81", "#F5A623", "#7ED321", "#9013FE", "#4A4A4A"]
    return {
        "primary": colors[0],
        "secondary": colors[1] if len(colors) > 1 else colors[0],
        "accents": colors,
        "ink": theme.get("fontColor") or "#111111",
        "muted": "#5B6470",
        "light": "#F4F6F9",
        "panel": "#EEF2F7",
        "line": "#E2E6EC",
        "font": theme.get("fontName") or "",
        "bg": theme.get("backgroundColor") or "#FFFFFF",
    }


def _p(s: str) -> str:
    return f"<p>{_html.escape(str(s))}</p>"


def txt(s, left, top, w, h, size, color, *, bold=False, italic=False, align="left", valign="top", font=None, fill=None):
    e = {
        "id": new_id(), "type": "text",
        "left": left, "top": top, "width": w, "height": h,
        "content": _p(s), "fontSize": size, "defaultColor": color,
        "bold": bold, "italic": italic, "align": align, "valign": valign,
    }
    if font:
        e["defaultFontName"] = font
    if fill:
        e["fill"] = fill
    return e


def rect(left, top, w, h, fill, *, shape="rect", outline=None):
    e = {"id": new_id(), "type": "shape", "shapeType": shape, "left": left, "top": top, "width": w, "height": h, "fill": fill}
    if outline:
        e["outline"] = outline
    return e


def hline(left, top, w, color, width=1):
    return {"id": new_id(), "type": "line", "left": left, "top": top, "width": w, "height": 0,
            "start": [0, 0], "end": [w, 0], "color": color, "style": "solid", "width": width}


def vline(left, top, h, color, width=1):
    return {"id": new_id(), "type": "line", "left": left, "top": top, "width": 0, "height": h,
            "start": [0, 0], "end": [0, h], "color": color, "style": "solid", "width": width}


def _slide(elements, background=None, remark=None):
    s = {"id": new_id(), "elements": elements}
    if background:
        s["background"] = background
    if remark:
        s["remark"] = remark
    return s


def header(title, pal):
    return [
        rect(MARGIN, 54, 8, 36, pal["primary"]),
        txt(title, MARGIN + 20, 50, 800, 44, 26, pal["ink"], bold=True, valign="middle", font=pal["font"]),
        hline(MARGIN, 104, W - 2 * MARGIN, pal["line"], 1),
    ]


def footer(pal, page):
    return [
        rect(0, 530, W, 10, pal["primary"]),
        txt(str(page), W - 100, 502, 50, 20, 11, pal["muted"], align="right", font=pal["font"]),
    ]


# ----- layouts -----

def title_layout(spec, pal):
    els = [
        rect(MARGIN, 150, 14, 150, pal["primary"]),
        txt(spec.get("title", "Untitled"), MARGIN + 30, 170, 800, 110, 46, pal["ink"], bold=True, font=pal["font"]),
    ]
    if spec.get("subtitle"):
        els.append(txt(spec["subtitle"], MARGIN + 32, 300, 760, 50, 22, pal["muted"], font=pal["font"]))
    els.append(hline(MARGIN + 32, 360, 360, pal["line"], 1))
    if spec.get("footer"):
        els.append(txt(spec["footer"], MARGIN, 480, 800, 24, 13, pal["muted"], font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def section_layout(spec, pal):
    color = spec.get("color") or pal["primary"]
    els = [
        txt(spec.get("index", ""), MARGIN, 130, 360, 160, 120, "#FFFFFF", bold=True, font=pal["font"]),
        rect(MARGIN + 4, 318, 84, 6, "#FFFFFF"),
        txt(spec.get("title", ""), MARGIN, 332, 840, 90, 40, "#FFFFFF", bold=True, font=pal["font"]),
    ]
    if spec.get("subtitle"):
        els.append(txt(spec["subtitle"], MARGIN, 420, 840, 40, 18, "#FFFFFF", font=pal["font"]))
    return _slide(els, background={"type": "solid", "color": color}, remark=spec.get("notes"))


def _normalize_points(points):
    out = []
    for p in points or []:
        if isinstance(p, dict):
            out.append((p.get("head", ""), p.get("body", "")))
        else:
            out.append((str(p), ""))
    return out


def bullets_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    points = _normalize_points(spec.get("points") or spec.get("bullets"))
    n = max(1, len(points))
    top0, area = 132, 360
    step = min(82, area / n)
    for i, (head, body) in enumerate(points):
        y = top0 + i * step
        c = pal["accents"][i % len(pal["accents"])]
        els.append(rect(MARGIN + 4, int(y + 4), 16, 16, c, shape="roundRect"))
        els.append(txt(head, MARGIN + 32, int(y), 800, 28, 18, pal["ink"], bold=True, valign="middle", font=pal["font"]))
        if body:
            els.append(txt(body, MARGIN + 32, int(y + 26), 800, 30, 14, pal["muted"], font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def agenda_layout(spec, pal):
    els = header(spec.get("title", "议程"), pal)
    items = spec.get("items") or []
    n = max(1, len(items))
    top0, area = 132, 360
    step = min(72, area / n)
    for i, it in enumerate(items):
        y = top0 + i * step
        c = pal["accents"][i % len(pal["accents"])]
        els.append(txt(f"{i + 1:02d}", MARGIN, int(y), 64, 40, 30, c, bold=True, valign="middle", font=pal["font"]))
        els.append(txt(str(it), MARGIN + 78, int(y), 760, 40, 18, pal["ink"], valign="middle", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def _panel_with_text(left, top, w, h, fill, ink, heading, body, pal, heading_color=None):
    out = [rect(left, top, w, h, fill, shape="roundRect")]
    pad = 22
    if heading:
        out.append(txt(heading, left + pad, top + pad, w - 2 * pad, 30, 18, heading_color or ink, bold=True, font=pal["font"]))
    if body:
        out.append(txt(body, left + pad, top + (56 if heading else pad), w - 2 * pad, h - 80, 14, ink, font=pal["font"]))
    return out


def two_column_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    left = spec.get("left", {})
    right = spec.get("right", {})
    cy, ch = 132, 350
    els += _panel_with_text(MARGIN, cy, 396, ch, pal["primary"], "#FFFFFF",
                            left.get("title", ""), left.get("body", ""), pal, heading_color="#FFFFFF")
    els += _panel_with_text(MARGIN + 420, cy, 396, ch, pal["panel"], pal["ink"],
                            right.get("title", ""), right.get("body", ""), pal, heading_color=pal["primary"])
    return _slide(els, remark=spec.get("notes"))


def cards_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    cards = spec.get("cards", [])
    n = max(1, len(cards))
    cols = n if n <= 3 else 2
    rows = (n + cols - 1) // cols
    gap = 22
    area_w, area_h = W - 2 * MARGIN, 350
    cw = (area_w - (cols - 1) * gap) / cols
    chh = (area_h - (rows - 1) * gap) / rows
    for i, card in enumerate(cards):
        r, c = divmod(i, cols)
        x = MARGIN + c * (cw + gap)
        y = 132 + r * (chh + gap)
        color = pal["accents"][i % len(pal["accents"])]
        els.append(rect(int(x), int(y), int(cw), int(chh), pal["light"], shape="roundRect"))
        els.append(rect(int(x), int(y), int(cw), 6, color, shape="roundRect"))
        els.append(rect(int(x) + 22, int(y) + 24, 34, 34, color, shape="roundRect"))
        els.append(txt(card.get("tag", str(i + 1)), int(x) + 22, int(y) + 24, 34, 34, 16, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(card.get("title", ""), int(x) + 22, int(y) + 70, int(cw) - 44, 28, 17, pal["ink"], bold=True, font=pal["font"]))
        els.append(txt(card.get("body", ""), int(x) + 22, int(y) + 102, int(cw) - 44, int(chh) - 120, 13, pal["muted"], font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def kpi_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    stats = spec.get("stats", [])
    n = max(1, len(stats))
    area_w = W - 2 * MARGIN
    cw = area_w / n
    cy = 200
    for i, st in enumerate(stats):
        x = MARGIN + i * cw
        color = pal["accents"][i % len(pal["accents"])]
        if i > 0:
            els.append(vline(int(x), cy, 120, pal["line"], 1))
        els.append(txt(st.get("value", ""), int(x), cy, int(cw), 80, 52, color, bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(st.get("label", ""), int(x), cy + 90, int(cw), 40, 15, pal["muted"], align="center", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def chart_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    els.append({
        "id": new_id(), "type": "chart",
        "left": MARGIN, "top": 130, "width": W - 2 * MARGIN, "height": 350,
        "chartType": spec.get("chartType", "bar"),
        "data": {"labels": spec.get("labels", []), "series": spec.get("series", [])},
        "themeColors": pal["accents"],
    })
    return _slide(els, remark=spec.get("notes"))


def comparison_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    cy, ch = 132, 350
    for side, x0, color in (("left", MARGIN, pal["primary"]), ("right", MARGIN + 420, pal["secondary"])):
        data = spec.get(side, {})
        els.append(rect(x0, cy, 396, ch, pal["light"], shape="roundRect"))
        els.append(rect(x0, cy, 396, 44, color, shape="roundRect"))
        els.append(txt(data.get("title", ""), x0 + 22, cy, 352, 44, 18, "#FFFFFF", bold=True, valign="middle", font=pal["font"]))
        items = data.get("items", [])
        for j, it in enumerate(items[:6]):
            y = cy + 60 + j * 44
            els.append(rect(x0 + 22, y + 6, 10, 10, color, shape="roundRect"))
            els.append(txt(str(it), x0 + 44, y, 332, 36, 14, pal["ink"], valign="middle", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def quote_layout(spec, pal):
    color = spec.get("color") or pal["secondary"]
    els = [
        txt("“", MARGIN, 90, 200, 120, 120, "#FFFFFF", bold=True, font=pal["font"]),
        txt(spec.get("text", ""), MARGIN + 40, 210, W - 2 * MARGIN - 40, 180, 30, "#FFFFFF", italic=True, font=pal["font"]),
    ]
    if spec.get("author"):
        els.append(txt(f"— {spec['author']}", MARGIN + 42, 410, 700, 36, 18, "#FFFFFF", font=pal["font"]))
    return _slide(els, background={"type": "solid", "color": color}, remark=spec.get("notes"))


def closing_layout(spec, pal):
    color = spec.get("color") or pal["primary"]
    els = [
        txt(spec.get("title", "Thank You"), 0, 210, W, 90, 54, "#FFFFFF", bold=True, align="center", font=pal["font"]),
    ]
    if spec.get("subtitle"):
        els.append(txt(spec["subtitle"], 0, 310, W, 40, 20, "#FFFFFF", align="center", font=pal["font"]))
    return _slide(els, background={"type": "solid", "color": color}, remark=spec.get("notes"))


LAYOUTS = {
    "title": title_layout,
    "section": section_layout,
    "bullets": bullets_layout,
    "agenda": agenda_layout,
    "two_column": two_column_layout,
    "cards": cards_layout,
    "kpi": kpi_layout,
    "chart": chart_layout,
    "comparison": comparison_layout,
    "quote": quote_layout,
    "closing": closing_layout,
}

CONTENT_LAYOUTS = {"bullets", "agenda", "two_column", "cards", "kpi", "chart", "comparison"}
