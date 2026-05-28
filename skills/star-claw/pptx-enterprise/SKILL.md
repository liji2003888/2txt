---
name: pptx-enterprise
description: Generate enterprise-grade presentations (TCL brand) as .pptx and HTML, driven by a single Slide JSON Schema. Routes between PptxGenJS (from-scratch), python-pptx (brand-fidelity template fill), and a forked PPTist renderer (Web/online edit).
---

# pptx-enterprise

A Skill for enterprise PPT generation. The Slide JSON Schema (`schema/slide_schema.json`) is the single source of truth; renderers project it to `.pptx` and HTML, and a separate path fills branded `.potx` templates in place for pixel-perfect brand fidelity.

## Model-agnostic

This skill contains **no LLM calls** — every script is plain Python/Node. It works with any agent model (Qwen, DeepSeek, Claude, …); the model only needs to (1) write a small JSON outline or edit-ops file following the examples here, and (2) run the commands below. The outline parser is forgiving (missing fields default; a malformed slide falls back to a bullet slide instead of aborting), and `scripts/validate.py` reports any schema problem before rendering. Prefer copying the templates in `assets/examples/` and editing values, rather than composing JSON from scratch.

## 制作流程总纲 (Production pipeline — follow in order)

Approach every deck like a senior solution/presentation consultant: **content logic first, layout last.** Don't open the engine until you know what each slide must say. The pipeline:

**① 立意 (Frame the goal).** Pin down: 主题、目标(看完要让受众相信什么/做什么)、受众(懂行还是外行)、场景(汇报/培训/对外…)、篇幅、材料类型. Write the deck's **single governing message** in one sentence — every slide must serve it. Map the material type to a narrative framework (see *Material frameworks* below: 培训/汇报/方案/复盘/产品/战略).

**② 搭故事线 (Build the storyline — text only, no layout yet).**
- *If the user gave an outline or source material*: use it; fix gaps and ordering so the logic is MECE, 总分, and 结论先行.
- *If not*: **you design the outline.** Reason from goal+audience+framework about what sections it should contain and what question each section answers. Produce a slide-by-slide list where **each slide has one takeaway sentence** (the future title). Sanity-check the spine: one through-line, each section a sub-conclusion, the `agenda` mirrors the sections.

**③ 找素材 (Research with web_search).** Go through the storyline and mark each point as *已知可直接写* vs *需检索*. For the latter, invoke the OpenClaw **`web_search` skill** to fetch accurate facts, current data/statistics, real named examples, definitions, and the conventional structure for that topic; **summarize the results into slide-ready content** (concrete numbers, named cases — not vague claims). Also search & download **key images** (diagrams, screenshots, product/photos) to use via `image`/`imagecard`. Verify across sources; **never fabricate data** — if unverifiable, drop it or flag it.

**④ 定稿内容结构 (Lock the structure).** Fold the research back in; finalize section order and each slide's takeaway. For every slide decide its content load: **标题(结论)+ 主证据(数据/例子/图)+ 小结(banner)**. Cut anything that doesn't serve the governing message; split overloaded slides.

**⑤ 逐页布局 (Compose each slide).** For each slide: pick structure from the **content-shape map** (not default cards) → compose **2–3 elements into one point** (see *Compose each slide as ONE point*) → write copy **通俗易懂** → mark at most one key node red. Keep deck-wide **variety** (no repeat on consecutive slides; ≥6–10 distinct structures; cards ≤⅓).

**⑥ 自检与出片 (QA & render).** Run `python scripts/lint_variety.py outline.json` until `VARIETY OK`; `python scripts/validate.py deck.json`; render with **`node scripts/schema_to_pptx.js` (default, editable)**; if a renderer is available, `scripts/preview.js`/`render_inspect.py` to eyeball for overflow/overlap, then iterate.

**⑦ 终审 (Review against the goal).** Re-read against ① — does every slide advance the governing message? Is the conclusion unmistakable and (for reports) the ask explicit? Trim, then deliver.

