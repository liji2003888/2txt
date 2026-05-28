#!/usr/bin/env node
// Render Iconify icons to recolored PNGs.
//   batch:  node icon.js <manifest.json>     (manifest: [{set,name,color,size,out}, ...])
//   single: node icon.js <set> <name> <#color> <size> <out.png>
// Sets: lucide, icon-park-outline (monochrome), icon-park (multicolor).
const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');

const PKG = {
  'lucide': '@iconify-json/lucide/icons.json',
  'icon-park': '@iconify-json/icon-park/icons.json',
  'icon-park-outline': '@iconify-json/icon-park-outline/icons.json',
};
const cache = {};
function load(set) {
  if (!cache[set]) {
    if (!PKG[set]) throw new Error('unknown icon set: ' + set);
    cache[set] = require(PKG[set]);
  }
  return cache[set];
}

function buildSvg(set, name, color) {
  const j = load(set);
  const ic = j.icons[name];
  if (!ic) return null;
  const w = ic.width || j.width || 24;
  const h = ic.height || j.height || 24;
  const left = ic.left || 0;
  const top = ic.top || 0;
  let body = ic.body;
  let root;
  if (set === 'lucide') {
    root = `fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
  } else {
    // Force monochrome in the target color so NO icon ever renders black:
    // recolor currentColor + every hardcoded fill/stroke hex (e.g. icon-park multicolor's #333/#000),
    // while preserving fill="none"/stroke="none".
    body = body
      .split('currentColor').join(color)
      .replace(/(fill|stroke)="#[0-9a-fA-F]{3,8}"/g, `$1="${color}"`)
      .replace(/(fill|stroke):\s*#[0-9a-fA-F]{3,8}/g, `$1:${color}`);
    root = `fill="${color}" stroke="${color}"`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${left} ${top} ${w} ${h}" ${root}>${body}</svg>`;
}

function render(set, name, color, size, out) {
  const svg = buildSvg(set, name, '#' + String(color).replace('#', ''));
  if (!svg) {
    console.error('missing icon: ' + set + '/' + name);
    return false;
  }
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: size } }).render().asPng();
  fs.writeFileSync(out, png);
  return true;
}

const args = process.argv.slice(2);
if (args.length === 1) {
  const manifest = JSON.parse(fs.readFileSync(args[0], 'utf-8'));
  let ok = 0;
  for (const it of manifest) {
    if (render(it.set, it.name, it.color, it.size || 128, it.out)) ok++;
  }
  console.log(`rendered ${ok}/${manifest.length} icons`);
} else if (args.length >= 5) {
  render(args[0], args[1], args[2], parseInt(args[3], 10), args[4]);
} else {
  console.error('usage: icon.js <manifest.json>  |  icon.js <set> <name> <#color> <size> <out.png>');
  process.exit(2);
}
