---
name: pptx-enterprise
description: Generate enterprise-grade presentations (TCL brand) as editable .pptx. Work in two phases like Kimi/Claude — first design the full written content (outline → per-section detail → per-page concrete text/data + layout), then render via PptxGenJS. Also edits existing .pptx and fills branded templates.
---

# pptx-enterprise

A Skill for enterprise PPT generation. **Content logic first, layout last.** The model writes a per-page content+layout plan, expressed as a Slide JSON layout-tree; the auto-layout engine + PptxGenJS render it to an editable `.pptx`. A separate path fills/edits branded templates for pixel-perfect fidelity.

## Model-agnostic

This skill contains **no LLM calls** — every script is plain Python/Node. It works with any agent model (Qwen, DeepSeek, Claude, …); the model only needs to (1) write a JSON outline/layout-tree, and (2) run the commands below. The outline parser is forgiving (missing fields default; a malformed slide falls back to a bullet slide instead of aborting), and `scripts/validate.py` reports any schema problem before rendering.

> **范例只是参考,不是模板。** `assets/examples/` 里的 deck 用来传达「叙事骨架 + 组合手法 + 质量基线」,**不要照抄**。每次都要针对真实主题、目标、受众和检索到的内容,**自己设计**这份片子:重新组织结构、自拟结论句、按本次内容选版式与组件、调整配比。范例是起跳板,模型的设计能力才是主体 —— 内容、构图、版式组合都应是为这次需求量身做的,而非填空。

## 制作流程:先内容,后排版(两阶段,像 Kimi/Claude)

**铁律:内容逻辑完整 > 样式多样。** 先把"要讲什么"想全、写实,再渲染。两个最常见的失败都要避免:① 内容稀薄的"骨架页"(只有标题 + 几个名词 + 大片留白);② 为凑版式多样,把一个本该展开 2–4 页的章节硬压成一页。

### 阶段一 · 内容设计(纯文字,先不碰渲染引擎)

1. **立意**:确定 主题 / 目标(看完让受众相信什么、做什么)/ 受众 / 场景 / 篇幅 / 材料类型;一句话写出**全篇唯一主张**。按材料类型选叙事框架(见 *Material frameworks*)。
2. **详细大纲**:列出章节 → 每章要回答的核心问题 → **每章预计几页**。**一个章节通常 2–5 页,不是只能一页** —— 该展开就展开(现状一页讲背景、一页讲痛点数据;方案一页总览、几页拆解关键模块)。`agenda` 镜像章节。
3. **检索补料(web_search)**:逐条标注 *已知可直接写* vs *需检索*;对后者用 OpenClaw `web_search` 取**真实事实/最新数据/实名案例/定义**,并**总结成可上页的句子和数字**;搜并下载**关键图片**(架构图/截图/产品图)经 `image`/`imagecard` 用上。多源核实,**绝不编造数据**。
4. **逐页内容稿(关键产物)**:为**每一页**写出**真实、完整的内容** —— 标题(结论句)+ 这一页实际要呈现的要点/短段落/数据/示例(**写出真句子,不是占位词**)+ 标注该页用什么版式/组件。内容要"讲透";宁可多开一页,也不要半页空白或一堆光秃秃的名词。

> **阶段一自检(过不了不进阶段二)**:通读逐页内容稿——逻辑是否完整闭环?有没有"骨架页"(只有标题+几个名词)?信息密度是否对得起一页 A4?有问题就补内容或合并。

### 阶段二 · 渲染出片(PptxGenJS)

5. **逐页排版**:把内容稿翻成布局树 JSON —— 按 **content-shape map** 选版式、把元素**组合成一个论点**、**通俗易懂**改写文案、至多一个红色关键点。
6. **渲染**:`node scripts/schema_to_pptx.js deck.json out.pptx`(默认,原生可编辑)。
7. **QA bug-hunt + 终审**:见 *QA is a bug hunt*。修完复验,再对照唯一主张终审(每页是否推进主张、结论是否清晰、汇报类 ask 是否明确)。

各阶段细则见下文。

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
- flows & structures: `arrowflow`/`steps` (`items:[{title,sub}]`), `timeline` (`items:[{date,title}]`), `milestone` (里程碑, alternating cards, `items:[{date,title,body}]`), `funnel` (`items:[{label,value}]`), `quadrant` (SWOT, `items:[4×{title,items}]`), `balance` (对比天平, `left`/`right`), `regions` (区域分布, `items:[{name,value}]`), `orgchart` (组织架构, `root`/`children:[{title,items}]`), `architecture` (技术架构, `layers:[{name,items}]`), `house` (战略屋, `roof`/`pillars:[{title,items}]`/`base`)
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

