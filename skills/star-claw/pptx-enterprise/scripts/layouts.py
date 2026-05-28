#!/usr/bin/env python3
"""Designed slide layouts: compose shapes + text + accents into professional slides (not bullet dumps)."""
import html as _html
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

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
        "ink": theme.get("fontColor") or theme.get("ink") or "#111111",
        "muted": theme.get("muted") or "#5B6470",
        "light": theme.get("light") or "#F4F6F9",
        "panel": theme.get("panel") or "#EEF2F7",
        "line": theme.get("line") or "#E2E6EC",
        "font": theme.get("fontName") or theme.get("font") or "",
        "bg": theme.get("backgroundColor") or theme.get("bg") or "#FFFFFF",
        "badge": bool(theme.get("badgeColor")),
        "red": theme.get("badgeColor") or "#E60012",
        "cover": theme.get("coverImage"),
        "coverDeco": theme.get("coverDeco"),
        "coverWordmark": theme.get("coverWordmark"),
    }


def _asset(path):
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = _ROOT / p
    return str(p) if p.exists() else None


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


def _text_w(s, size):
    w = 0
    for ch in str(s):
        w += size * (0.95 if ord(ch) > 0x2E80 else 0.55)
    return w


def header(title, pal):
    els = []
    if pal.get("badge"):
        red = pal["red"]
        els.append(txt(title, 84, 40, 760, 44, 26, red, bold=True, valign="middle", font=pal["font"]))
        uw = min(_text_w(title, 26) + 10, 800)
        els.append(rect(84, 92, int(uw), 5, red))
    else:
        els.append(rect(MARGIN, 54, 8, 36, pal["primary"]))
        els.append(txt(title, MARGIN + 20, 50, 700, 44, 26, pal["ink"], bold=True, valign="middle", font=pal["font"]))
        els.append(hline(MARGIN, 104, W - 2 * MARGIN, pal["line"], 1))
    return els


def logo_elements(theme: dict):
    raw = theme.get("logo")
    if not raw:
        return []
    p = Path(raw)
    if not p.is_absolute():
        p = _ROOT / p
    if not p.exists():
        return []
    w = theme.get("logoWidth", 140)
    h = theme.get("logoHeight", round(w * 489 / 1928))
    return [{
        "id": new_id(), "type": "image", "src": str(p),
        "left": W - w - 24, "top": 18, "width": w, "height": h, "fixedRatio": True,
    }]


def icon_img(ref, color, left, top, w, h):
    # ref like "lucide/calendar" or "icon-park/people"; resolved to a recolored PNG by outline_to_schema.
    return {
        "id": new_id(), "type": "image", "src": f"icon:{ref}", "iconColor": color,
        "left": int(left), "top": int(top), "width": int(w), "height": int(h), "fixedRatio": True,
    }


