---
name: pptx-enterprise
description: Generate enterprise-grade presentations (TCL brand) as .pptx and HTML, driven by a single Slide JSON Schema. Routes between PptxGenJS (from-scratch), python-pptx (brand-fidelity template fill), and a forked PPTist renderer (Web/online edit).
---

# pptx-enterprise

A Skill for enterprise PPT generation. The Slide JSON Schema (`schema/slide_schema.json`) is the single source of truth; renderers project it to `.pptx` and HTML, and a separate path fills branded `.potx` templates in place for pixel-perfect brand fidelity.

## Model-agnostic

This skill contains **no LLM calls** — every script is plain Python/Node. It works with any agent model (Qwen, DeepSeek, Claude, …); the model only needs to (1) write a small JSON outline or edit-ops file following the examples here, and (2) run the commands below. The outline parser is forgiving (missing fields default; a malformed slide falls back to a bullet slide instead of aborting), and `scripts/validate.py` reports any schema problem before rendering. Prefer copying the templates in `assets/examples/` and editing values, rather than composing JSON from scratch.

## Authoring slides: prefer the auto-layout engine (compose a tree)

**To get designed, non-templated slides, author each slide as a layout TREE — do not just pick a fixed template.** A slide with a `"body"` tree is flowed by the auto-layout engine (`compose.py`): you decide the *structure*, the engine computes geometry (flexbox-style) so nothing overlaps and it adapts to the content. This is how to make decks that look bespoke rather than mechanical.

```json
{ "title": "页面标题", "banner": "可选底部金句",
  "body": { "type": "row", "gap": 20, "items": [ ...nodes... ] } }
```

Containers: `row` / `col` / `grid` (`gap`, `sizes` weights for row, `cols` for grid) — nest freely.
Components: `card` (`title`/`body`/`icon`/`metric`/`tag`/`tone:light|blue|navy`/`accent`), `stat` (`value`/`label`/`note`), `panel` (`title`/`tone`/`items:[...]`), `iconitem` (`icon`/`title`/`body`), `bullets` (`items`), `text` (`text`/`size`/`bold`/`align`), `chart` (`chartType`/`labels`/`series`), `image` (`src`), `spacer`.

Design guidance:
- Vary structure per slide to fit the content — a comparison is two `panel`s in a `row`; a dashboard is a `col` of a stat `row` + a chart `row` (`sizes:[2,1]`); a feature set is a `grid`. Don't reuse the same shape every slide.
- Accent colors rotate across sibling items automatically (tech-blue series); set `"accent":"red"` on the one key node only.
- Icons are white on colored chips, never black. Keep card bodies short; the engine prevents overlap but concise text reads better.

The fixed-template layouts below (`cards`, `process`, `kpi`, …) still work as quick presets and as examples of good composition, but the **tree is the primary, more flexible path**.

## When to use which path

Choose by input:

### Two ways to render a generated deck to .pptx

**Prefer `schema_to_pptx.js` (PptxGenJS) for fully-editable output** — every shape/text/table is a native editable PowerPoint object, charts are embedded images. This is the default path. Use `schema_to_pptx_tpl.py` (master) only when pixel-perfect master chrome matters more than editability.

- **`schema_to_pptx.js` (PptxGenJS, DEFAULT)** — draws everything from primitives, including the brand chrome (corner badge, logo, red top title + divider) and the cover background image. No template needed; works for any theme; output is fully editable.
- **`schema_to_pptx_tpl.py` (python-pptx, THE path for TCL)** — renders the body onto slides created from the real **master template's layouts**, so the corner badge, olympic logo, slide number and cover background come **pixel-perfect from the master** (not redrawn), and the title sits where the template puts it (top). The theme sets `baseTemplate` + layout names (`tcl_feishu` → `assets/csot_master.pptx`). Each deck slide carries a `role` (cover/content/full) that selects the master layout (`空白` / `标题幻灯片`). Elements tagged `role:"chrome"`/`"coverbg"`/`"headerline"` are skipped because the master provides them. Charts work here too — `outline_to_schema` pre-renders every chart to a PNG (via `chart_img.js`) and embeds it as an image, so no native-chart limitation.

