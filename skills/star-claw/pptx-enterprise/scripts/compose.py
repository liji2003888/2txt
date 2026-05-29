#!/usr/bin/env python3
"""Auto-layout engine: turn a model-authored layout TREE into positioned slide elements.

The model composes a tree of containers (row/col/grid) + components (card/stat/panel/
iconitem/bullets/text/chart/image). This engine flows them (flexbox-style) within the
content area, computing geometry so nothing overlaps — the model decides structure, the
engine decides pixels. Output elements feed the existing renderers (native editable pptx).
"""
from layouts import txt, rect, card, icon_img, accent_for, _text_w, new_id, W, H, MARGIN, palette

PAD = 18  # inner padding for panels/cards

# Common synonyms a model may invent → the canonical component this engine renders.
# This keeps weak/varied models from producing blank slides when they pick a reasonable
# but non-exact type name (the #1 cause of empty pages seen in the field).
ALIASES = {
    "list": "bullets", "bulletlist": "bullets", "bullet": "bullets", "points": "bullets", "ul": "bullets",
    "infobox": "card", "box": "card", "feature": "card", "featurecard": "card", "tile": "card",
    "statement": "hero", "definition": "hero", "keypoint": "hero", "headline": "hero", "bignumber": "hero",
    "process": "arrowflow", "flow": "arrowflow", "steps": "arrowflow", "stepflow": "arrowflow", "pipeline": "arrowflow",
    "comparison": "balance", "compare": "balance", "versus": "balance", "vs": "balance",
    "swot": "quadrant", "2x2": "quadrant", "fourquadrant": "quadrant",
    "metric": "stat", "kpi": "stat", "number": "stat", "bignum": "stat",
    "testimonial": "personcard", "person": "personcard", "voice": "personcard",
    "org": "orgchart", "hierarchy": "orgchart", "tree": "orgchart",
    "arch": "architecture", "stack": "architecture", "layered": "architecture",
    "ranking": "regions", "distribution": "regions", "rank": "regions",
    "progress": "progresslist", "progressbar": "progresslist", "bars": "progresslist",
    "picture": "image", "photo": "image", "img": "image",
    "paragraph": "text", "para": "text", "p": "text",
    "callout": "card", "note": "card",
    "graph": "chart", "barchart": "chart", "linechart": "chart",
}
# Every component type the engine knows how to draw (canonical names).
KNOWN_TYPES = {
    "row", "col", "grid", "card", "stat", "panel", "iconitem", "bullets", "text", "spacer",
    "chart", "image", "hero", "quote", "timeline", "arrowflow", "quadrant", "funnel", "gauge",
    "balance", "radar", "heatmap", "imagecard", "personcard", "regions", "progresslist",
    "pricing", "milestone", "orgchart", "architecture", "house", "roadmap",
}


def _normalize(node):
    """Recursively rewrite synonym type names to canonical ones so the engine renders them."""
    if not isinstance(node, dict):
        return node
    t = node.get("type")
    if isinstance(t, str) and t not in KNOWN_TYPES:
        node["type"] = ALIASES.get(t.lower().replace("-", "").replace("_", ""), t)
    for it in (node.get("items") if isinstance(node.get("items"), list) else []):
        _normalize(it)
    for key in ("left", "right", "root"):
        if isinstance(node.get(key), dict):
            _normalize(node[key])
    for key in ("children", "pillars", "layers", "plans", "phases"):
        for it in (node.get(key) if isinstance(node.get(key), list) else []):
            _normalize(it)
    return node


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
    if t == "progresslist":
        return 42 * len(node.get("items", [])) + 8
    if t == "pricing":
        return node.get("h", 320)
    if t == "milestone":
        return node.get("h", 240)
    if t == "roadmap":
        return node.get("h", 260)
    if t == "orgchart":
        return node.get("h", 300)
    if t == "architecture":
        return node.get("h", 300)
    if t == "house":
        return node.get("h", 320)
    if t == "spacer":
        return node.get("h", 20)
    return 40


