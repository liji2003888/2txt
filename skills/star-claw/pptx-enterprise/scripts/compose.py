#!/usr/bin/env python3
"""Auto-layout engine: turn a model-authored layout TREE into positioned slide elements.

The model composes a tree of containers (row/col/grid) + components (card/stat/panel/
iconitem/bullets/text/chart/image). This engine flows them (flexbox-style) within the
content area, computing geometry so nothing overlaps — the model decides structure, the
engine decides pixels. Output elements feed the existing renderers (native editable pptx).
"""
from layouts import txt, rect, card, icon_img, accent_for, _text_w, new_id, W, H, MARGIN, palette

PAD = 18  # inner padding for panels/cards


def _wrap_lines(text, w, size):
    if not text:
        return 0
    lw, lines = 0.0, 1
    for ch in str(text):
        cw = size * (1.0 if ord(ch) > 0x2E80 else 0.55)
        if lw + cw > w and lw > 0:
            lines += 1
            lw = cw
        else:
            lw += cw
    return lines


def _text_h(text, w, size, lh=1.35):
    return _wrap_lines(text, w, size) * size * lh


# ---------- component natural heights (given a width) ----------

def measure(node, pal, w):
    t = node.get("type", "text")
    if t in ("row", "col", "grid"):
        return _measure_container(node, pal, w)
    if t == "card":
        h = PAD * 2 + 6
        if node.get("icon") or node.get("tag"):
            h += 44
        if node.get("title"):
            h += 26
        if node.get("body"):
            h += _text_h(node["body"], w - 2 * PAD, 13)
        return max(h, 96)
    if t == "stat":
        return 116
    if t == "panel":
        inner = node.get("items", [])
        ih = sum(measure(it, pal, w - 2 * PAD) + 10 for it in inner) if inner else 0
        return 48 + PAD + ih + PAD
    if t == "iconitem":
        bh = _text_h(node.get("body", ""), w - 64, 12) if node.get("body") else 0
        return max(48, 24 + bh)
    if t == "bullets":
        return sum(max(26, _text_h(str(b.get("text", b) if isinstance(b, dict) else b), w - 28, 14) + 8) for b in node.get("items", [])) or 26
    if t == "text":
        return _text_h(node.get("text", ""), w, node.get("size", 16)) + 6
    if t in ("chart", "image"):
        return node.get("h", 240)
    if t == "spacer":
        return node.get("h", 20)
    return 40


def _measure_container(node, pal, w):
    items = node.get("items", [])
    gap = node.get("gap", 16)
    if node["type"] == "row":
        sizes = node.get("sizes") or [1] * len(items)
        tot = sum(sizes) or 1
        inner_w = w - gap * (len(items) - 1)
        return max((measure(it, pal, inner_w * s / tot) for it, s in zip(items, sizes)), default=40)
    if node["type"] == "grid":
        cols = node.get("cols", 2)
        rows = (len(items) + cols - 1) // cols
        cw = (w - gap * (cols - 1)) / cols
        rowh = [max((measure(items[r * cols + c], pal, cw) for c in range(cols) if r * cols + c < len(items)), default=0) for r in range(rows)]
        return sum(rowh) + gap * (rows - 1)
    # col
    return sum(measure(it, pal, w) for it in items) + gap * (max(0, len(items) - 1))


# ---------- placement (emit elements) ----------

def place(node, pal, x, y, w, h, els):
    t = node.get("type", "text")
    if t == "row":
        items = node.get("items", [])
        gap = node.get("gap", 16)
        sizes = node.get("sizes") or [1] * len(items)
        tot = sum(sizes) or 1
        inner_w = w - gap * (len(items) - 1)
        cx = x
        for it, s in zip(items, sizes):
            cw = inner_w * s / tot
            place(it, pal, cx, y, cw, h, els)
            cx += cw + gap
    elif t == "col":
        items = node.get("items", [])
        gap = node.get("gap", 16)
        nat = [measure(it, pal, w) for it in items]
        avail = h - gap * (max(0, len(items) - 1))
        tot = sum(nat) or 1
        scale = min(1.0, avail / tot) if tot > avail else 1.0
        # if extra space, leave components at natural height (top-aligned)
        cy = y
        for it, nh in zip(items, nat):
            ph = nh * scale
            place(it, pal, x, cy, w, ph, els)
            cy += ph + gap
    elif t == "grid":
        items = node.get("items", [])
        gap = node.get("gap", 16)
        cols = node.get("cols", 2)
        rows = (len(items) + cols - 1) // cols
        cw = (w - gap * (cols - 1)) / cols
        ch = (h - gap * (rows - 1)) / rows
        for i, it in enumerate(items):
            r, c = divmod(i, cols)
            place(it, pal, x + c * (cw + gap), y + r * (ch + gap), cw, ch, els)
    else:
        _component(node, pal, x, y, w, h, els)


def _tone_fill(tone, pal):
    return {"light": pal["light"], "blue": pal["primary"], "navy": pal["navy"], "white": "#FFFFFF"}.get(tone, pal["light"])