To add or update the master: strip example slides from a branded `.pptx` (keep masters/layouts) and point `baseTemplate` at it; set `contentLayout`/`coverLayout` to the layout names (see `python scripts/dump_pptx.py` / list via python-pptx `slide_layouts`).

### 1. From scratch (outline → deck)

1. Author a **designed outline** (`outline.json`): a list of `slides`, each declaring a `layout` plus structured content. See `assets/examples/sample_outline.json`.
2. `python scripts/outline_to_schema.py <outline.json> [branding.json] > deck.json` — dispatches each slide through the layout library (`scripts/layouts.py`), composing shapes + text + accents.
3. `python scripts/validate.py deck.json` — validate before rendering.
4. `node scripts/schema_to_pptx.js deck.json out.pptx` (PptxGenJS).
5. HTML: prefer the forked PPTist renderer in `web/` (online-editable). Fallback: `node scripts/schema_to_html.js deck.json out.html` for QA preview only.

For one-off, highly custom slides you may emit `deck.json` directly per `schema/slide_schema.json` instead of going through `outline_to_schema.py` — but still compose multiple elements; see the design rules below.

#### Layout catalog (`layouts.py`)

`title`, `cover` (branded title page; on the TCL master the cover background comes from the `空白` master layout — overlays only `meta`/`title`/`dept`/`author` + wordmark), `agenda`, `section` (full-bleed divider), `bullets` (colored markers + head/body, **not** `<ul>` dumps), `two_column`, `cards` (feature grid), `kpi` (big-number stats), `comparison`, `process` (numbered step circles), `flow` (流程图: rounded-rect nodes + arrows), `chevron` (箭头推进: numbered chevrons + callout bubbles), `hub` (辐射图: center circle + satellite ring), `dashboard` (数据看板: KPI strip + main chart + pie/donut), `architecture` (技术架构图: stacked layers, each = colored label + module chips), `house` (战略房子: trapezoid roof + pillars + foundation), `cases` (AI应用案例: shadowed icon cards + metric badges), `solution` (解决方案: 挑战→方案→价值, arrows, middle emphasized), `roadmap` (项目时程: phase bars on a quarter axis + deliverables), `gantt` (甘特图: workstream rows × period columns with bars), `timeline` (milestones), `matrix` (capability matrix: N category columns × item lists), `hierarchy` (root box + connected tier cards), `circles` (3 overlapping concept circles + side copy), `pyramid` (stacked levels, `inverted` for funnel), `chart` (business chart — `chartType`: `column`/`bar`/`line`/`pie`/`donut`; rendered to an embedded PNG so it works on the master path too), `table` (styled, colored header), `statement` (big takeaway), `image_text` (image + copy split), `quote`, `closing`. Content layouts get an auto brand footer + page number.

Icons inside colored/dark slots are always rendered **white** (monochrome sets `lucide`/`icon-park-outline` recolor cleanly). The accent palette is a **tech-blue series** (`#1677FF`/`#00A6F0`/`#0E5FD8`/`#4D9BFF`/`#0068B7`/`#00C2FF`) cycled across multi-item layouts; **red `#E60012` and black `#111111` are reserved for key nodes** — set `"accent":"red"` or `"accent":"black"` (or a hex) on any item in slot layouts (`cards`/`kpi`/`process`/`flow`/`chevron`/`hub`/`dashboard`) to emphasize it.

#### Composition: rigorous 总分 structure

Compose decks with a clear overview-then-detail (总→分) logic: open with `cover`, then an `agenda`/overview slide listing the sections (总), break each section with a `section` divider, then detail it (分) with the layout matching the content shape, and close with `statement`/`closing`. The agenda items should mirror the actual sections in order, so the first pages establish the logical skeleton before diving into specifics. Vary layouts — never repeat the same one on consecutive slides; combine diagrams + icons + charts.

