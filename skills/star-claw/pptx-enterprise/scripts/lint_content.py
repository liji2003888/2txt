#!/usr/bin/env python3
"""Lint an OUTLINE for *thin / blank* content pages — the #1 real-world failure:
slides that are just a title + a few lone words + empty space, or a body whose
container is empty so nothing renders.

This complements lint_variety.py (which only catches monotony). Content completeness
comes first, so this linter is the hard gate: a deck must not ship skeleton pages.

Rules (per content slide — chrome slides cover/section/closing/agenda are exempt):
  - BLANK  (fail): a `body` slide whose tree has zero drawable components.
  - THIN   (fail): visible text < MIN_CHARS and no substantive visual (chart/diagram/image).
  - SPARSE (warn): visible text < WARN_CHARS and no substantive visual — borderline,
                   consider adding substance or merging.

usage: lint_content.py <outline.json>
exit 0 = OK (warnings allowed), exit 1 = at least one BLANK/THIN page.
"""
import json
import sys
from pathlib import Path

MIN_CHARS = 55     # below this with no visual => skeleton page, FAIL
WARN_CHARS = 130   # below this with no visual => borderline, WARN

CHROME_LAYOUTS = {"cover", "title", "section", "closing", "agenda", "toc"}
CONTAINERS = {"row", "col", "grid"}
# components that carry their own visual substance (a page of just this is still fine)
VISUALS = {
    "chart", "image", "imagecard", "gauge", "radar", "heatmap", "timeline", "arrowflow",
    "funnel", "quadrant", "balance", "regions", "orgchart", "architecture", "house",
    "milestone", "roadmap", "progresslist", "pricing", "personcard",
}
# designed focal elements — a page built on these is intentional (definition / KPI / quote),
# not a skeleton, even when the text is short.
FOCAL = {"hero", "quote", "stat"}
# fixed-layout presets carry their substance in the layout type, not a body tree.
VISUAL_LAYOUTS = {"chart", "dashboard", "timeline", "matrix", "pyramid", "gantt", "roadmap",
                  "cases", "process", "funnel", "quadrant", "architecture", "comparison", "gallery"}
FOCAL_LAYOUTS = {"statement", "quote", "kpi", "hero", "bignumber"}
TEXT_FIELDS = ("title", "body", "text", "value", "label", "name", "quote", "note",
               "sub", "kicker", "roof", "base", "date", "metric", "tag", "desc", "price", "role")


def _collect(node, leaves, texts):
    """Walk a body subtree: record leaf component types and all visible text."""
    if isinstance(node, str):
        texts.append(node)
        return
    if isinstance(node, list):
        for it in node:
            _collect(it, leaves, texts)
        return
    if not isinstance(node, dict):
        return
    for f in TEXT_FIELDS:
        v = node.get(f)
        if isinstance(v, str):
            texts.append(v)
    t = node.get("type")
    if t and t not in CONTAINERS:
        leaves.append(t)
    for key in ("items", "children", "pillars", "layers", "plans", "phases", "rows", "series", "left", "right", "root"):
        if key in node:
            _collect(node[key], leaves, texts)


def analyse(spec):
    """Return (source, chars, n_leaves, has_visual, has_focal) for one slide."""
    leaves, texts = [], []
    layout = spec.get("layout")
    if spec.get("body") is not None:
        _collect(spec["body"], leaves, texts)
        source = "body"
        has_visual = any(l in VISUALS for l in leaves)
        has_focal = any(l in FOCAL for l in leaves)
        n = len(leaves)
    else:
        # fixed-layout preset: gather any text from common content fields; the preset type
        # is itself the substance (a `chart`/`kpi`/`timeline` slide is not a skeleton).
        for k, v in spec.items():
            if k in ("layout", "notes", "remark", "chrome", "role", "background"):
                continue
            _collect(v if isinstance(v, (dict, list, str)) else str(v), leaves, texts)
        source = "layout"
        has_visual = layout in VISUAL_LAYOUTS or any(l in VISUALS for l in leaves)
        has_focal = layout in FOCAL_LAYOUTS or any(l in FOCAL for l in leaves)
        n = len(leaves) + 1  # the preset counts as one component
    title = spec.get("title", "")
    body_texts = [x for x in texts if x and x != title]
    chars = sum(len(x.strip()) for x in body_texts)
    return source, chars, n, has_visual, has_focal


def main():
    if len(sys.argv) < 2:
        print("usage: lint_content.py <outline.json>", file=sys.stderr)
        sys.exit(2)
    outline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    slides = outline.get("slides", [])
    fails, warns = [], []
    print("per-slide content density:")
    for i, spec in enumerate(slides):
        layout = spec.get("layout", "auto" if spec.get("body") is not None else "bullets")
        title = spec.get("title", "") or spec.get("subtitle", "") or "(no title)"
        if layout in CHROME_LAYOUTS:
            print(f"  {i + 1:>2}. [{layout}] {title[:30]} — chrome, skip")
            continue
        source, chars, n_leaves, has_visual, has_focal = analyse(spec)
        # a page is "substantive" if it has a diagram/chart, a focal element (hero/kpi/quote),
        # or composes >=3 components — otherwise it must carry enough body text.
        substantive = has_visual or has_focal or n_leaves >= 3
        tag = "OK"
        if source == "body" and n_leaves == 0:
            tag = "BLANK"
            fails.append((i + 1, title, "body has no drawable component (empty container?)"))
        elif not substantive and chars < MIN_CHARS:
            tag = "THIN"
            fails.append((i + 1, title, f"only {chars} chars, {n_leaves} comp, no visual — skeleton page"))
        elif has_focal and not has_visual and n_leaves <= 1 and chars < 40:
            tag = "sparse"
            warns.append((i + 1, title, f"lone focal element with {chars} chars — add a supporting line or detail"))
        print(f"  {i + 1:>2}. [{layout}] {title[:28]} — {chars}ch {n_leaves}comp vis={int(has_visual)} foc={int(has_focal)} => {tag}")

    if warns:
        print("\nwarnings (borderline sparse — review, not blocking):")
        for n, t, why in warns:
            print(f"  - p{n} «{t[:24]}»: {why}")
    if fails:
        print("\nCONTENT TOO THIN — fill these pages with real substance (or merge/split):")
        for n, t, why in fails:
            print(f"  - p{n} «{t[:24]}»: {why}")
        sys.exit(1)
    print("\nCONTENT OK" + (f" ({len(warns)} warning(s))" if warns else ""))


if __name__ == "__main__":
    main()
