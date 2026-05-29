#!/usr/bin/env python3
"""Repack an unpacked directory (see unpack_pptx.py) back into a .pptx.
[Content_Types].xml is written first (OOXML requirement). Validates the result.

usage: pack_pptx.py <dir> <out.pptx>
"""
import sys
import zipfile
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("usage: pack_pptx.py <dir> <out.pptx>", file=sys.stderr)
        sys.exit(2)
    root, out = Path(sys.argv[1]), sys.argv[2]
    files = [p for p in root.rglob("*") if p.is_file()]
    rels = [str(p.relative_to(root)).replace("\\", "/") for p in files]
    # [Content_Types].xml must come first
    rels.sort(key=lambda n: (n != "[Content_Types].xml", n))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in rels:
            z.write(root / n, n)
    print(f"packed {len(rels)} parts -> {out}")
    # best-effort validation
    try:
        import subprocess
        r = subprocess.run([sys.executable, str(Path(__file__).parent / "validate_pptx.py"), out], capture_output=True, text=True)
        print((r.stdout or r.stderr).strip())
    except Exception:
        pass


if __name__ == "__main__":
    main()