On brand themes (those with `badgeColor`, e.g. `tcl_feishu`) every content page renders the TCL standard header: a **dark-navy bold title at the top + a thin light-gray divider**, plus the left red corner badge and right TCL logo. The palette is flat & corporate — **blue (`#1668DC` series) + navy (`#1A2332`) + red (`#E60012`, reserved for key nodes) + light-gray panels**; comparison/contrast panels pair blue with navy.

Any content slide can add a bottom **黑红组合框 banner** (key takeaway) via `"banner": "text"` or `"banner": {"text": "...", "sub": "..."}` — renders a navy bar with a red left cap and white text. The `cover`/`full` slides omit the corner chrome.

Shape elements support `"shadow": true` for a soft drop shadow (rendered on the PptxGenJS path and previews); the new card-based layouts use it for a clean, lifted look. Layouts adapt to content: item/column/step/card/level counts drive spacing and sizing, and accent colors rotate. They are **starting points, not rigid templates** — see the flexibility rule below.

#### Themes

The 2nd arg to `outline_to_schema.py` is a theme/branding JSON. **When omitted, the default is `assets/themes/tcl_feishu.json`** — so all generations share one content palette unless explicitly overridden. Also ships `assets/tcl_branding.json` (red) and `assets/themes/{ocean,midnight,mono}.json`. A theme sets `themeColors` plus optional `fontColor`/`backgroundColor`/`muted`/`light`/`panel`/`line` (dark themes like `midnight` recolor backgrounds), and brand chrome: `logo` (right-corner image) + `badgeColor` (left-corner badge). When both are set, every light-background slide carries the same left + right corner badges, matching the TCL reference decks. Author new themes by copying one of these.

#### Icons

Slot-based layouts (`cards`, `process`, `hierarchy`, `circles`, `matrix`) take an optional `icon` per item, e.g. `"icon": "lucide/search"` or `"icon": "icon-park/people"`. Sets: `lucide` (~1.7k line), `icon-park-outline` (~2.6k line), `icon-park` (~2.6k multicolor). `outline_to_schema` recolors monochrome icons (white inside the colored slot), rasterizes to PNG via `scripts/icon.js` (`@resvg/resvg-js`), caches under `assets/.icon_cache/`, and embeds them. An unknown icon name is dropped gracefully (slot falls back to its number/tag). All three sets are commercial-safe (ISC/Apache-2.0). Browse names on iconify.design. Requires `@iconify-json/*` + `@resvg/resvg-js` (pulled by `npm install`).

#### Design rules — DO NOT produce text dumps

- A slide is a **composition**, never a title + one `<ul>`. Every content slide carries an accent header bar, a divider, and colored markers/cards/panels.
- Vary layouts across the deck: open with `title`/`agenda`, break sections with `section`, use `cards`/`kpi`/`chart`/`comparison` for substance, close with `quote`/`closing`.
- Keep ≤ 6 items per slide; split dense content across `two_column` or `cards`.
- Drive all color from `assets/tcl_branding.json` `themeColors`; never hardcode.
- Run `scripts/render_inspect.py` and read the PNGs to confirm it looks designed, not listed.

#### Don't over-template (keep layouts flexible)

- Layouts are composable starting points, not a fixed mold. **Vary them** — don't reuse the same layout on consecutive slides, and don't force every deck through the same sequence.
- Adjust the content density to fit (2–6 items), and pick the layout that matches the *shape* of the content (steps→`process`, levels→`pyramid`, categories→`matrix`, concepts→`circles`).
- For a slide that no layout fits, **compose elements directly** in `deck.json` per `schema/slide_schema.json` (shapes/text/lines/images with explicit positions). Mixing hand-composed slides with layout-generated ones is expected and encouraged.
- Per-slide overrides are allowed: e.g. `color` on `section`/`quote`/`closing`, `inverted` on `pyramid`, `imageSide` on `image_text`, `chrome: false` to drop corner badges on a specific slide.

### 2. Fill enterprise template (.potx with placeholders) — brand-fidelity path