Detailed rules for each phase are below.

## Authoring slides: prefer the auto-layout engine (compose a tree)

**To get designed, non-templated slides, author each slide as a layout TREE — do not just pick a fixed template.** A slide with a `"body"` tree is flowed by the auto-layout engine (`compose.py`): you decide the *structure*, the engine computes geometry (flexbox-style) so nothing overlaps and it adapts to the content. This is how to make decks that look bespoke rather than mechanical.

```json
{ "title": "页面标题", "banner": "可选底部金句",
  "body": { "type": "row", "gap": 20, "items": [ ...nodes... ] } }
```

Containers: `row` / `col` / `grid` (`gap`, `sizes` weights for row, `cols` for grid) — nest freely.
Components:
- text/containers: `text` (`text`/`size`/`bold`/`align`), `bullets` (`items`), `spacer`
- cards & panels: `card` (`title`/`body`/`icon`/`metric`/`tag`/`tone:light|blue|navy`/`accent`), `panel` (`title`/`tone`/`items:[...]`), `iconitem` (`icon`/`title`/`body`), `imagecard` (`src`/`title`/`body`), `personcard` (`avatar`/`name`/`role`/`quote`), `quote` (`text`/`author`/`tone`)
- numbers & emphasis: `stat` (`value`/`label`/`note`), `hero` (`kicker`/`value`/`label`)
- flows & structures: `arrowflow`/`steps` (`items:[{title,sub}]`), `timeline` (`items:[{date,title}]`), `milestone` (里程碑, alternating cards, `items:[{date,title,body}]`), `funnel` (`items:[{label,value}]`), `quadrant` (SWOT, `items:[4×{title,items}]`), `balance` (对比天平, `left`/`right`), `regions` (区域分布, `items:[{name,value}]`), `orgchart` (组织架构, `root`/`children:[{title,items}]`)
- progress & compare: `progresslist` (进度条, `items:[{label,value}]`), `pricing` (方案对比, `plans:[{name,price,items,featured}]`)
- charts: `chart` (`chartType`: column/bar/line/area/pie/donut/radar; `labels`/`series`), `gauge` (进度环, `value`/`label`), `image` (`src`)

Any item takes `"accent":"red"` (or `"black"`/hex) to mark a key node; icons always render white on chips.

### Material frameworks (deck-level logic — choose by material type)

Before composing slides, fix the **narrative skeleton** for the material type. A deck is an argument with a spine, not a pile of slides. Each framework lists the section flow, the golden rule, and the layout to use per section.

**培训 / 教学 (Training)** — 认知阶梯 What→Why→How→Example→Practice→Summary.
`cover → agenda → 是什么(hero/statement 下定义) → 为什么重要(stat/chart 给证据) → 怎么运作(arrowflow/architecture) → 能与不能(quadrant/balance) → 案例(imagecard/chart) → 上手三步(arrowflow/cards) → 一句话总结(quote) → closing`. 黄金法则:每页一个认知点,由浅入深,多用类比与对比。

**工作汇报 / 述职 (Report)** — 结论先行 (BLUF / 金字塔原理).
`cover → 一页结论(hero/statement:核心结论+3 论据) → 背景与目标(bullets/text) → 关键进展(timeline/chart+stat) → 数据成果(dashboard: chart+stat+gauge) → 问题与对策(comparison/quadrant) → 下一步与资源请求(arrowflow/bullets + banner) → closing`. 黄金法则:**先抛结论再展开**,数据支撑,最后给明确的 ask。

**方案 / 解决方案 (Solution proposal)** — SCQA + 总分.
`cover → 现状与痛点(bullets/regions/stat) → 目标(hero/statement) → 方案总览(architecture/house 一张全景图) → 关键设计(arrowflow/orgchart/grid 分点详述) → 价值与 ROI(stat/gauge/chart) → 实施路径(roadmap/gantt/milestone) → 风险与应对(quadrant/comparison) → 行动建议(banner) → closing`. 黄金法则:痛点要扎心,方案总览先给全景再拆解,价值要可量化。

