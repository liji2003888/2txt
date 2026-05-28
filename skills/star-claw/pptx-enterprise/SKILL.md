---
name: pptx-enterprise
description: Generate enterprise-grade presentations (TCL brand) as .pptx and HTML, driven by a single Slide JSON Schema. Routes between PptxGenJS (from-scratch), python-pptx (brand-fidelity template fill), and a forked PPTist renderer (Web/online edit).
---

# pptx-enterprise

A Skill for enterprise PPT generation. The Slide JSON Schema (`schema/slide_schema.json`) is the single source of truth; renderers project it to `.pptx` and HTML, and a separate path fills branded `.potx` templates in place for pixel-perfect brand fidelity.

## When to use which path

Choose by input:

### 1. From scratch (outline → deck)

1. Author a **designed outline** (`outline.json`): a list of `slides`, each declaring a `layout` plus structured content. See `assets/examples/sample_outline.json`.
2. `python scripts/outline_to_schema.py <outline.json> [branding.json] > deck.json` — dispatches each slide through the layout library (`scripts/layouts.py`), composing shapes + text + accents.
3. `python scripts/validate.py deck.json` — validate before rendering.
4. `node scripts/schema_to_pptx.js deck.json out.pptx` (PptxGenJS).
5. HTML: prefer the forked PPTist renderer in `web/` (online-editable). Fallback: `node scripts/schema_to_html.js deck.json out.html` for QA preview only.

For one-off, highly custom slides you may emit `deck.json` directly per `schema/slide_schema.json` instead of going through `outline_to_schema.py` — but still compose multiple elements; see the design rules below.

#### Layout catalog (`layouts.py`)

`title`, `agenda`, `section` (full-bleed divider), `bullets` (colored markers + head/body, **not** `<ul>` dumps), `two_column`, `cards` (feature grid), `kpi` (big-number stats), `chart`, `comparison`, `process` (numbered step flow), `timeline` (milestones), `table` (styled, colored header), `statement` (big takeaway), `image_text` (image + copy split), `quote`, `closing`. Content layouts get an auto brand footer + page number.

#### Themes

The 2nd arg to `outline_to_schema.py` is a theme/branding JSON. Ships with `assets/tcl_branding.json` (default red) and `assets/themes/{ocean,midnight,mono}.json`. A theme sets `themeColors` plus optional `fontColor`/`backgroundColor`/`muted`/`light`/`panel`/`line` — so dark themes (e.g. `midnight`) recolor backgrounds and panels automatically. Author new themes by copying one of these.

#### Design rules — DO NOT produce text dumps

- A slide is a **composition**, never a title + one `<ul>`. Every content slide carries an accent header bar, a divider, and colored markers/cards/panels.
- Vary layouts across the deck: open with `title`/`agenda`, break sections with `section`, use `cards`/`kpi`/`chart`/`comparison` for substance, close with `quote`/`closing`.
- Keep ≤ 6 items per slide; split dense content across `two_column` or `cards`.
- Drive all color from `assets/tcl_branding.json` `themeColors`; never hardcode.
- Run `scripts/render_inspect.py` and read the PNGs to confirm it looks designed, not listed.

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

## Sandbox requirements & self-check

- Python ≥ 3.9 with `python-pptx`, `jsonschema` (see `requirements.txt`)
- Node ≥ 18 with `pptxgenjs`, `pptxtojson` (see `package.json`)
- `soffice` (LibreOffice headless, with Impress import filters) and poppler-utils (`pdftoppm` or `pdftocairo`) for QA rendering
- CJK fonts installed: `Noto Sans CJK SC` or `Source Han Sans` (otherwise headless rendering corrupts Chinese)

Setup (run once in the skill dir):

```
bash setup.sh
```

`setup.sh` installs system deps (LibreOffice Impress headless + poppler + Noto CJK, lean via `--no-install-recommends`), Python and Node deps, then runs the smoke test. To do it manually instead:

```
sudo apt-get install -y --no-install-recommends libreoffice-impress poppler-utils fonts-noto-cjk
pip install -r requirements.txt
npm install
python scripts/smoke_test.py   # verifies runtime + generates a sample deck end to end
```

`smoke_test.py` is the runtime guarantee: it checks each tool, runs outline → schema → .pptx, and asserts the output is a designed composition (shapes/lines/charts present), not a text dump.

> Note: the core generation path (outline → schema → .pptx) needs only Python + Node. LibreOffice/poppler are required **only** for the optional visual-QA auto-render (`render_inspect.py`) and the `.pptx → HTML` fallback. If disk is tight you can skip them and QA by opening the .pptx manually.

## Progress notifications (long tasks)

`scripts/notify_lark.py "<message>"` posts a one-line update to Lark/Feishu. It prefers a configured **Lark-CLI** and falls back to a webhook; it is a no-op if neither is set. Use it to ping key milestones during long generations.

- **Lark-CLI (preferred)**: set `LARK_CLI_CMD` to your send command; the message is appended as the final argument (no shell, injection-safe). Example:
  ```
  export LARK_CLI_CMD="lark-cli message send --chat oc_xxx --text"
  python scripts/notify_lark.py "PPT 生成完成:15 页,已导出 deck.pptx"
  ```
- **Webhook (fallback)**: set `LARK_WEBHOOK` (and `LARK_SECRET` for signed bots).

## License notice

`web/` will host a fork of PPTist (AGPL-3.0). It is isolated behind the Slide JSON Schema and swappable. See `references/agpl_notice.md` before merging the fork.
