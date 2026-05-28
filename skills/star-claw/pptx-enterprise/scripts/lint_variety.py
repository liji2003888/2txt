#!/usr/bin/env python3
"""Lint an OUTLINE for layout monotony — the #1 quality issue in long decks.

Classifies each content slide's primary structure and checks the variety rules
from SKILL.md: no same structure on consecutive slides, enough distinct types,
and card/grid usage capped. Exits non-zero if a deck of >=6 content slides
violates the rules, so it can gate generation.

usage: lint_variety.py <outline.json>
"""
import json
import sys
from collections import Counter
from pathlib import Path

CHROME = {"cover", "title", "section", "closing", "agenda"}


def _leaf_types(node, acc):
    if not isinstance(node, dict):
        return
    t = node.get("type")
    if t in ("row", "col", "grid"):
        if t == "grid":
            acc["__grid__"] += 1
        for it in node.get("items", []):
            _leaf_types(it, acc)
    elif t:
        acc[t] += 1


def primary_of(spec):
    if spec.get("body") is not None:
        acc = Counter()
        _leaf_types(spec["body"], acc)
        # grid of cards reads as "cards"
        if acc.get("card", 0) >= 3 and acc.get("__grid__", 0):
            return "cards(grid)"
        acc.pop("__grid__", None)
        acc.pop("text", None)
        acc.pop("bullets", None)
        if acc:
            return acc.most_common(1)[0][0]
        return "text"
    return spec.get("layout", "bullets")


def main():
    if len(sys.argv) < 2:
        print("usage: lint_variety.py <outline.json>", file=sys.stderr)
        sys.exit(2)
    outline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    slides = outline.get("slides", [])
    seq = [primary_of(s) for s in slides]
    content = [(i, p) for i, p in enumerate(seq) if p not in CHROME]
    n = len(content)
    print("per-slide primary structure:")
    for i, p in enumerate(seq):
        print(f"  {i + 1:>2}. {p}")
    if n < 6:
        print(f"\n{n} content slides — variety rules apply to >=6; OK.")
        return
    distinct = len(set(p for _, p in content))
    cnt = Counter(p for _, p in content)
    cards = cnt.get("cards", 0) + cnt.get("cards(grid)", 0)
    # max consecutive repeat among content slides
    maxrun = run = 1
    for k in range(1, len(content)):
        run = run + 1 if content[k][1] == content[k - 1][1] else 1
        maxrun = max(maxrun, run)
    need = 8 if n >= 16 else 6
    problems = []
    if maxrun >= 2:
        problems.append(f"same structure repeats on {maxrun} consecutive content slides (rule: never 2 in a row)")
    if distinct < need:
        problems.append(f"only {distinct} distinct structures across {n} content slides (need >={need})")
    if cards > n / 3:
        problems.append(f"cards/grids = {cards}/{n} (> 1/3 cap)")
    print(f"\ndistinct structures: {distinct} | content slides: {n} | cards-grids: {cards} | max consecutive: {maxrun}")
    if problems:
        print("\nVARIETY FAIL — redesign per SKILL.md content-shape map:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("VARIETY OK")


if __name__ == "__main__":
    main()