Reference decks (one per material type) live in `assets/examples/` — `training_deck` / `report_deck` / `solution_deck` / `review_deck` / `product_deck` / `strategy_deck`. Read the matching one to absorb its spine and composition quality, **then design your own** for the real content (see the "范例只是参考" note above).

### Each page = one clear message, fully fleshed out (never sparse)

A slide is an argument, not a widget. Two rules:

1. **填满,别留白.** Never ship a thin "skeleton" page (a title + 3–4 lone words + huge empty space). Every content slide combines **2–3 elements** and carries real substance: **【论点标题(结论句)】 + 【主视觉(证明它的结构)】 + 【支撑/数据/示例 + 小结 banner】**. If a topic deserves depth, **give it more pages** — don't compress it into one bare page.
2. **不要裸组件.** Don't output a body that's a single lone chart / lone card grid / lone bullet list — combine it with context (callouts, a framing line, a takeaway banner).

Composition recipes (combine, don't isolate):
- **数据页**: `chart` + 2–3 `stat`/`hero` callouts (`row` `sizes:[2,1]`) + a `banner` takeaway.
- **结论页**: `hero`/`quote` claim + `bullets` of 3 reasons beside/below.
- **流程/架构页**: the `arrowflow`/`orgchart`/`architecture` diagram + a `banner` saying what it means.
- **对比页**: `balance`/two `panel`s + a verdict line.
- **要点页**: a `grid` of cards/iconitems, **with** a 1-line framing `text` above + a `banner` below — so it argues, not just lists.
- Use `sizes` for asymmetry (`[2,1]`, `[3,2]`). Titles are sentences ("AI 不取代人,但放大人"), not labels ("AI 介绍").

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

### Variety — secondary to content, but avoid true monotony

Content completeness comes first; variety is the tie-breaker, not a goal that overrides depth.

- **Pick the structure that fits each page's content** (use the content-shape map). When pages genuinely differ, their structures will naturally differ.
- **A section may span multiple pages, and adjacent pages MAY share a structure** when the content calls for it (e.g. two card grids in 核心能力). That is fine — do NOT distort content just to vary.
- **What to actually avoid:** a whole deck that is overwhelmingly one structure (every page a card grid). Mix in `hero`/`quote`/`statement` focal pages and `section` dividers for rhythm.
- Accent colors rotate automatically; set `"accent":"red"` on at most one key node per slide. Icons are white on chips, never black.

`python scripts/lint_variety.py <outline.json>` flags only **true monotony** (>=6 content slides that are <4 distinct structures, or >55% cards, or one structure on >60% of slides) — it no longer penalizes multi-page sections or adjacent repeats. Examples in `assets/examples/` show the quality bar.

## When to use which path

Choose by input:

### Two ways to render a generated deck to .pptx

**RULE: default to `schema_to_pptx.js` (PptxGenJS).** Generate with PptxGenJS unless the user explicitly asks for the master path — every shape/text/table is a native editable PowerPoint object (charts/icons are embedded images), works for any theme, and draws the full brand chrome itself.

- **`node scripts/schema_to_pptx.js deck.json out.pptx` (PptxGenJS — DEFAULT)** — draws everything from primitives, including the brand chrome (corner badge, logo, dark title + divider) and the cover background image. No template needed; output is fully editable. **Use this by default.**
- **`python scripts/schema_to_pptx_tpl.py deck.json out.pptx` (python-pptx, master — opt-in)** — only when the user wants pixel-perfect master chrome. Renders the body onto slides created from the master template's layouts; corner badge / logo / slide number / cover background come from the master. Theme sets `baseTemplate` + layout names. Elements tagged `role:"chrome"`/`"coverbg"`/`"headerline"` are skipped (master provides them). Charts are pre-rendered to PNG so they embed here too.

To add or update the master: strip example slides from a branded `.pptx` (keep masters/layouts) and point `baseTemplate` at it; set `contentLayout`/`coverLayout` to the layout names (see `python scripts/dump_pptx.py` / list via python-pptx `slide_layouts`).

### 1. From scratch — the layout-tree path (primary)

Write the deck JSON yourself (a `title`/meta + `slides`, each a `body` tree as in *Authoring slides* above), then:

```bash
python scripts/outline_to_schema.py deck.json > out.deck.json   # resolves icons/charts/gradients + adds chrome
python scripts/validate.py out.deck.json                        # JSON check before render
node   scripts/schema_to_pptx.js out.deck.json out.pptx         # render (default, editable)
```

`outline_to_schema.py` also accepts slides that name a fixed `layout` (e.g. `cover`/`agenda`/`section`/`closing`, plus presets like `cards`/`process`/`dashboard`/`timeline`/`matrix`/`pyramid`/`gantt`/`roadmap`/`cases` …). Use those for chrome slides and as quick presets; for content slides prefer `body` trees. Slides may also carry `"banner"` (a navy + red-cap takeaway bar) and `"notes"` (speaker notes); shapes support `"shadow": true`.

**Branding is automatic & always applied.** With the default theme, every content page gets the TCL chrome (red corner badge + olympic logo + standard header), and if your outline has no `cover` slide one is **auto-prepended** using the outline's top-level `title`/`dept`/`author`/`meta` — so every generated deck opens with the brand cover and is branded throughout. Put `dept`/`author`/`meta` at the outline root to fill the cover; add your own `{"layout":"cover",...}` slide to override.

**Themes** — 2nd arg to `outline_to_schema.py`; default `assets/themes/tcl_feishu.json` (flat blue `#1668DC` + navy `#1A2332` + red key + light panels, 微软雅黑, TCL chrome). Also `ocean`/`midnight`/`mono` and `tcl_branding.json`. A theme sets `themeColors` + optional `fontColor`/`backgroundColor`/… + `logo`/`badgeColor` chrome. On brand themes every content page gets the standard header (dark-navy bold title + thin gray divider + red corner badge + logo); `cover`/`full` slides omit corner chrome.

**Icons** — any item's `"icon": "lucide/search"` / `"icon-park/people"` (sets: `lucide`, `icon-park-outline`, `icon-park`). Recolored to white on colored chips (never black), rasterized + cached. Unknown name drops gracefully. Browse names on iconify.design.

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

### 4. QA is a bug hunt, not a confirmation — assume there ARE problems

Your first render is almost never perfect. If you found zero issues, you weren't looking hard enough. Run all three checks and a fix-verify loop before declaring done:

**a) Variety QA** — `python scripts/lint_variety.py outline.json` → must say `VARIETY OK`.

