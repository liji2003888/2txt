#!/usr/bin/env python3
"""Unpack a .pptx into a directory with pretty-printed XML, for arbitrary deep OOXML editing.
Edit the XML files, then repack with pack_pptx.py.

usage: unpack_pptx.py <file.pptx> <outdir>
"""
import sys
import xml.dom.minidom as minidom
import zipfile
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("usage: unpack_pptx.py <file.pptx> <outdir>", file=sys.stderr)
        sys.exit(2)
    src, outdir = sys.argv[1], Path(sys.argv[2])
    z = zipfile.ZipFile(src)
    for n in z.namelist():
        data = z.read(n)
        dest = outdir / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        if n.endswith(".xml") or n.endswith(".rels"):
            try:
                data = minidom.parseString(data).toprettyxml(indent="  ", encoding="UTF-8")
            except Exception:
                pass
        dest.write_bytes(data)
    print(f"unpacked {len(z.namelist())} parts -> {outdir}")
    print("edit the XML, then: python scripts/pack_pptx.py", outdir, "<out.pptx>")


if __name__ == "__main__":
    main()
