# PptxGenJS cookbook (for `schema_to_pptx.js`)

## Units

PptxGenJS uses inches by default. `schema_to_pptx.js` defines a custom layout `OC16x9` at 13.333×7.5 in and converts px → in at slide load time. Schema coordinates stay in px so the same JSON works for the Web renderer.

## Common patterns

- **Title slide**: one centered `text` element with `<strong>` content at 44pt; optional subtitle at 20pt.
- **Bulleted body**: a `text` element whose `content` is `<ul><li>...</li></ul>`. The script splits `<li>` items and emits PptxGenJS bullets with `{ bullet: true }`.
- **Section divider**: solid-color slide `background` + single centered white text element at ~40pt.
- **Two-column**: two `text` elements side by side, each `width: 420`, `left: 60` and `left: 480`.
- **Chart**: emit a `chart` element; `data.series` is mapped to PptxGenJS's series format with shared `labels`.
- **Embedded image**: `image` element with `src` as a path resolvable at render time (absolute path inside the sandbox is safest).

## Where this script falls short

- Animations and SmartArt are not emitted (PptxGenJS doesn't author them).
- Master slides / theme inheritance — PptxGenJS builds from primitives; there is no real theme application.
- Text autofit — text that doesn't fit its box will be clipped, not shrunk. Run `render_inspect.py` and shrink fontSize / increase box height when overflow is visible.

For any of the above, use `template_fill.py` against a designer-authored `.potx`.
