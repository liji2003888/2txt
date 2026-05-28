#!/usr/bin/env python3
"""Render a .pptx to per-slide PNGs via LibreOffice + pdftoppm/pdftocairo for visual QA."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("error: soffice/libreoffice not found in PATH")
    profile = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    env = {**os.environ, "HOME": str(profile)}
    subprocess.run(
        [
            soffice, "--headless",
            f"-env:UserInstallation=file://{profile}",
            "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path),
        ],
        check=True,
        env=env,
    )
    pdf_path = out_dir / (pptx_path.stem + ".pdf")
    # soffice returns 0 even when it fails to load the source, so verify the output exists.
    if not pdf_path.exists():
        sys.exit(
            "error: LibreOffice produced no PDF (it returns exit 0 even on failure). "
            "Likely a broken/incomplete headless install or missing Impress import filters."
        )
    return pdf_path


def _to_pngs(pdf_path: Path, out_dir: Path, stem: str) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    pdftocairo = shutil.which("pdftocairo")
    if pdftoppm:
        subprocess.run([pdftoppm, "-png", "-r", "120", str(pdf_path), str(out_dir / stem)], check=True)
    elif pdftocairo:
        subprocess.run([pdftocairo, "-png", "-r", "120", str(pdf_path), str(out_dir / stem)], check=True)
    else:
        sys.exit("error: neither pdftoppm nor pdftocairo (poppler-utils) found in PATH")
    return sorted(out_dir.glob(f"{stem}-*.png"))


def render(pptx_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = _to_pdf(pptx_path, out_dir)
    return _to_pngs(pdf_path, out_dir, pptx_path.stem)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: render_inspect.py <file.pptx> [out_dir]", file=sys.stderr)
        sys.exit(2)
    pptx = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else pptx.parent / f"{pptx.stem}.preview"
    pngs = render(pptx, out_dir)
    for p in pngs:
        print(p)
    print(f"\n{len(pngs)} slide(s) rendered to {out_dir}", file=sys.stderr)
    print(
        "Visual QA checklist: text overflow, element overlap, font/color match, CJK glyph completeness.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