**项目复盘 (Review / retro)** — 目标vs结果 → 归因 → 沉淀.
`cover → 目标 vs 结果(comparison/stat 对照) → 数据复盘(dashboard/chart) → 做对了什么(cards/bullets) → 问题与根因(quadrant/balance) → 改进项(progresslist/arrowflow) → 经验沉淀(quote/bullets) → closing`. 黄金法则:用数据对照目标,归因要到根,改进要可执行。

**产品介绍 (Product intro)** — 痛点→定位→能力→差异→证据→获取.
`cover → 用户痛点(statement/regions) → 产品定位(hero) → 核心能力(grid/iconitem 3–6) → 差异化(comparison/balance) → 案例与数据(imagecard/chart/stat) → 客户之声(personcard) → 获取方式(arrowflow/banner) → closing`. 黄金法则:从用户痛点切入而非功能罗列,差异化要鲜明,用案例与数字背书。

**战略 / 规划 (Strategy)** — 洞察→愿景→路径→举措→里程碑.
`cover → 外部洞察(chart/regions) → 机会与挑战(quadrant) → 愿景目标(hero/statement) → 战略框架(house 战略屋) → 关键举措(orgchart/cards) → 里程碑(roadmap/milestone) → 资源与组织(orgchart/stat) → closing`. 黄金法则:自上而下,用战略屋串起愿景-支柱-基础,举措对齐目标。

If the material doesn't match these, build a custom spine but keep the discipline: **一条主线、总分结构、每节一个小结论、首页给全局**. Mirror the chosen spine in the `agenda` slide.

### Compose each slide as ONE point, not a bare component

A slide is an argument, not a widget. **Never output a slide whose body is a single bare component** (one lone chart, one lone card grid, one lone bullet list). Every content slide combines **2–3 elements** arranged as:

> **【论点标题】** (the title states the conclusion, not the topic) + **【主视觉】** (the structure that proves it) + **【支撑/结论】** (a short takeaway, callouts, or context).

