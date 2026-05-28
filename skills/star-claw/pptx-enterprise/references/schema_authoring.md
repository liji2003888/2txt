# Slide Schema authoring guide

## Canvas

All coordinates are pixels on a 960×540 canvas (16:9). Renderers map to PowerPoint's 13.333×7.5 in.

## Element types

| Type | Required props | Notes |
|---|---|---|
| `text` | `content` (HTML) | Use `<ul><li>` for bullets, `<strong>` for bold, `style="text-align:center"` for centering. |
| `image` | `src` | Path or URL. `fixedRatio: true` to preserve aspect. |
| `shape` | `shapeType` | One of `rect`, `roundRect`, `ellipse`, `triangle`, `diamond`, `arrow`, `star`. Optional inline `text`. |
| `line` | `start`, `end` | Offsets relative to `(left, top)`. |
| `table` | `data` | 2D array of `{text}` cells. |
| `chart` | `chartType`, `data` | `chartType` ∈ `bar`/`line`/`pie`/`area`/`scatter`. `data` = `{labels[], series[{name, values}]}`. |
| `latex` | `path` | Pre-rendered SVG path; keep original `latex` for editing. |

All elements share `{id, type, left, top, width, height, rotate}`.

## Placeholder convention (for template fill)

When authoring a `.potx` template for `template_fill.py`:

- Name each placeholder explicitly in PowerPoint's Selection Pane using `{{section.field}}` form, e.g. `{{title.main}}`, `{{kpi.revenue}}`, `{{body.bullets}}`.
- Keep placeholder names stable across template versions — they are the contract with the content JSON.
- Avoid embedding sample text in placeholders that you don't want to leak; python-pptx replaces text content but cannot redo autofit on text that overflows a fixed-size placeholder.

Content JSON shape for `template_fill.py`:

```json
{
  "slides": {
    "0": { "{{title.main}}": "Q4 Business Review", "{{title.sub}}": "December 2025" },
    "1": { "{{body.bullets}}": ["Revenue +18% YoY", "GP margin 27.4%", "Cash from ops $1.2B"] }
  }
}
```

## Common pitfalls

- **Text overflow**: PowerPoint may autofit but the browser will clip. Cap bullets at ~6 items at body sizes; run `render_inspect.py` and verify.
- **CJK fonts**: set `defaultFontName` to `Noto Sans CJK SC` or `Source Han Sans` to guarantee glyph coverage in headless rendering. Without it, soffice silently substitutes and Chinese turns into boxes.
- **Color**: always include the leading `#`. Renderers strip it for OOXML; missing `#` will produce malformed XML or unexpected colors.
- **Round-trip loss**: `pptx_to_schema.js` (pptxtojson) discards masters/theme/SmartArt/animations. Never use it as the source for final brand-fidelity export.