def _component(node, pal, x, y, w, h, els):
    t = node.get("type", "text")
    x, y, w, h = int(x), int(y), int(w), int(h)
    if t == "card":
        accent = accent_for(pal, node.get("_i", 0), node)
        tone = node.get("tone", "white")
        fill = _tone_fill(tone, pal)
        dark = tone in ("blue", "navy")
        els.append(card(x, y, w, h, fill))
        els.append(rect(x, y, w, 5, accent, shape="roundRect"))
        ink = "#FFFFFF" if dark else pal["ink"]
        sub = "#DCE8F7" if dark else pal["muted"]
        cy = y + PAD + 6
        if node.get("icon"):
            els.append(rect(x + PAD, cy, 40, 40, accent, shape="roundRect"))
            els.append(icon_img(node["icon"], "#FFFFFF", x + PAD + 10, cy + 10, 20, 20))
            if node.get("metric"):
                mc = "#FFFFFF" if dark else accent
                els.append(txt(node["metric"], x + w - 120, cy, 104, 32, 19, mc, bold=True, align="right", font=pal["font"]))
            cy += 52
        elif node.get("tag"):
            els.append(txt(str(node["tag"]), x + PAD, cy, 40, 36, 24, accent, bold=True, font=pal["font"]))
            cy += 46
        if node.get("title"):
            els.append(txt(node["title"], x + PAD, cy, w - 2 * PAD, 26, 16, ink, bold=True, font=pal["font"]))
            cy += 28
        if node.get("body"):
            els.append(txt(node["body"], x + PAD, cy, w - 2 * PAD, h - (cy - y) - PAD, 13, sub, font=pal["font"]))
    elif t == "stat":
        accent = accent_for(pal, node.get("_i", 0), node)
        els.append(txt(node.get("value", ""), x, y + 10, w, 56, 44, accent, bold=True, align="center", valign="middle", font=pal["font"]))
        els.append(txt(node.get("label", ""), x, y + 70, w, 26, 15, pal["ink"], bold=True, align="center", font=pal["font"]))
        if node.get("note"):
            els.append(txt(node["note"], x, y + 96, w, 22, 12, pal["muted"], align="center", font=pal["font"]))
    elif t == "panel":
        accent = accent_for(pal, node.get("_i", 0), node)
        tone = node.get("tone")
        head = accent if tone != "navy" else pal["navy"]
        els.append(card(x, y, w, h, pal["light"]))
        els.append(rect(x, y, w, 44, head, shape="roundRect"))
        if node.get("title"):
            els.append(txt(node["title"], x + PAD, y, w - 2 * PAD, 44, 16, "#FFFFFF", bold=True, valign="middle", font=pal["font"]))
        inner = node.get("items", [])
        iy = y + 44 + PAD
        for k, it in enumerate(inner):
            it = dict(it) if isinstance(it, dict) else {"type": "text", "text": str(it)}
            it.setdefault("_i", k)
            ih = measure(it, pal, w - 2 * PAD)
            place(it, pal, x + PAD, iy, w - 2 * PAD, ih, els)
            iy += ih + 10
    elif t == "iconitem":
        accent = accent_for(pal, node.get("_i", 0), node)
        if node.get("icon"):
            els.append(rect(x, y + 2, 38, 38, accent, shape="roundRect"))
            els.append(icon_img(node["icon"], "#FFFFFF", x + 9, y + 11, 20, 20))
        tx = x + 50 if node.get("icon") else x
        els.append(txt(node.get("title", ""), tx, y, w - (tx - x), 24, 15, pal["ink"], bold=True, font=pal["font"]))
        if node.get("body"):
            els.append(txt(node["body"], tx, y + 22, w - (tx - x), h - 22, 12, pal["muted"], font=pal["font"]))
    elif t == "bullets":
        accent = accent_for(pal, node.get("_i", 0), node)
        cy = y
        for b in node.get("items", []):
            text = b.get("text", "") if isinstance(b, dict) else str(b)
            ih = max(26, _text_h(text, w - 28, 14) + 8)
            els.append(rect(x + 2, cy + 7, 8, 8, accent, shape="ellipse"))
            els.append(txt(text, x + 22, cy, w - 28, ih, 14, pal["ink"], valign="middle", font=pal["font"]))
            cy += ih
    elif t == "text":
        els.append(txt(node.get("text", ""), x, y, w, h, node.get("size", 16),
                       node.get("color") or pal["ink"], bold=node.get("bold", False),
                       align=node.get("align", "left"), font=pal["font"]))
    elif t == "chart":
        els.append({"id": new_id(), "type": "chart", "left": x, "top": y, "width": w, "height": h,
                    "chartType": node.get("chartType", "column"),
                    "data": {"labels": node.get("labels", []), "series": node.get("series", [])},
                    "themeColors": pal["accents"]})
    elif t == "image":
        els.append({"id": new_id(), "type": "image", "left": x, "top": y, "width": w, "height": h,
                    "src": node.get("src", ""), "fixedRatio": node.get("fixedRatio", True)})
    # spacer: nothing


def _tag_indices(node):
    """Give each direct child an _i for accent rotation."""
    items = node.get("items")
    if isinstance(items, list):
        for i, it in enumerate(items):
            if isinstance(it, dict):
                it.setdefault("_i", i)
                _tag_indices(it)


def compose_slide(spec, pal, content_box):
    """Place spec['body'] (a layout tree) within content_box=(x0,y0,x1,y1). Returns elements."""
    x0, y0, x1, y1 = content_box
    els = []
    body = spec.get("body")
    if not body:
        return els
    _tag_indices(body)
    place(body, pal, x0, y0, x1 - x0, y1 - y0, els)
    return els