Composition recipes (combine, don't isolate):
- **数据页**: `chart` + 2–3 `stat`/`hero` callouts beside it (`row` `sizes:[2,1]`) + a one-line `banner` takeaway. Not a chart alone.
- **结论页**: `hero`/`statement` (the claim) + `bullets` of 3 reasons beside or below it.
- **流程/架构页**: the `arrowflow`/`orgchart`/`architecture` diagram + a `banner` saying what it means ("所以…").
- **对比页**: `balance`/`comparison` + a verdict line (`banner` or a short `text`).
- **要点页**: a `grid` of cards/iconitems, **but** lead with a 1-line framing `text` above and close with a `banner` — so it argues, not just lists.
- Use `sizes` for asymmetry (`[2,1]`, `[3,2]`), mix a left structure with a right support column. Title should be a sentence ("AI 不取代人,但放大人"), not a label ("AI 介绍").

Every slide must answer: *what's the ONE takeaway?* Put it in the title or the banner.

### Write it 通俗易懂 (plain language)

The audience is usually busy non-experts — make every slide instantly understandable:
- **大白话优先**:用日常说法,避免术语堆砌。必须用专业词时,紧跟一句类比或解释("Token,就是模型眼里的‘字’")。
- **多用类比、例子、数字**:抽象概念配一个具体例子或贴切类比;能用数字就用数字("省下 1 小时/天"胜过"显著提效")。
- **短句、口语**:一句话讲一件事;标题写成人能脱口而出的结论句,不是名词标签。
- **一页一个意思**:信息过载就拆成两页;宁可页多,不要一页塞满。
- **贴近受众场景**:面向一线同事就讲他们的日常痛点与工具,不堆理论。
- 正文每条都要"读完就懂",读者不需要再脑补。

### Pick the layout from the CONTENT SHAPE (do not default to cards)

The #1 failure mode is **every slide becoming a card/grid** → a monotonous "AI-flavored" deck. Avoid this: read what each slide is *doing* and pick the matching structure. Reference map:

| Content shape | Use (NOT cards) |
|---|---|
| One definition / key idea / takeaway | `hero` (big term + explanation) or `statement`/`quote` — one focal slide, lots of whitespace |
| A sequence / workflow / steps | `arrowflow` / `process` / `timeline` / `milestone` |
| Two things compared | `balance` / `comparison` / two `panel`s in a `row` (one blue, one navy) |
| Pros/cons, 2×2, SWOT | `quadrant` |
| Taxonomy / hierarchy / org | `orgchart` / `hierarchy` |
| Layered system / architecture | `architecture` / `house` |
| Numbers / metrics / KPIs | `stat` row, `hero`, `gauge`, `chart` |
| Distribution / ranking / proportion | `chart` (bar/pie/donut/radar), `regions`, `heatmap` |
| Progress / maturity | `progresslist`, `gauge` |
| 3–6 parallel features (cards OK here) | `grid` of `card`/`iconitem` — but only ~1 in every 3–4 slides |
| A testimonial / voice | `personcard` |
| A funnel / conversion | `funnel` |

### Hard variety rules (self-check before finishing)

1. **Never use the same primary structure on two consecutive content slides.** If slide N is a card grid, slide N+1 must be something else.
2. **For a deck of ≥10 slides, use at least 6 distinct layout/component types** as the slide's primary structure. For ~20 slides, aim for 8–10 distinct types.
3. **Cap cards/grids at ~⅓ of content slides.** When you catch yourself writing another card grid, convert it: a "types of X" list → `arrowflow` if sequential, `quadrant` if it's 4, `orgchart` if hierarchical, `hero`+`bullets` if one matters most.
4. **Insert focal/breather slides.** Every few dense slides, add a `statement`/`quote`/`hero` single-idea slide and a `section` divider — varies rhythm and reads less mechanical.
5. **Vary internal composition too:** alternate `row` vs `col` roots, use `sizes` (e.g. `[2,1]`) for asymmetry, mix `panel`/`iconitem`/`stat`, not always equal-width cards.
6. Accent colors rotate automatically (tech-blue series); set `"accent":"red"` on **one** key node per slide at most. Icons are white on chips, never black. Keep body text short.

Before returning a multi-slide deck, run **`python scripts/lint_variety.py <outline.json>`** — it classifies each slide's primary structure and FAILS if structures repeat consecutively, too few distinct types are used, or cards/grids exceed ⅓. Fix any flagged slides using the content-shape map above, then re-run until it reports `VARIETY OK`. See `assets/examples/training_deck.json` for a worked 12-slide deck where every slide uses a different structure (it passes the linter).

The fixed-template layouts below (`cards`, `process`, `kpi`, …) are quick presets, but the **tree is the primary path** — and even with presets, obey the variety rules.

## When to use which path

Choose by input:

### Two ways to render a generated deck to .pptx

**RULE: default to `schema_to_pptx.js` (PptxGenJS).** Generate with PptxGenJS unless the user explicitly asks for the master path — every shape/text/table is a native editable PowerPoint object (charts/icons are embedded images), works for any theme, and draws the full brand chrome itself.

- **`node scripts/schema_to_pptx.js deck.json out.pptx` (PptxGenJS — DEFAULT)** — draws everything from primitives, including the brand chrome (corner badge, logo, dark title + divider) and the cover background image. No template needed; output is fully editable. **Use this by default.**
- **`python scripts/schema_to_pptx_tpl.py deck.json out.pptx` (python-pptx, master — opt-in)** — only when the user wants pixel-perfect master chrome. Renders the body onto slides created from the master template's layouts; corner badge / logo / slide number / cover background come from the master. Theme sets `baseTemplate` + layout names. Elements tagged `role:"chrome"`/`"coverbg"`/`"headerline"` are skipped (master provides them). Charts are pre-rendered to PNG so they embed here too.

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
