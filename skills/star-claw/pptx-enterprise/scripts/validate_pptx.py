#!/usr/bin/env python3
"""Validate a generated .pptx (structural OOXML integrity). Exits non-zero on problems.

Checks: the file is a loadable PowerPoint (python-pptx round-trip), every part XML is
well-formed, [Content_Types].xml is present, and each slide's relationship targets resolve.
This catches real corruption without bundling the full ISO XSD set; if `lxml` + XSD files
are available it can be extended to schema validation later.

usage: validate_pptx.py <file.pptx>
"""
import sys
import xml.dom.minidom as minidom
import zipfile
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("usage: validate_pptx.py <file.pptx>", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    problems = []

    # 1) loadable as a presentation
    try:
        from pptx import Presentation
        prs = Presentation(str(path))
        n_slides = len(prs.slides)
    except Exception as exc:  # noqa: BLE001
        print(f"INVALID: not a loadable .pptx — {exc}", file=sys.stderr)
        sys.exit(1)

    z = zipfile.ZipFile(str(path))
    names = set(z.namelist())

    # 2) required parts
    if "[Content_Types].xml" not in names:
        problems.append("missing [Content_Types].xml")
    if "ppt/presentation.xml" not in names:
        problems.append("missing ppt/presentation.xml")

    # 3) every XML part well-formed
    for n in names:
        if n.endswith(".xml") or n.endswith(".rels"):
            try:
                minidom.parseString(z.read(n))
            except Exception as exc:  # noqa: BLE001
                problems.append(f"malformed XML: {n} ({exc})")

    # 4) slide relationship targets resolve
    import re
    for n in names:
        m = re.match(r"ppt/slides/(slide\d+\.xml)$", n)
        if not m:
            continue
        rels = f"ppt/slides/_rels/{m.group(1)}.rels"
        if rels not in names:
            continue
        import xml.etree.ElementTree as ET
        import posixpath
        for rel in ET.fromstring(z.read(rels)):
            tgt = rel.get("Target", "")
            if rel.get("TargetMode") == "External" or tgt.startswith("http"):
                continue
            if tgt.startswith("/"):
                resolved = tgt.lstrip("/")                       # absolute from package root
            else:
                resolved = posixpath.normpath(posixpath.join("ppt/slides", tgt))  # relative to the part
            if resolved not in names:
                problems.append(f"{m.group(1)} → broken rel target: {tgt}")

    if problems:
        print(f"INVALID ({len(problems)} issue(s)):", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        sys.exit(1)
    print(f"OK: valid .pptx — {n_slides} slides, {len(names)} parts, all XML well-formed, rels resolve")


if __name__ == "__main__":
    main()