**b) Content QA** — extract the rendered text and scan it:
```bash
python -m markitdown out.pptx        # or: python scripts/dump_pptx.py out.pptx
python -m markitdown out.pptx | grep -iE "lorem|ipsum|xxxx|占位|示例|标题文字|your title|请单击"
```
If the grep matches, you left placeholder/filler text — fix it. Also check for missing content, typos, wrong order, fabricated numbers.

**c) Visual QA** — render every slide and inspect:
```bash
python scripts/preview_all.py deck.json out.preview/     # resvg, no LibreOffice (default)
# or, if LibreOffice is available: python scripts/render_inspect.py out.pptx
```
If the agent model has vision (or a fresh-eyes **subagent** is available — strongly preferred, you've been staring at the JSON and will see what you expect), inspect each PNG against this checklist:
- Overlapping elements (text through shapes, lines through words, stacked boxes)
- Text overflow / clipped at a box or slide edge; a box too narrow causing ugly wrapping
- A title that wrapped to 2 lines but the divider/elements were placed for 1
- Footer/banner/citation colliding with content above
- Gaps < ~14px or wildly uneven gaps; insufficient margin from slide edges
- Columns/cards not aligned; low-contrast text or icons (light on light / dark on dark)
- Leftover placeholder content

**Verification loop:** list issues → fix → **re-render the affected slides and look again** (one fix often creates another) → repeat until a full pass is clean. Don't declare success until you've completed at least one fix-and-verify cycle. (No vision and no subagent? Rely on `lint_variety` + content grep + the engine's auto-layout, and say you couldn't do visual QA.)

## Schema essentials

`schema/slide_schema.json` adopts the PPTist element model:

- Canvas in pixels (default 960×540, 16:9). The renderers map to PowerPoint's 13.333×7.5 in.
- Element types: `text` (HTML content), `image`, `shape`, `line`, `table`, `chart`, `latex`.
- All elements share `{id, type, left, top, width, height, rotate}`.

See `references/schema_authoring.md` for authoring guidance and pitfalls.

## Utility scripts (full .pptx lifecycle)

| Need | Command |
|---|---|
| Generate (default, editable) | `node scripts/schema_to_pptx.js deck.json out.pptx` |
| Generate on TCL master | `python scripts/schema_to_pptx_tpl.py deck.json out.pptx` |
| Variety lint (anti-monotony) | `python scripts/lint_variety.py outline.json` |
| Validate JSON deck | `python scripts/validate.py deck.json` |
| **Validate output .pptx (OOXML integrity)** | `python scripts/validate_pptx.py out.pptx` |
| **Extract text + notes (content QA)** | `python scripts/extract_text.py out.pptx` |
| Render every slide to PNG | `python scripts/preview_all.py deck.json out.preview/` |
| **One-glance thumbnail grid** | `python scripts/thumbnail.py deck.json grid.png` |
| Render one slide (no LibreOffice) | `node scripts/preview.js deck.json N out.png` |
| Inspect existing deck | `python scripts/dump_pptx.py in.pptx` |
| Edit existing deck (high-level ops) | `python scripts/edit_pptx.py in.pptx ops.json out.pptx` |
| **Deep OOXML edit (any XML)** | `python scripts/unpack_pptx.py in.pptx dir/` → edit → `python scripts/pack_pptx.py dir/ out.pptx` |
| Fill a branded template | `python scripts/template_fill.py tpl.pptx content.json out.pptx` |

Charts (`column`/`bar`/`line`/`area`/`pie`/`donut`/`radar`) are emitted as **native, editable** PowerPoint charts on both render paths; `gauge` (custom ring) is rasterized. Images support `"sizing": {"type": "cover"|"contain"|"crop"}`. Slides take `"notes"` for speaker notes.

## Output trade-off (be honest with users)

The two outputs are **content-consistent, not pixel-consistent**. PowerPoint and browser engines differ in line-wrapping, font metrics, and autofit. For brand-pixel-perfect deliverables, path 2 (template fill) is authoritative; the HTML rendering is for review/embedding.

## Branding

`assets/tcl_branding.json` holds brand colors, font, and logo path. `outline_to_schema.py` and `schema_to_pptx.js` both read it (or default if absent).

## Sandbox requirements & self-check

- Python ≥ 3.9 with `python-pptx`, `jsonschema` (see `requirements.txt`); optional `markitdown[pptx]` for content QA (text extraction)
- Node ≥ 18 with `pptxgenjs`, `pptxtojson`, `@resvg/resvg-js`, `@iconify-json/*` (see `package.json`)
- Visual QA renders to PNG via **resvg (`preview_all.py`, no extra deps)** by default; `render_inspect.py` additionally needs `soffice` + poppler-utils for a true PowerPoint render
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

## Deploying into OpenClaw (no surprises)

- **Self-contained & portable** — all scripts resolve paths relative to the skill dir (no hardcoded `/home`/`/tmp`). Drop the folder into your skills directory as-is.
- **Don't copy `node_modules`** (it's ~23MB and gitignored). On first use run `bash setup.sh` (or `npm install` + `pip install -r requirements.txt`) inside the skill dir.
- **No heavy/system deps for the core path** — generating a `.pptx` needs only Node + Python. `LibreOffice`/`poppler` are optional, only for the LibreOffice-based QA render; default QA uses `preview_all.py` (resvg, bundled). `markitdown` is optional.
- **No bundled third-party AGPL/GPL code** — output uses PptxGenJS (MIT) / python-pptx (MIT); icons are ISC/Apache-2.0. Nothing here imposes copyleft on your decks.
- **Distinct skill name** `pptx-enterprise` — won't collide with a generic `pptx` skill; its description triggers on PPT/deck/slide requests.

