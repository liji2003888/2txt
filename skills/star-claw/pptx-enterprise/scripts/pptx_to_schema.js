#!/usr/bin/env node
// .pptx -> Slide JSON via pptxtojson. LOSSY: masters/theme/SmartArt/animations are not preserved.
// For brand-fidelity export, do NOT round-trip through this — use template_fill.py against the original .potx.
const fs = require('fs');
const path = require('path');
const { parse } = require('pptxtojson');

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('usage: pptx_to_schema.js <in.pptx> <out.json>');
  process.exit(2);
}

(async () => {
  const buf = fs.readFileSync(args[0]);
  const result = await parse(buf);
  const deck = {
    meta: {
      title: path.basename(args[0], path.extname(args[0])),
      width: (result.size && result.size.width) || 960,
      height: (result.size && result.size.height) || 540,
    },
    slides: (result.slides || []).map((s, i) => ({
      id: `s${i}`,
      background: s.fill ? { type: 'solid', color: s.fill } : undefined,
      elements: (s.elements || []).map((el, j) => ({ id: `e${i}_${j}`, ...el })),
    })),
  };
  fs.writeFileSync(args[1], JSON.stringify(deck, null, 2));
  console.log(`wrote ${args[1]}`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