def _measure_container(node, pal, w):
    items = node.get("items", [])
    gap = node.get("gap", 16)
    if not items:
        return 40
    if node["type"] == "row":
        sizes = node.get("sizes") or [1] * len(items)
        tot = sum(sizes) or 1
        inner_w = w - gap * (len(items) - 1)
        return max((measure(it, pal, inner_w * s / tot) for it, s in zip(items, sizes)), default=40)
    if node["type"] == "grid":
        cols = min(node.get("cols", 2), len(items))
        rows = (len(items) + cols - 1) // cols
        cw = (w - gap * (cols - 1)) / cols
        rowh = [max((measure(items[r * cols + c], pal, cw) for c in range(cols) if r * cols + c < len(items)), default=0) for r in range(rows)]
        return sum(rowh) + gap * (rows - 1)
    # col
    return sum(measure(it, pal, w) for it in items) + gap * (max(0, len(items) - 1))


# components that genuinely want to fill the available height (charts/diagrams/nested
# containers). Text/card/panel rows should instead size to content and center, so a
# sparse row doesn't render as a few tall, mostly-empty boxes.
FILL_HUNGRY = {
    "chart", "image", "imagecard", "gauge", "radar", "balance", "quadrant", "funnel",
    "orgchart", "architecture", "house", "roadmap", "milestone", "timeline", "heatmap",
    "pricing", "row", "col", "grid",
}


def _wants_fill(node):
    return isinstance(node, dict) and node.get("type") in FILL_HUNGRY


# ---------- placement (emit elements) ----------