## 通用 PPT 设计技巧 (apply on top of the engine)

The engine already enforces alignment, consistent spacing, one font, and the brand palette. Spend your judgment on the things it can't decide:

- **视觉层级**:每页一个焦点。用大小/粗细/颜色拉开主次 —— 标题 26–28pt、节标题 18–20、正文 13–15、注释 11–12;关键数字放大成 `hero`/`stat`。
- **CRAP 四原则**:对比(Contrast,重要的就让它显眼)、重复(Repetition,全篇同一套卡片/间距/配色)、对齐(Alignment,用 `row/col/sizes`,左对齐正文)、亲密(Proximity,相关的靠拢成组、无关的拉开)。
- **少字、说人话**:正文不写整段;标题写结论句不写名词;一条要点一句话(参见"通俗易懂")。
- **数字优先**:用具体数字和实名案例胜过形容词("省 1 小时/天">"显著提效")。
- **数据诚实**:图表从 0 起轴、标单位、别用 3D/花哨装饰;一图说明一件事。
- **颜色克制**:主蓝统治画面,红色只点睛(每页 ≤1 处);深色块上文字/图标用白色。
- **留白有度**:不要填满每一寸,但更不能空洞 —— 内容不够就合并、够多就拆页(内容优先)。
- **首尾有力**:封面点题、`agenda` 给全局、`section` 分隔换节奏、结尾给结论或行动号召。