def chrome_elements(theme: dict):
    # Persistent brand chrome: left red corner badge + right logo, on every light slide.
    # Tagged role='chrome' so the template renderer can skip them (the master layout provides them).
    els = []
    bc = theme.get("badgeColor")
    if bc:
        els.append(rect(0, 0, 56, 58, bc))
    els.extend(logo_elements(theme))
    for e in els:
        e["role"] = "chrome"
    return els


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
        if card.get("icon"):
            els.append(icon_img(card["icon"], "#FFFFFF", int(x) + 28, int(y) + 30, 22, 22))
        else:
            els.append(txt(card.get("tag", str(i + 1)), int(x) + 22, int(y) + 24, 34, 34, 16, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(card.get("title", ""), int(x) + 22, int(y) + 70, int(cw) - 44, 28, 17, pal["ink"], bold=True, font=pal["font"]))
        els.append(txt(card.get("body", ""), int(x) + 22, int(y) + 102, int(cw) - 44, int(chh) - 120, 13, pal["muted"], font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def kpi_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    stats = spec.get("stats", [])
    n = max(1, len(stats))
    cw = (W - 2 * MARGIN) / n
    cy = 186
    for i, st in enumerate(stats):
        x = MARGIN + i * cw
        color = pal["accents"][i % len(pal["accents"])]
        if i > 0:
            els.append(vline(int(x), cy, 150, pal["line"], 1))
        els.append(txt(st.get("value", ""), int(x), cy, int(cw), 78, 52, color, bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(st.get("label", ""), int(x), cy + 86, int(cw), 30, 15, pal["ink"], bold=True, align="center", font=pal["font"]))
        if st.get("note"):
            els.append(txt(st["note"], int(x) + 16, cy + 120, int(cw) - 32, 50, 12, pal["muted"], align="center", font=pal["font"]))
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


def process_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    steps = spec.get("steps", [])
    n = max(1, len(steps))
    gap = 16
    sw = (W - 2 * MARGIN - (n - 1) * gap) / n
    cy = 200
    for i, st in enumerate(steps):
        x = MARGIN + i * (sw + gap)
        color = pal["accents"][i % len(pal["accents"])]
        els.append(rect(int(x + sw / 2 - 28), cy, 56, 56, color, shape="ellipse"))
        if st.get("icon"):
            els.append(icon_img(st["icon"], "#FFFFFF", int(x + sw / 2 - 15), cy + 13, 30, 30))
        else:
            els.append(txt(str(i + 1), int(x + sw / 2 - 28), cy, 56, 56, 24, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(st.get("title", ""), int(x), cy + 70, int(sw), 28, 16, pal["ink"], bold=True, align="center", font=pal["font"]))
        els.append(txt(st.get("body", ""), int(x), cy + 100, int(sw), 80, 12, pal["muted"], align="center", font=pal["font"]))
        if i < n - 1:
            els.append(txt("→", int(x + sw - 6), cy + 8, int(gap + 12), 40, 22, pal["muted"], bold=True, align="center", valign="middle", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def timeline_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    items = spec.get("items", [])
    n = max(1, len(items))
    cy = 268
    els.append(hline(MARGIN, cy, W - 2 * MARGIN, pal["line"], 2))
    step = (W - 2 * MARGIN) / n
    for i, it in enumerate(items):
        cx = MARGIN + i * step + step / 2
        color = pal["accents"][i % len(pal["accents"])]
        els.append(rect(int(cx - 9), cy - 9, 18, 18, color, shape="ellipse"))
        els.append(txt(it.get("date", ""), int(cx - step / 2) + 8, cy - 74, int(step) - 16, 24, 14, color, bold=True, align="center", font=pal["font"]))
        els.append(txt(it.get("title", ""), int(cx - step / 2) + 8, cy + 22, int(step) - 16, 26, 15, pal["ink"], bold=True, align="center", font=pal["font"]))
        els.append(txt(it.get("body", ""), int(cx - step / 2) + 8, cy + 50, int(step) - 16, 70, 12, pal["muted"], align="center", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def statement_layout(spec, pal):
    els = [
        rect(MARGIN, 220, 80, 8, pal["primary"]),
        txt(spec.get("text", ""), MARGIN, 250, W - 2 * MARGIN, 160, 38, pal["ink"], bold=True, valign="top", font=pal["font"]),
    ]
    if spec.get("subtitle"):
        els.append(txt(spec["subtitle"], MARGIN, 200, W - 2 * MARGIN, 30, 16, pal["primary"], bold=True, font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def table_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    columns = spec.get("columns", [])
    rows = spec.get("rows", [])
    data = [[{"text": str(c), "bold": True, "fill": pal["primary"], "color": "#FFFFFF"} for c in columns]]
    for r in rows:
        data.append([{"text": str(c)} for c in r])
    els.append({
        "id": new_id(), "type": "table",
        "left": MARGIN, "top": 132, "width": W - 2 * MARGIN, "height": 330,
        "data": data,
    })
    return _slide(els, remark=spec.get("notes"))


def image_text_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    side = spec.get("imageSide", "left")
    img_x = MARGIN if side == "left" else MARGIN + 440
    txt_x = MARGIN + 440 if side == "left" else MARGIN
    if spec.get("image"):
        els.append({"id": new_id(), "type": "image", "src": spec["image"], "left": img_x, "top": 132, "width": 376, "height": 330, "fixedRatio": True})
    else:
        els.append(rect(img_x, 132, 376, 330, pal["panel"], shape="roundRect"))
        els.append(txt("[image]", img_x, 132, 376, 330, 16, pal["muted"], align="center", valign="middle", font=pal["font"]))
    if spec.get("heading"):
        els.append(txt(spec["heading"], txt_x, 150, 376, 36, 22, pal["ink"], bold=True, font=pal["font"]))
    if spec.get("body"):
        els.append(txt(spec["body"], txt_x, 200, 376, 260, 15, pal["muted"], font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def matrix_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    cols = spec.get("columns", [])
    n = max(1, len(cols))
    gap = 14
    cw = (W - 2 * MARGIN - (n - 1) * gap) / n
    top, hh = 130, 44
    body_top = top + hh + 8
    body_h = 472 - body_top
    for i, c in enumerate(cols):
        x = MARGIN + i * (cw + gap)
        color = pal["accents"][i % len(pal["accents"])]
        els.append(rect(int(x), top, int(cw), hh, color, shape="roundRect"))
        if c.get("icon"):
            els.append(icon_img(c["icon"], "#FFFFFF", int(x) + 14, top + (hh - 20) // 2, 20, 20))
        els.append(txt(c.get("header", ""), int(x), top, int(cw), hh, 15, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(rect(int(x), body_top, int(cw), int(body_h), pal["light"], shape="roundRect"))
        items = (c.get("items") or [])[:6]
        m = max(1, len(items))
        for j, it in enumerate(items):
            iy = body_top + 16 + j * ((body_h - 26) / m)
            els.append(rect(int(x) + 16, int(iy) + 7, 6, 6, color, shape="ellipse"))
            els.append(txt(str(it), int(x) + 30, int(iy), int(cw) - 44, 24, 12.5, pal["ink"], valign="middle", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def hierarchy_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    cards = spec.get("cards", [])
    n = max(1, len(cards))
    rw, rh, ry = 200, 50, 128
    rx = (W - rw) / 2
    els.append(rect(int(rx), ry, rw, rh, pal["primary"], shape="roundRect"))
    els.append(txt(spec.get("root", "Main Idea"), int(rx), ry, rw, rh, 16, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
    gap, cy, ch = 18, 248, 206
    cw = (W - 2 * MARGIN - (n - 1) * gap) / n
    busy = ry + rh + 22
    first_cx = MARGIN + cw / 2
    els.append(vline(int(W / 2), int(ry + rh), int(busy - (ry + rh)), pal["line"], 1))
    if n > 1:
        els.append(hline(int(first_cx), int(busy), int((n - 1) * (cw + gap)), pal["line"], 1))
    for i, c in enumerate(cards):
        x = MARGIN + i * (cw + gap)
        cxp = x + cw / 2
        color = pal["accents"][i % len(pal["accents"])]
        els.append(vline(int(cxp), int(busy), int(cy - busy), pal["line"], 1))
        els.append(rect(int(x), cy, int(cw), ch, pal["light"], shape="roundRect"))
        els.append(rect(int(x), cy, int(cw), 40, color, shape="roundRect"))
        els.append(txt(c.get("title", ""), int(x), cy, int(cw), 40, 15, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(rect(int(cxp - 22), cy + 54, 44, 44, color, shape="ellipse"))
        if c.get("icon"):
            els.append(icon_img(c["icon"], "#FFFFFF", int(cxp - 12), cy + 64, 24, 24))
        else:
            els.append(txt(c.get("tag", str(i + 1)), int(cxp - 22), cy + 54, 44, 44, 18, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(c.get("body", ""), int(x) + 16, cy + 106, int(cw) - 32, ch - 116, 12, pal["muted"], align="center", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def circles_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    items = (spec.get("items") or [])[:3]
    d = 170
    centers = [(480, 208), (408, 332), (552, 332)]
    texts = [(60, 156, 312, "right"), (44, 366, 286, "right"), (636, 332, 286, "left")]
    for i, it in enumerate(items):
        cx, cy = centers[i]
        color = pal["accents"][i % len(pal["accents"])]
        els.append(rect(int(cx - d / 2), int(cy - d / 2), d, d, color, shape="ellipse"))
        if it.get("icon"):
            els.append(icon_img(it["icon"], "#FFFFFF", int(cx - 32), int(cy - 32), 64, 64))
        else:
            els.append(txt(it.get("tag", f"{i + 1:02d}"), int(cx - d / 2), int(cy - d / 2), d, d, 26, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        tx, ty, tw, al = texts[i]
        els.append(txt(it.get("title", ""), tx, ty, tw, 28, 17, color, bold=True, align=al, font=pal["font"]))
        els.append(txt(it.get("body", ""), tx, ty + 30, tw, 110, 13, pal["muted"], align=al, font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def pyramid_layout(spec, pal):
    els = header(spec.get("title", ""), pal)
    levels = spec.get("levels", [])
    n = max(1, len(levels))
    top, bottom, gap = 122, 500, 14
    band_h = (bottom - top - (n - 1) * gap) / n
    maxw, minw = W - 2 * MARGIN, (W - 2 * MARGIN) * 0.46
    inverted = spec.get("inverted", False)
    for i, lv in enumerate(levels):
        frac = i / (n - 1) if n > 1 else 1.0
        if inverted:
            frac = 1 - frac
        w = minw + (maxw - minw) * frac
        x = (W - w) / 2
        y = top + i * (band_h + gap)
        color = pal["accents"][i % len(pal["accents"])]
        label = lv.get("label", "") if isinstance(lv, dict) else str(lv)
        note = lv.get("note", "") if isinstance(lv, dict) else ""
        els.append(rect(int(x), int(y), int(w), int(band_h), color, shape="roundRect"))
        if note:
            els.append(txt(label, int(x), int(y + band_h / 2 - 25), int(w), 28, 18, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
            els.append(txt(note, int(x) + 20, int(y + band_h / 2 + 5), int(w) - 40, 22, 12, "#EAF2FF", align="center", valign="middle", font=pal["font"]))
        else:
            els.append(txt(label, int(x), int(y), int(w), int(band_h), 18, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
    return _slide(els, remark=spec.get("notes"))


def cover_layout(spec, pal):
    red = pal["red"]
    p = _asset(pal.get("cover"))
    els = []
    if p:
        # Clean cover background image (red shape + photo); overlay only the editable fields.
        # bg/deco tagged role='coverbg' so the template renderer skips them (the '空白' master layout provides them).
        els.append({"id": new_id(), "type": "image", "src": p, "left": 0, "top": 0, "width": W, "height": H, "role": "coverbg"})
        deco = _asset(pal.get("coverDeco"))
        if deco:
            els.append({"id": new_id(), "type": "image", "src": deco, "left": 746, "top": 5, "width": 197, "height": 161, "fixedRatio": True, "role": "coverbg"})
        wm = _asset(pal.get("coverWordmark"))
        if wm:
            els.append({"id": new_id(), "type": "image", "src": wm, "left": 29, "top": 140, "width": 302, "height": 49, "fixedRatio": True})
        meta = spec.get("meta")
        if meta is None:
            meta = [
                "文档编号：              保存年限：    年",
                "保密等级：□一般   ■秘密   □机密   □绝密",
                "报告归档：□DCC   □部门内   □中心内",
            ]
        if isinstance(meta, str):
            meta = [meta]
        for i, line in enumerate(meta):
            els.append(txt(line, 27, 18 + i * 18, 470, 18, 10, "#FFFFFF", font=pal["font"]))
        els.append(txt(spec.get("title", "材料标题"), 27, 218, 470, 70, 36, "#FFFFFF", font=pal["font"]))
        if spec.get("dept"):
            els.append(txt(spec["dept"], 32, 343, 440, 28, 20, "#FFFFFF", font=pal["font"]))
        if spec.get("author"):
            els.append(txt(spec["author"], 32, 373, 440, 28, 20, "#FFFFFF", font=pal["font"]))
        return _slide(els)
    # Fallback (no cover image yet): approximate TCL red cover — lacks the building photo.
    els.append(rect(0, 0, 560, H, red))
    if spec.get("meta"):
        els.append(txt(spec["meta"], 48, 38, 500, 24, 11, "#FFFFFF", font=pal["font"]))
    els.append(txt(spec.get("brand", "TCL 华星"), 48, 150, 480, 80, 46, "#FFFFFF", bold=True, font=pal["font"]))
    els.append(txt(spec.get("title", "材料标题"), 48, 258, 480, 70, 34, "#FFFFFF", bold=True, font=pal["font"]))
    if spec.get("dept"):
        els.append(txt(spec["dept"], 48, 404, 420, 34, 20, "#FFFFFF", font=pal["font"]))
    if spec.get("author"):
        els.append(txt(spec["author"], 48, 446, 420, 34, 20, "#FFFFFF", font=pal["font"]))
    return _slide(els)


LAYOUTS = {
    "title": title_layout,
    "cover": cover_layout,
    "section": section_layout,
    "bullets": bullets_layout,
    "agenda": agenda_layout,
    "two_column": two_column_layout,
    "cards": cards_layout,
    "kpi": kpi_layout,
    "chart": chart_layout,
    "comparison": comparison_layout,
    "process": process_layout,
    "timeline": timeline_layout,
    "matrix": matrix_layout,
    "hierarchy": hierarchy_layout,
    "circles": circles_layout,
    "pyramid": pyramid_layout,
    "statement": statement_layout,
    "table": table_layout,
    "image_text": image_text_layout,
    "quote": quote_layout,
    "closing": closing_layout,
}

CONTENT_LAYOUTS = {
    "bullets", "agenda", "two_column", "cards", "kpi", "chart", "comparison",
    "process", "timeline", "matrix", "hierarchy", "circles", "pyramid", "table", "image_text",
}