- Use `python scripts/template_fill.py <template.potx> <content.json> <out.pptx>` (python-pptx).
- Opens the .potx and injects content into **named placeholders in place**. Masters, layouts, theme, fonts, SmartArt, and animations are preserved verbatim.
- **This is the authoritative path when brand consistency matters.** Do NOT round-trip a branded template through `pptx_to_schema.js` + `schema_to_pptx.js` for final output — that re-builds from primitives and loses the master/theme fidelity.

### 3. Modify an existing .pptx in place (faithful tweaks) — preferred for "edit this deck"

When the user hands you a finished deck and asks to change things while keeping the design:

1. `python scripts/dump_pptx.py <in.pptx>` — lists every slide's shapes (index, name, text, table cells, pictures, positions) so you can target edits precisely.
2. Author an ops file and run `python scripts/edit_pptx.py <in.pptx> <ops.json> <out.pptx>`. Everything not touched (masters, theme, fonts, SmartArt, animations, layout) is preserved.

Supported ops (target shapes by `shape_index` — most reliable — or `shape` name):

```json
{"ops": [
  {"op": "replace_text", "find": "小黑", "replace": "小白"},
  {"op": "replace_text", "slide": 2, "find": "...", "replace": "..."},
  {"op": "set_text", "slide": 1, "shape_index": 0, "text": ["第一行", "第二行"]},
  {"op": "set_table_cell", "slide": 0, "shape": "表格 8", "row": 1, "col": 2, "text": "..."},
  {"op": "set_chart_data", "slide": 7, "shape_index": 3, "categories": ["Q1","Q2"], "series": [{"name": "营收", "values": [1, 2]}]},
  {"op": "replace_image", "slide": 6, "shape_index": 5, "path": "/abs/new.png"},
  {"op": "duplicate_slide", "index": 4, "to": 5},
  {"op": "delete_slide", "index": 9},
  {"op": "reorder_slides", "order": [0, 2, 1, 3]}
]}
```

Ops apply sequentially; indices refer to the deck state at each step, so list index-shifting ops (duplicate/delete/reorder) last. `replace_image` is a same-format blob swap. This is the right path when the deck's body lives in text boxes / auto-shapes rather than placeholders.

### 3b. Import an existing .pptx to re-layout (lossy)

- `node scripts/pptx_to_schema.js <in.pptx> <out.json>` (pptxtojson).
- **Lossy** by design (masters/theme/SmartArt/animations are not preserved). Use only when you intend to *re-generate* the deck through our layouts/themes, not to tweak the original.

### 3c. Native editable cover from a template + generated content (one file)

To put a real, still-editable template cover in front of a generated deck:

1. `python scripts/flatten_cover.py <template.pptx> cover.pptx --title "材料标题" --dept "部门" --author "作者" [--keep 0]` — bakes the cover's layout background images onto the slide, fills the three fields, and keeps just that one self-contained slide.
2. Generate the content deck without its own cover slide → `content.pptx`.
3. `python scripts/merge_pptx.py content.pptx cover.pptx final.pptx --prepend` — prepends the cover; the content (including charts) is preserved natively.

`merge_pptx` copies shapes + images (re-embedding them); it does **not** copy charts on the *added* slides — keep charts in the base deck. (Alternative single-file cover that needs no template at generation time: the `cover` layout with `theme.coverImage`, see Themes.)

### 4. Always run visual QA after generation

- `python scripts/render_inspect.py <file.pptx> [out_dir]` renders each slide to PNG via LibreOffice + pdftoppm.
- **No LibreOffice?** `node scripts/preview.js <deck.json> <slideIndex> <out.png>` rasterizes one slide to PNG via resvg-js (embeds images/icons; CJK needs an installed CJK font). Fast layout/overlap check that works in any sandbox.
- If the agent model has vision, open the PNGs and check: text overflow, element overlap, color/font deviation, missing CJK glyphs, then iterate. If the model has no vision, this step is manual (or skipped) — generation/validation does not depend on it.

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
