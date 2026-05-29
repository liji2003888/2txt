#!/usr/bin/env python3
"""Lint an OUTLINE for *genuine* monotony — only the real failure: a whole deck of
near-identical slides (e.g. every page a card grid).

NOTE: content completeness comes first. A section legitimately spans multiple pages, and
adjacent pages MAY share a structure when the content calls for it — that is NOT a problem.
So this linter does NOT fail on consecutive repeats; it only flags a deck that is
overwhelmingly one structure (true "AI-flavored" monotony).

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
    content = [p for i, p in enumerate(seq) if p not in CHROME]
    n = len(content)
    print("per-slide primary structure:")
    for i, p in enumerate(seq):
        print(f"  {i + 1:>2}. {p}")
    if n < 6:
        print(f"\n{n} content slides — OK (variety check applies to >=6).")
        return
    cnt = Counter(content)
    distinct = len(cnt)
    cards = cnt.get("cards", 0) + cnt.get("cards(grid)", 0)
    top, topn = cnt.most_common(1)[0]
    problems = []
    # only TRUE monotony fails:
    if distinct < 4:
        problems.append(f"only {distinct} distinct structures across {n} content slides (need >=4) — too monotonous")
    if cards > n * 0.55:
        problems.append(f"cards/grids = {cards}/{n} (>55%) — break some into other structures")
    if topn > n * 0.6:
        problems.append(f"structure '{top}' used on {topn}/{n} slides (>60%) — vary where content differs")
    print(f"\ndistinct: {distinct} | content slides: {n} | cards-grids: {cards} | most-used: {top}×{topn}")
    if problems:
        print("\nMONOTONY — vary where content genuinely differs (content completeness still comes first):")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("VARIETY OK")


if __name__ == "__main__":
    main()
