---
name: pptx-enterprise
description: Generate enterprise-grade presentations (TCL brand) as .pptx and HTML, driven by a single Slide JSON Schema. Routes between PptxGenJS (from-scratch), python-pptx (brand-fidelity template fill), and a forked PPTist renderer (Web/online edit).
---

# pptx-enterprise

A Skill for enterprise PPT generation. The Slide JSON Schema (`schema/slide_schema.json`) is the single source of truth; renderers project it to `.pptx` and HTML, and a separate path fills branded `.potx` templates in place for pixel-perfect brand fidelity.

## When to use which path

Choose by input:

### 1. From scratch (outline → deck)

- Either run `scripts/outline_to_schema.py <outline.json> [branding.json]` to template a structured outline into slide JSON, **or** emit JSON directly conforming to `schema/slide_schema.json` (richer control).
- Render to `.pptx`: `node scripts/schema_to_pptx.js <deck.json> <out.pptx>` (PptxGenJS).
- Render to HTML: prefer the forked PPTist renderer in `web/` (online-editable). Fallback: `node scripts/schema_to_html.js <deck.json> <out.html>` for QA preview only.

### 2. Fill enterprise template (.potx with placeholders) — brand-fidelity path

- Use `python scripts/template_fill.py <template.potx> <content.json> <out.pptx>` (python-pptx).
- Opens the .potx and injects content into **named placeholders in place**. Masters, layouts, theme, fonts, SmartArt, and animations are preserved verbatim.
- **This is the authoritative path when brand consistency matters.** Do NOT round-trip a branded template through `pptx_to_schema.js` + `schema_to_pptx.js` for final output — that re-builds from primitives and loses the master/theme fidelity.

### 3. Import existing .pptx for editing/preview

- `node scripts/pptx_to_schema.js <in.pptx> <out.json>` (pptxtojson).
- **Lossy** by design (masters/theme/SmartArt/animations are not preserved). Use only for letting users edit content in the Web shell.
- For the final brand-perfect export, re-run path 2 against the original `.potx` carrying the edited content.

### 4. Always run visual QA after generation

- `python scripts/render_inspect.py <file.pptx> [out_dir]` renders each slide to PNG via LibreOffice + pdftoppm.
- Inspect the PNGs (read them with the Read tool) and check: text overflow, element overlap, color/font deviation, missing CJK glyphs. Iterate on the JSON/template and re-render.

## Schema essentials

`schema/slide_schema.json` adopts the PPTist element model:

- Canvas in pixels (default 960×540, 16:9). The renderers map to PowerPoint's 13.333×7.5 in.
- Element types: `text` (HTML content), `image`, `shape`, `line`, `table`, `chart`, `latex`.
- All elements share `{id, type, left, top, width, height, rotate}`.

See `references/schema_authoring.md` for authoring guidance and pitfalls.

## Output trade-off (be honest with users)

The two outputs are **content-consistent, not pixel-consistent**. PowerPoint and browser engines differ in line-wrapping, font metrics, and autofit. For brand-pixel-perfect deliverables, path 2 (template fill) is authoritative; the HTML rendering is for review/embedding.

## Branding

`assets/tcl_branding.json` holds brand colors, font, and logo path. `outline_to_schema.py` and `schema_to_pptx.js` both read it (or default if absent).

## Sandbox requirements

- Python ≥ 3.9 with `python-pptx`, `jsonschema` (see `requirements.txt`)
- Node ≥ 18 with `pptxgenjs`, `pptxtojson` (see `package.json`)
- `soffice` (LibreOffice headless, with Impress import filters) and poppler-utils (`pdftoppm` or `pdftocairo`) for QA rendering
- CJK fonts installed: `Noto Sans CJK SC` or `Source Han Sans` (otherwise headless rendering corrupts Chinese)

## License notice

`web/` will host a fork of PPTist (AGPL-3.0). It is isolated behind the Slide JSON Schema and swappable. See `references/agpl_notice.md` before merging the fork.
