#!/usr/bin/env python3
"""Verify the pptx-enterprise runtime in the current sandbox and run the from-scratch pipeline."""
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def check(name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}{(' — ' + detail) if detail else ''}")
    return ok


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="pptx_smoke_"))
    deck_json = tmp / "deck.json"
    deck_pptx = tmp / "deck.pptx"
    ok = True

    ok &= check("node present", bool(shutil.which("node")), shutil.which("node") or "missing")
    ok &= check("pptxgenjs installed", (ROOT / "node_modules" / "pptxgenjs").exists(),
                "run `npm install` in the skill dir" if not (ROOT / "node_modules" / "pptxgenjs").exists() else "")
    has_soffice = bool(shutil.which("soffice") or shutil.which("libreoffice"))
    check("soffice present (QA render)", has_soffice, "needed for render_inspect.py")
    has_poppler = bool(shutil.which("pdftoppm") or shutil.which("pdftocairo"))
    check("poppler present (QA render)", has_poppler, "needed for render_inspect.py")

    sample = ROOT / "assets" / "examples" / "sample_outline.json"
    branding = ROOT / "assets" / "tcl_branding.json"
    deck_json.write_text(
        subprocess.run([sys.executable, str(SCRIPTS / "outline_to_schema.py"), str(sample), str(branding)],
                       capture_output=True, text=True, check=True).stdout,
        encoding="utf-8",
    )
    deck = json.loads(deck_json.read_text(encoding="utf-8"))
    ok &= check("outline -> schema", len(deck.get("slides", [])) > 0, f"{len(deck['slides'])} slides")

    types = Counter(el["type"] for s in deck["slides"] for el in s["elements"])
    rich = (types.get("shape", 0) + types.get("line", 0) + types.get("chart", 0)) >= 10
    ok &= check("designed output (not text-only)", rich, f"element types: {dict(types)}")

    try:
        from jsonschema import Draft202012Validator  # noqa: F401
        r = subprocess.run([sys.executable, str(SCRIPTS / "validate.py"), str(deck_json)], capture_output=True, text=True)
        ok &= check("schema validation", r.returncode == 0, r.stdout.strip() or r.stderr.strip())
    except ImportError:
        check("schema validation", True, "skipped (jsonschema not installed)")

    if (ROOT / "node_modules" / "pptxgenjs").exists():
        r = subprocess.run(["node", str(SCRIPTS / "schema_to_pptx.js"), str(deck_json), str(deck_pptx)],
                           capture_output=True, text=True)
        produced = deck_pptx.exists()
        ok &= check("schema -> .pptx", produced and r.returncode == 0, r.stderr.strip()[:200] if not produced else str(deck_pptx))
        if produced:
            import zipfile
            z = zipfile.ZipFile(deck_pptx)
            n = len([x for x in z.namelist() if x.startswith("ppt/slides/slide") and x.endswith(".xml")])
            ok &= check("valid OOXML", n == len(deck["slides"]), f"{n} slide XML parts")

    print(f"\nArtifacts in {tmp}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
