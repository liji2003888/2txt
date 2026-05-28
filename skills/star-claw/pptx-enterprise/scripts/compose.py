#!/usr/bin/env python3
"""Auto-layout engine: turn a model-authored layout TREE into positioned slide elements.

The model composes a tree of containers (row/col/grid) + components (card/stat/panel/
iconitem/bullets/text/chart/image). This engine flows them (flexbox-style) within the
content area, computing geometry so nothing overlaps — the model decides structure, the
engine decides pixels. Output elements feed the existing renderers (native editable pptx).
"""
from layouts import txt, rect, card, icon_img, accent_for, _text_w, new_id, W, H, MARGIN, palette

PAD = 18  # inner padding for panels/cards


def _lerp_hex(c1, c2, t):
    a = c1.lstrip("#"); b = c2.lstrip("#")
    if len(a) != 6 or len(b) != 6:
        return c2
    ch = lambda i: round(int(a[i:i + 2], 16) + (int(b[i:i + 2], 16) - int(a[i:i + 2], 16)) * t)
    return f"#{ch(0):02X}{ch(2):02X}{ch(4):02X}"


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
    if t == "hero":
        return 80 + (28 if node.get("kicker") else 0) + (24 if node.get("label") else 0)
    if t == "quote":
        return PAD * 2 + _text_h(node.get("text", ""), w - 2 * PAD - 48, 22) + (26 if node.get("author") else 0) + 12
    if t == "timeline":
        return 132
    if t in ("arrowflow", "steps"):
        return 100
    if t == "quadrant":
        return node.get("h", 300)
    if t == "funnel":
        return max(200, 44 * len(node.get("items", [])) + 20)
    if t == "gauge":
        return node.get("h", 200)
    if t == "balance":
        return node.get("h", 280)
    if t in ("radar",):
        return node.get("h", 280)
    if t == "heatmap":
        return 40 + 34 * len(node.get("rows", [])) + 10
    if t == "imagecard":
        return node.get("h", 260)
    if t == "personcard":
        return max(150, PAD * 2 + _text_h(node.get("quote", ""), w - 120, 15) + 40)
    if t == "regions":
        return 30 * len(node.get("items", [])) + 10
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
    elif t == "hero":
        accent = accent_for(pal, node.get("_i", 0), node)
        cy = y
        if node.get("kicker"):
            els.append(txt(node["kicker"], x, cy, w, 24, 14, pal["muted"], bold=True, align=node.get("align", "left"), font=pal["font"]))
            cy += 28
        els.append(txt(str(node.get("value", "")), x, cy, w, 72, node.get("size", 60), accent, bold=True, align=node.get("align", "left"), valign="middle", font=pal["font"]))
        cy += 76
        if node.get("label"):
            els.append(txt(node["label"], x, cy, w, 24, 15, pal["ink"], align=node.get("align", "left"), font=pal["font"]))
    elif t == "quote":
        tone = node.get("tone", "light")
        dark = tone in ("blue", "navy")
        fill = _tone_fill(tone, pal)
        accent = accent_for(pal, node.get("_i", 0), node)
        els.append(card(x, y, w, h, fill))
        els.append(txt("“", x + PAD, y + 2, 44, 50, 52, (accent if not dark else "#FFFFFF"), bold=True, font=pal["font"]))
        ink = "#FFFFFF" if dark else pal["ink"]
        els.append(txt(node.get("text", ""), x + PAD + 44, y + PAD, w - 2 * PAD - 52, h - 2 * PAD - (24 if node.get("author") else 0), 18, ink, italic=True, valign="middle", font=pal["font"]))
        if node.get("author"):
            els.append(txt("— " + node["author"], x + PAD + 44, y + h - PAD - 22, w - 2 * PAD - 52, 22, 13, (pal["muted"] if not dark else "#C8D2DF"), align="right", font=pal["font"]))
    elif t == "timeline":
        items = node.get("items", [])
        n = max(1, len(items))
        ly = y + h / 2
        els.append(rect(x, int(ly) - 1, w, 3, pal["line"]))
        step = w / n
        for i, it in enumerate(items):
            it = it if isinstance(it, dict) else {"title": str(it)}
            cx = x + step * i + step / 2
            accent = accent_for(pal, i, it)
            if it.get("date"):
                els.append(txt(it["date"], int(cx - step / 2) + 6, int(ly) - 52, int(step) - 12, 24, 14, accent, bold=True, align="center", font=pal["font"]))
            els.append(rect(int(cx) - 9, int(ly) - 9, 18, 18, accent, shape="ellipse"))
            els.append(txt(it.get("title", ""), int(cx - step / 2) + 6, int(ly) + 16, int(step) - 12, 40, 13, pal["ink"], bold=True, align="center", font=pal["font"]))
    elif t in ("arrowflow", "steps"):
        items = node.get("items", [])
        n = max(1, len(items))
        arrow = 26
        nw = (w - arrow * (n - 1)) / n
        for i, it in enumerate(items):
            it = it if isinstance(it, dict) else {"title": str(it)}
            nx = x + i * (nw + arrow)
            accent = accent_for(pal, i, it)
            els.append(rect(int(nx), y, int(nw), h, accent, shape="roundRect"))
            els.append(txt(it.get("title", ""), int(nx) + 12, y + (10 if it.get("sub") else 0), int(nw) - 24, h - (28 if it.get("sub") else 0), 15, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
            if it.get("sub"):
                els.append(txt(it["sub"], int(nx) + 12, y + h - 30, int(nw) - 24, 24, 11, "#DCE8F7", align="center", font=pal["font"]))
            if i < n - 1:
                els.append(txt("➜", int(nx + nw), y, arrow, h, 18, pal["muted"], bold=True, align="center", valign="middle", font=pal["font"]))
    elif t == "quadrant":
        # SWOT / 四象限: 2x2 cells, each a shadowed card with colored header + bullets
        cells = node.get("items", [])[:4]
        gap = 16
        cw = (w - gap) / 2
        ch = (h - gap) / 2
        for i in range(4):
            c = cells[i] if i < len(cells) else {}
            r, col = divmod(i, 2)
            cx = x + col * (cw + gap)
            cyy = y + r * (ch + gap)
            accent = accent_for(pal, i, c)
            els.append(card(int(cx), int(cyy), int(cw), int(ch), pal["light"]))
            els.append(rect(int(cx), int(cyy), int(cw), 40, accent, shape="roundRect"))
            els.append(txt(c.get("title", ""), int(cx) + PAD, int(cyy), int(cw) - 2 * PAD, 40, 15, "#FFFFFF", bold=True, valign="middle", font=pal["font"]))
            iy = int(cyy) + 40 + 12
            for it in (c.get("items", [])[:4]):
                els.append(rect(int(cx) + PAD, iy + 7, 7, 7, accent, shape="ellipse"))
                els.append(txt(str(it), int(cx) + PAD + 16, iy, int(cw) - 2 * PAD - 20, 24, 12.5, pal["ink"], valign="middle", font=pal["font"]))
                iy += 28
    elif t == "funnel":
        stages = node.get("items", [])
        n = max(1, len(stages))
        gap = 8
        bh = (h - gap * (n - 1)) / n
        maxw, minw = w, w * 0.42
        for i, st in enumerate(stages):
            st = st if isinstance(st, dict) else {"label": str(st)}
            frac = 1 - (i / (n - 1) if n > 1 else 0)
            bw = minw + (maxw - minw) * frac
            bx = x + (w - bw) / 2
            by = y + i * (bh + gap)
            accent = accent_for(pal, i, st)
            els.append(rect(int(bx), int(by), int(bw), int(bh), accent, shape="trapezoid" if i < n - 1 else "roundRect", shadow=True))
            lab = st.get("label", "")
            if st.get("value"):
                lab = f"{lab}  ·  {st['value']}"
            els.append(txt(lab, int(bx), int(by), int(bw), int(bh), 15, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
    elif t == "gauge":
        els.append({"id": new_id(), "type": "chart", "left": x, "top": y, "width": w, "height": h,
                    "chartType": "gauge", "data": {"labels": [node.get("label", "")], "series": [{"name": "", "values": [node.get("value", 0)]}]},
                    "themeColors": [accent_for(pal, node.get("_i", 0), node)] + pal["accents"]})
    elif t == "balance":
        # 对比天平: a beam + fulcrum + two pans (left vs right)
        left = node.get("left", {})
        right = node.get("right", {})
        beam_y = y + 30
        els.append(rect(x + 40, beam_y, w - 80, 8, pal["primary"], shape="roundRect"))
        # fulcrum triangle at center
        els.append({"id": new_id(), "type": "shape", "shapeType": "triangle", "left": int(x + w / 2 - 26), "top": beam_y + 8, "width": 52, "height": 40, "fill": pal["navy"]})
        els.append(txt("VS", int(x + w / 2 - 26), beam_y + 14, 52, 30, 15, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        pan_w = (w - 120) / 2
        pan_y = beam_y + 70
        pan_h = y + h - pan_y - 6
        for side, px, data in (("L", x + 20, left), ("R", x + w - 20 - pan_w, right)):
            accent = pal["primary"] if side == "L" else pal["navy"]
            els.append(rect(int(px + (pan_w / 2) - 1), beam_y + 4, 2, 66, pal["line"]))
            els.append(card(int(px), int(pan_y), int(pan_w), int(pan_h), pal["light"]))
            els.append(rect(int(px), int(pan_y), int(pan_w), 40, accent, shape="roundRect"))
            els.append(txt(data.get("title", ""), int(px) + PAD, int(pan_y), int(pan_w) - 2 * PAD, 40, 15, "#FFFFFF", bold=True, valign="middle", font=pal["font"]))
            iy = int(pan_y) + 52
            for it in data.get("items", [])[:5]:
                els.append(rect(int(px) + PAD, iy + 7, 7, 7, accent, shape="ellipse"))
                els.append(txt(str(it), int(px) + PAD + 16, iy, int(pan_w) - 2 * PAD - 20, 24, 12.5, pal["ink"], valign="middle", font=pal["font"]))
                iy += 28
    elif t == "radar":
        els.append({"id": new_id(), "type": "chart", "left": x, "top": y, "width": w, "height": h,
                    "chartType": "radar", "data": {"labels": node.get("labels", []), "series": node.get("series", [])},
                    "themeColors": pal["accents"]})
    elif t == "heatmap":
        cols = node.get("cols", [])
        rows = node.get("rows", [])
        nc = max(1, len(cols))
        label_w = 110
        cellw = (w - label_w) / nc
        rh = 30
        hy = y + 34
        for j, cl in enumerate(cols):
            els.append(txt(str(cl), int(x + label_w + j * cellw), y, int(cellw), 30, 12, pal["ink"], bold=True, align="center", valign="middle", font=pal["font"]))
        for i, row in enumerate(rows):
            row = row if isinstance(row, dict) else {"label": str(row), "values": []}
            ry = hy + i * (rh + 2)
            els.append(txt(row.get("label", ""), int(x), int(ry), label_w - 8, rh, 12, pal["ink"], valign="middle", font=pal["font"]))
            for j, v in enumerate(row.get("values", [])[:nc]):
                frac = max(0.0, min(1.0, float(v) / 100.0))
                cellc = _lerp_hex("#EAF1FB", pal["primary"], frac)
                cx = x + label_w + j * cellw
                els.append(rect(int(cx) + 2, int(ry) + 1, int(cellw) - 4, rh - 2, cellc, shape="roundRect"))
                els.append(txt(str(v), int(cx) + 2, int(ry) + 1, int(cellw) - 4, rh - 2, 11, ("#FFFFFF" if frac > 0.5 else pal["ink"]), align="center", valign="middle", font=pal["font"]))
    elif t == "imagecard":
        accent = accent_for(pal, node.get("_i", 0), node)
        els.append(card(x, y, w, h, "#FFFFFF"))
        ih = int(h * 0.52)
        if node.get("src"):
            els.append({"id": new_id(), "type": "image", "left": x, "top": y, "width": w, "height": ih, "src": node["src"], "fixedRatio": False})
        else:
            els.append(rect(x, y, w, ih, pal["panel"], shape="roundRect"))
            els.append(txt("[image]", x, y, w, ih, 13, pal["muted"], align="center", valign="middle", font=pal["font"]))
        els.append(rect(x, y + ih, 46, 4, accent))
        els.append(txt(node.get("title", ""), x + PAD, y + ih + 12, w - 2 * PAD, 26, 16, pal["ink"], bold=True, font=pal["font"]))
        if node.get("body"):
            els.append(txt(node["body"], x + PAD, y + ih + 42, w - 2 * PAD, h - ih - 52, 12.5, pal["muted"], font=pal["font"]))
    elif t == "personcard":
        accent = accent_for(pal, node.get("_i", 0), node)
        els.append(card(x, y, w, h, pal["light"]))
        av = y + PAD
        ax = x + PAD
        if node.get("avatar"):
            els.append({"id": new_id(), "type": "image", "left": ax, "top": av, "width": 64, "height": 64, "src": node["avatar"], "fixedRatio": True})
        else:
            els.append(rect(ax, av, 64, 64, accent, shape="ellipse"))
            nm = node.get("name", "")
            els.append(txt(nm[:1] if nm else "", ax, av, 64, 64, 26, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        tx = ax + 84
        els.append(txt(node.get("quote", ""), tx, y + PAD, x + w - tx - PAD, h - 2 * PAD - 26, 15, pal["ink"], italic=True, font=pal["font"]))
        els.append(txt((node.get("name", "") + ("  ·  " + node["role"] if node.get("role") else "")), tx, y + h - PAD - 22, x + w - tx - PAD, 22, 13, accent, bold=True, font=pal["font"]))
    elif t == "regions":
        items = node.get("items", [])
        items = sorted(items, key=lambda r: (r.get("value", 0) if isinstance(r, dict) else 0), reverse=True)
        mx = max((r.get("value", 0) for r in items if isinstance(r, dict)), default=1) or 1
        label_w = 96
        bar_max = w - label_w - 80
        rh = 30
        for i, r in enumerate(items):
            r = r if isinstance(r, dict) else {"name": str(r), "value": 0}
            ry = y + i * rh
            accent = accent_for(pal, i, r)
            els.append(txt(r.get("name", ""), x, ry, label_w - 8, rh - 6, 13, pal["ink"], valign="middle", font=pal["font"]))
            bw = bar_max * (r.get("value", 0) / mx)
            els.append(rect(x + label_w, ry + 4, max(4, int(bw)), rh - 12, accent, shape="roundRect"))
            els.append(txt(str(r.get("value", "")), x + label_w + int(bw) + 8, ry, 72, rh - 6, 12, pal["muted"], valign="middle", font=pal["font"]))
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
