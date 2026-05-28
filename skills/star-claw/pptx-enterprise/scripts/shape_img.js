#!/usr/bin/env node
// Render one shape with a linear gradient (+ optional soft glow) to a transparent PNG via resvg.
// Gives premium gradient fills while keeping text native/editable (text is drawn separately).
// usage: shape_img.js <manifest.json>   manifest: [{shape,w,h,c1,c2,angle,glow,radius,out}, ...]
const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');

function buildSvg(it) {
  const w = it.w, h = it.h;
  const pad = it.glow ? Math.round(Math.min(w, h) * 0.12) : 2;
  const W = w + pad * 2, H = h + pad * 2;
  const c1 = it.c1 || '#2E7BFF', c2 = it.c2 || '#0E5FD8';
  const ang = (it.angle == null ? 120 : it.angle) * Math.PI / 180;
  const dx = Math.cos(ang), dy = Math.sin(ang);
  const x1 = 50 - dx * 50, y1 = 50 - dy * 50, x2 = 50 + dx * 50, y2 = 50 + dy * 50;
  const defs = `<linearGradient id="g" x1="${x1}%" y1="${y1}%" x2="${x2}%" y2="${y2}%">`
    + `<stop offset="0%" stop-color="${c1}"/><stop offset="100%" stop-color="${c2}"/></linearGradient>`
    + (it.glow ? `<filter id="gl" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="${pad * 0.5}"/></filter>` : '');
  const shape = it.shape || 'roundRect';
  let body = '';
  const X = pad, Y = pad;
  const geom = (fill, extra = '') => {
    if (shape === 'ellipse') return `<ellipse cx="${X + w / 2}" cy="${Y + h / 2}" rx="${w / 2}" ry="${h / 2}" fill="${fill}"${extra}/>`;
    if (shape === 'chevron') { const tip = Math.min(h * 0.5, w * 0.3); return `<polygon points="${X},${Y} ${X + w - tip},${Y} ${X + w},${Y + h / 2} ${X + w - tip},${Y + h} ${X},${Y + h} ${X + tip},${Y + h / 2}" fill="${fill}"${extra}/>`; }
    if (shape === 'trapezoid') { const ins = w * 0.18; return `<polygon points="${X + ins},${Y} ${X + w - ins},${Y} ${X + w},${Y + h} ${X},${Y + h}" fill="${fill}"${extra}/>`; }
    const r = shape === 'roundRect' ? (it.radius || Math.min(w, h) * 0.12) : 0;
    return `<rect x="${X}" y="${Y}" width="${w}" height="${h}" rx="${r}" fill="${fill}"${extra}/>`;
  };
  if (it.glow) body += geom(c1, ` opacity="0.35" filter="url(#gl)"`);
  body += geom('url(#g)');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs>${defs}</defs>${body}</svg>`;
}

const mf = process.argv[2];
if (!mf) { console.error('usage: shape_img.js <manifest.json>'); process.exit(2); }
const items = JSON.parse(fs.readFileSync(mf, 'utf-8'));
let ok = 0;
for (const it of items) {
  try {
    const png = new Resvg(buildSvg(it), { fitTo: { mode: 'width', value: Math.round((it.w + (it.glow ? it.w * 0.24 : 4)) * 2) } }).render().asPng();
    fs.writeFileSync(it.out, png);
    ok++;
  } catch (e) { console.error('shape failed:', e.message); }
}
console.log(`rendered ${ok}/${items.length} gradient shapes`);