def place(node, pal, x, y, w, h, els):
    t = node.get("type", "text")
    if t == "row":
        items = node.get("items", [])
        if not items:
            return
        gap = node.get("gap", 16)
        sizes = node.get("sizes") or [1] * len(items)
        tot = sum(sizes) or 1
        inner_w = w - gap * (len(items) - 1)
        widths = [inner_w * s / tot for s in sizes]
        # equal-height columns sized to tallest content, vertically centered — unless a
        # child needs to fill (chart/diagram/nested container), then keep the full band.
        if not any(_wants_fill(it) for it in items):
            nat = max((measure(it, pal, cw) for it, cw in zip(items, widths)), default=h)
            band = min(h, nat)
            y = y + (h - band) / 2
            h = band
        cx = x
        for it, cw in zip(items, widths):
            place(it, pal, cx, y, cw, h, els)
            cx += cw + gap
    elif t == "col":
        items = node.get("items", [])
        if not items:
            return
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
        if not items:
            return
        gap = node.get("gap", 16)
        cols = min(node.get("cols", 2), len(items))
        rows = (len(items) + cols - 1) // cols
        cw = (w - gap * (cols - 1)) / cols
        ch = (h - gap * (rows - 1)) / rows
        # if the cards don't need to fill, cap row height to natural content + center the
        # block vertically, so a short card grid isn't blown up into tall empty cards.
        if not any(_wants_fill(it) for it in items):
            nat = max((measure(it, pal, cw) for it in items), default=ch)
            ch_nat = min(ch, max(nat, 96))
            block = ch_nat * rows + gap * (rows - 1)
            y = y + max(0, (h - block) / 2)
            ch = ch_nat
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
        # fixed band height, vertically centered (don't stretch to fill a tall box)
        bh = min(h, 132)
        y = y + (h - bh) / 2
        h = bh
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
    elif t == "progresslist":
        items = node.get("items", [])
        label_w = 150
        track_x = x + label_w
        track_w = w - label_w - 60
        rh = 42
        for i, it in enumerate(items):
            it = it if isinstance(it, dict) else {"label": str(it), "value": 0}
            ry = y + i * rh
            accent = accent_for(pal, i, it)
            v = max(0, min(100, float(it.get("value", 0))))
            els.append(txt(it.get("label", ""), x, ry, label_w - 10, rh - 8, 13, pal["ink"], valign="middle", font=pal["font"]))
            els.append(rect(track_x, ry + rh / 2 - 6, track_w, 12, pal["panel"], shape="roundRect"))
            els.append(rect(track_x, ry + rh / 2 - 6, max(6, int(track_w * v / 100)), 12, accent, shape="roundRect"))
            els.append(txt(f"{int(v)}%", track_x + track_w + 10, ry, 50, rh - 8, 13, accent, bold=True, valign="middle", font=pal["font"]))
    elif t == "pricing":
        plans = node.get("plans", node.get("items", []))
        n = max(1, len(plans))
        gap = 16
        pw = (w - gap * (n - 1)) / n
        for i, p in enumerate(plans):
            p = p if isinstance(p, dict) else {"name": str(p)}
            px = x + i * (pw + gap)
            featured = p.get("featured")
            accent = pal["primary"] if not featured else pal["alert"]
            els.append(card(int(px), y, int(pw), h, "#FFFFFF", outline=({"color": accent, "width": 2} if featured else None)))
            els.append(rect(int(px), y, int(pw), 70, accent, shape="roundRect"))
            els.append(txt(p.get("name", ""), int(px), y + 10, int(pw), 26, 16, "#FFFFFF", bold=True, align="center", font=pal["font"]))
            price = p.get("price", "")
            if p.get("period"):
                price = f"{price}"
            els.append(txt(str(price), int(px), y + 34, int(pw), 30, 22, "#FFFFFF", bold=True, align="center", font=pal["font"]))
            iy = y + 86
            for it in p.get("items", [])[:6]:
                els.append(txt("✓", int(px) + 16, iy, 18, 24, 13, accent, bold=True, valign="middle", font=pal["font"]))
                els.append(txt(str(it), int(px) + 38, iy, int(pw) - 50, 24, 12.5, pal["ink"], valign="middle", font=pal["font"]))
                iy += 30
    elif t == "milestone":
        items = node.get("items", [])
        n = max(1, len(items))
        ly = y + h / 2
        els.append(rect(x, int(ly) - 2, w, 4, pal["primary"], shape="roundRect"))
        step = w / n
        for i, it in enumerate(items):
            it = it if isinstance(it, dict) else {"title": str(it)}
            cx = x + step * i + step / 2
            accent = accent_for(pal, i, it)
            above = i % 2 == 0
            cardh = (h / 2) - 28
            cy0 = (ly - 14 - cardh) if above else (ly + 14)
            cw = step - 18
            els.append(rect(int(cx) - 7, int(ly) - 7, 14, 14, accent, shape="ellipse"))
            els.append(rect(int(cx) - 1, int(cy0 + cardh) if above else int(ly), 2, 14, pal["line"]))
            els.append(card(int(cx - cw / 2), int(cy0), int(cw), int(cardh), pal["light"]))
            els.append(rect(int(cx - cw / 2), int(cy0), int(cw), 4, accent))
            if it.get("date"):
                els.append(txt(it["date"], int(cx - cw / 2) + 12, int(cy0) + 10, int(cw) - 24, 22, 13, accent, bold=True, font=pal["font"]))
            els.append(txt(it.get("title", ""), int(cx - cw / 2) + 12, int(cy0) + 32, int(cw) - 24, 24, 13, pal["ink"], bold=True, font=pal["font"]))
            if it.get("body"):
                els.append(txt(it["body"], int(cx - cw / 2) + 12, int(cy0) + 56, int(cw) - 24, int(cardh) - 64, 11, pal["muted"], font=pal["font"]))
    elif t == "roadmap":
        # phased plan: connected columns, each a card with a colored header (name + time)
        # and a short bullet list. Connecting chevrons convey forward motion.
        phases = node.get("phases", node.get("items", []))
        n = max(1, len(phases))
        gap = 22
        pw = (w - gap * (n - 1)) / n
        hdr = 48
        for i, p in enumerate(phases):
            p = p if isinstance(p, dict) else {"name": str(p)}
            px = x + i * (pw + gap)
            accent = accent_for(pal, i, p)
            els.append(card(int(px), y, int(pw), h, pal["light"]))
            els.append(rect(int(px), y, int(pw), hdr, accent, shape="roundRect"))
            nm = p.get("name", p.get("title", ""))
            has_time = bool(p.get("time"))
            els.append(txt(nm, int(px) + 12, y + (6 if has_time else 0), int(pw) - 24, 24, 14, "#FFFFFF",
                           bold=True, align="center", valign=("top" if has_time else "middle"), font=pal["font"]))
            if has_time:
                els.append(txt(str(p["time"]), int(px) + 12, y + 27, int(pw) - 24, 18, 11, "#DCE8F7", align="center", font=pal["font"]))
            iy = y + hdr + 14
            for it in p.get("items", [])[:6]:
                tx = (it.get("text") or it.get("title") or "") if isinstance(it, dict) else str(it)
                els.append(rect(int(px) + 16, iy + 7, 6, 6, accent, shape="ellipse"))
                els.append(txt(str(tx), int(px) + 28, iy, int(pw) - 42, 24, 12, pal["ink"], valign="middle", font=pal["font"]))
                iy += 26
            if i < n - 1:
                els.append(txt("➜", int(px + pw), y, gap, hdr, 18, accent, bold=True, align="center", valign="middle", font=pal["font"]))
    elif t == "orgchart":
        root = node.get("root", {})
        children = node.get("children", [])
        m = max(1, len(children))
        rw, rh0 = 200, 50
        rx = x + (w - rw) / 2
        els.append(rect(int(rx), y, rw, rh0, pal["primary"], shape="roundRect", shadow=True))
        els.append(txt(root.get("title", "") if isinstance(root, dict) else str(root), int(rx), y, rw, rh0, 15, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        gap = 16
        cw = (w - gap * (m - 1)) / m
        ch0 = 56
        cy0 = y + rh0 + 46
        bus_y = y + rh0 + 22
        els.append(rect(int(x + w / 2) - 1, y + rh0, 2, 22, pal["line"]))
        if m > 1:
            els.append(rect(int(x + cw / 2), bus_y, int((m - 1) * (cw + gap)), 2, pal["line"]))
        for i, c in enumerate(children):
            c = c if isinstance(c, dict) else {"title": str(c)}
            cx = x + i * (cw + gap)
            cxc = cx + cw / 2
            accent = accent_for(pal, i, c)
            els.append(rect(int(cxc) - 1, bus_y, 2, cy0 - bus_y, pal["line"]))
            els.append(card(int(cx), int(cy0), int(cw), ch0, pal["light"]))
            els.append(rect(int(cx), int(cy0), 5, ch0, accent, shape="roundRect"))
            els.append(txt(c.get("title", ""), int(cx) + 14, int(cy0), int(cw) - 20, ch0, 14, pal["ink"], bold=True, valign="middle", font=pal["font"]))
            subs = c.get("items", [])
            for k, s in enumerate(subs[:3]):
                sy = cy0 + ch0 + 12 + k * 26
                els.append(rect(int(cx) + 14, sy + 7, 6, 6, accent, shape="ellipse"))
                els.append(txt(str(s), int(cx) + 28, sy, int(cw) - 36, 24, 12, pal["muted"], valign="middle", font=pal["font"]))
    elif t == "architecture":
        layers = node.get("layers", [])
        n = max(1, len(layers))
        gap = 12
        lh = (h - gap * (n - 1)) / n
        label_w = 140
        for i, ly in enumerate(layers):
            ly = ly if isinstance(ly, dict) else {"name": str(ly), "items": []}
            yy = y + i * (lh + gap)
            accent = accent_for(pal, i, ly)
            els.append(card(x, int(yy), w, int(lh), pal["light"]))
            els.append(rect(x, int(yy), label_w, int(lh), accent, shape="roundRect"))
            els.append(txt(ly.get("name", ""), x, int(yy), label_w, int(lh), 14, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
            items = ly.get("items", [])
            m = max(1, len(items))
            ax = x + label_w + 14
            aw = (x + w) - ax - 10
            cgap = 10
            cw = (aw - (m - 1) * cgap) / m
            for j, it in enumerate(items):
                cx = ax + j * (cw + cgap)
                els.append(rect(int(cx), int(yy) + 10, int(cw), int(lh) - 20, "#FFFFFF", shape="roundRect", outline={"color": accent, "width": 1}))
                els.append(txt(str(it), int(cx) + 4, int(yy) + 10, int(cw) - 8, int(lh) - 20, 12, pal["ink"], align="center", valign="middle", font=pal["font"]))
    elif t == "house":
        primary = pal["accents"][0]
        roof_h = 54
        els.append(rect(x, y, w, roof_h, primary, shape="trapezoid"))
        if node.get("roof"):
            els.append(txt(node["roof"], x + 40, y + 12, w - 80, 30, 16, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
        pillars = node.get("pillars", [])
        np_ = max(1, len(pillars))
        base_h = 38
        py = y + roof_h + 12
        ph = (y + h) - py - base_h - 12
        gap = 14
        pw = (w - gap * (np_ - 1)) / np_
        for i, pil in enumerate(pillars):
            pil = pil if isinstance(pil, dict) else {"title": str(pil), "items": []}
            px = x + i * (pw + gap)
            accent = accent_for(pal, i, pil)
            els.append(card(int(px), int(py), int(pw), int(ph), pal["light"]))
            els.append(rect(int(px), int(py), int(pw), 38, accent, shape="roundRect"))
            els.append(txt(pil.get("title", ""), int(px), int(py), int(pw), 38, 14, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
            for k, it in enumerate(pil.get("items", [])[:5]):
                els.append(txt("· " + str(it), int(px) + 14, int(py) + 48 + k * 26, int(pw) - 22, 24, 12, pal["ink"], valign="middle", font=pal["font"]))
        base = node.get("base", "")
        if isinstance(base, list):
            base = "   ·   ".join(base)
        els.append(rect(x, y + h - base_h, w, base_h, pal["navy"], shape="roundRect"))
        els.append(txt(base, x, y + h - base_h, w, base_h, 14, "#FFFFFF", bold=True, align="center", valign="middle", font=pal["font"]))
    elif t == "spacer":
        pass  # intentional whitespace
    else:
        # Unknown component type — NEVER vanish silently (that is what causes blank pages).
        # Render whatever textual content the node carries inside a light panel so the
        # content is visible and QA can catch the wrong type.
        title = node.get("title") or node.get("name") or node.get("label") or node.get("kicker")
        body = node.get("body") or node.get("text") or node.get("value") or node.get("quote") or node.get("desc")
        items = node.get("items") if isinstance(node.get("items"), list) else None
        els.append(card(x, y, w, h, pal["light"]))
        accent = accent_for(pal, node.get("_i", 0), node)
        els.append(rect(x, y, 5, h, accent, shape="roundRect"))
        cy = y + PAD
        if title:
            els.append(txt(str(title), x + PAD + 6, cy, w - 2 * PAD - 6, 26, 16, pal["ink"], bold=True, font=pal["font"]))
            cy += 30
        if items:
            for it in items[:6]:
                tx = (it.get("text") or it.get("title") or "") if isinstance(it, dict) else str(it)
                els.append(rect(x + PAD + 6, cy + 7, 7, 7, accent, shape="ellipse"))
                els.append(txt(str(tx), x + PAD + 22, cy, w - 2 * PAD - 28, 24, 13, pal["ink"], valign="middle", font=pal["font"]))
                cy += 28
        elif body:
            els.append(txt(str(body), x + PAD + 6, cy, w - 2 * PAD - 6, h - (cy - y) - PAD, 13, pal["muted"], font=pal["font"]))


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
    _normalize(body)
    _tag_indices(body)
    place(body, pal, x0, y0, x1 - x0, y1 - y0, els)
    return els
