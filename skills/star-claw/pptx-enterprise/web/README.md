# web/ — Forked PPTist (AGPL-3.0)

This directory hosts a fork of [PPTist](https://github.com/pipipi-pikachu/PPTist), used for:

- Online slide editing in the OpenClaw web shell (the "五星AI岛" iframe target)
- HTML rendering driven by `../schema/slide_schema.json`

The standalone `../scripts/schema_to_html.js` is a QA-only fallback, not a substitute for this renderer.

## Why isolated here

PPTist is AGPL-3.0. Per the architecture decision, this fork:

1. Is confined to `web/` and interacts with the rest of the Skill **only through the Slide JSON Schema**.
2. Treats the Schema as the swap point — if deployment ever shifts external/commercial, this directory can be replaced with a non-AGPL renderer without touching anything else in the Skill.

See `../references/agpl_notice.md` before merging the fork.

## Setup (to be performed in implementation)

1. Fork `https://github.com/pipipi-pikachu/PPTist` into the org's internal GitLab.
2. Add the fork at this path: `git subtree add --prefix=skills/star-claw/pptx-enterprise/web <internal-pptist-remote> main --squash`.
3. Strip features not needed (printing, mobile shell) per the integration contract below.
4. Replace PPTist's default slide store loader with one that reads the OpenClaw Slide JSON Schema directly — the schemas are compatible by design (`schema/slide_schema.json` adopts the PPTist element model).
5. Build: `pnpm install && pnpm build` → output in `web/dist/`.
6. The web shell loads `web/dist/index.html` in an iframe and passes deck JSON via `postMessage`.

## Integration contract

- **Input**: `postMessage({type: 'load', deck})` where `deck` conforms to `../schema/slide_schema.json`.
- **Editor changes**: emit `postMessage({type: 'change', deck})` on debounced edits.
- **Export**: on user request, emit `postMessage({type: 'export', format: 'pptx', data: ArrayBuffer})`. The exporter inside PPTist (which uses PptxGenJS internally) is acceptable here; for brand-fidelity exports of templated decks, the host should instead call `scripts/template_fill.py` against the original `.potx`.
- **Network**: the embedded PPTist must NOT call any endpoint not listed in `web/ALLOWED_HOSTS.txt`.

## Files to add when the fork lands

- `LICENSE.AGPL-3.0` at this directory root
- `NOTICE` listing PPTist's copyright and our modifications
- `ALLOWED_HOSTS.txt` enumerating permitted outbound hosts
- `MODIFICATIONS.md` summarizing what we changed (required to make source-availability meaningful)
