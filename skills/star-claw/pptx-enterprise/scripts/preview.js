#!/usr/bin/env node
// Visual QA without LibreOffice: render ONE slide of a deck JSON to PNG via SVG + resvg-js.
// usage: preview.js <deck.json> <slideIndex> <out.png>
const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');
const { chartInner } = require('./chart_img.js');

const [deckPath, idxStr, outPath] = process.argv.slice(2);
if (!deckPath || !outPath) {
  console.error('usage: preview.js <deck.json> <slideIndex> <out.png>');
  process.exit(2);
}
const deck = JSON.parse(fs.readFileSync(deckPath, 'utf-8'));
const W = (deck.meta && deck.meta.width) || 960;
const H = (deck.meta && deck.meta.height) || 540;
const slide = deck.slides[parseInt(idxStr || '0', 10)];

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const stripHtml = (h) =>
  String(h).replace(/<br\s*\/?>/gi, '\n').replace(/<\/(p|li|div)>/gi, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim();
const dataUri = (src) => {
  try {
    if (/^data:/.test(src)) return src;
    const b = fs.readFileSync(src);
    const e = (src.split('.').pop() || 'png').toLowerCase();
    const m = e === 'svg' ? 'image/svg+xml' : e === 'jpg' || e === 'jpeg' ? 'image/jpeg' : 'image/' + e;
    return `data:${m};base64,${b.toString('base64')}`;
  } catch {
    return null;
  }
};
const charW = (ch, sz) => (ch.charCodeAt(0) > 0x2e80 ? sz : sz * 0.55);
const wrap = (text, width, sz) => {
  const out = [];
  for (const para of String(text).split('\n')) {
    let line = '', w = 0;
    for (const ch of para) {
      const cw = charW(ch, sz);
      if (w + cw > width && line) { out.push(line); line = ''; w = 0; }
      line += ch; w += cw;
    }
    out.push(line);
  }
  return out;
};

let svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`;
svg += `<defs><filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#8595A8" flood-opacity="0.35"/></filter></defs>`;
const bg = (slide.background && slide.background.color) || (deck.meta && deck.meta.theme && deck.meta.theme.backgroundColor) || '#FFFFFF';
svg += `<rect width="${W}" height="${H}" fill="${bg}"/>`;
for (const el of slide.elements || []) {
  const x = el.left, y = el.top, w = el.width, h = el.height;
  if (el.type === 'shape') {
    const fill = el.fill || '#CCCCCC';
    const f = el.shadow ? ' filter="url(#sh)"' : '';
    if (el.shapeType === 'ellipse') svg += `<ellipse cx="${x + w / 2}" cy="${y + h / 2}" rx="${w / 2}" ry="${h / 2}" fill="${fill}"${f}/>`;
    else if (el.shapeType === 'triangle') svg += `<polygon points="${x + w / 2},${y} ${x + w},${y + h} ${x},${y + h}" fill="${fill}"${f}/>`;
    else if (el.shapeType === 'trapezoid') { const inset = w * 0.18; svg += `<polygon points="${x + inset},${y} ${x + w - inset},${y} ${x + w},${y + h} ${x},${y + h}" fill="${fill}"${f}/>`; }
    else if (el.shapeType === 'chevron') { const tip = Math.min(h * 0.5, w * 0.3); svg += `<polygon points="${x},${y} ${x + w - tip},${y} ${x + w},${y + h / 2} ${x + w - tip},${y + h} ${x},${y + h} ${x + tip},${y + h / 2}" fill="${fill}"${f}/>`; }
    else svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${el.shapeType === 'roundRect' ? 8 : 0}" fill="${fill}"${f}/>`;
  } else if (el.type === 'line') {
    const x1 = x + ((el.start && el.start[0]) || 0), y1 = y + ((el.start && el.start[1]) || 0);
    const x2 = x + ((el.end && el.end[0]) || w), y2 = y + ((el.end && el.end[1]) || 0);
    svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${el.color || '#000'}" stroke-width="${el.width || 1}"/>`;
  } else if (el.type === 'image') {
    const u = dataUri(el.src);
    if (u) svg += `<image x="${x}" y="${y}" width="${w}" height="${h}" xlink:href="${u}" preserveAspectRatio="${el.fixedRatio ? 'xMidYMid meet' : 'none'}"/>`;
    else svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#eeeeee" stroke="#999999"/>`;
  } else if (el.type === 'table') {
    const rows = el.data || [];
    const nr = rows.length || 1;
    const nc = (rows[0] || []).length || 1;
    const cw = w / nc, rh = h / nr;
    for (let r = 0; r < nr; r++) {
      for (let c = 0; c < nc; c++) {
        const cell = (rows[r] || [])[c] || {};
        const cx = x + c * cw, cy = y + r * rh;
        if (cell.fill) svg += `<rect x="${cx}" y="${cy}" width="${cw}" height="${rh}" fill="${cell.fill}"/>`;
        svg += `<rect x="${cx}" y="${cy}" width="${cw}" height="${rh}" fill="none" stroke="#D9DEE5"/>`;
        const ct = cell.text || '';
        if (ct) svg += `<text x="${cx + cw / 2}" y="${cy + rh / 2 + 4}" font-size="12" fill="${cell.color || '#333'}" text-anchor="middle" font-family="sans-serif"${cell.bold ? ' font-weight="bold"' : ''}>${esc(ct)}</text>`;
      }
    }
  } else if (el.type === 'chart') {
    // native charts don't render in resvg; draw the same SVG chart used by the rasterizer
    // so visual QA sees the real chart (otherwise chart slides look half-empty / blank).
    const c = {
      type: el.chartType || 'column',
      labels: (el.data && el.data.labels) || [],
      series: (el.data && el.data.series) || [],
      colors: el.themeColors,
    };
    try {
      svg += `<g transform="translate(${x},${y})">${chartInner(c, w, h, 'sans-serif')}</g>`;
    } catch (e) {
      svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#F0F4FA" stroke="#C9D4E3"/><text x="${x + w / 2}" y="${y + h / 2}" font-size="13" fill="#8A95A5" text-anchor="middle" font-family="sans-serif">[${esc(c.type)} chart]</text>`;
    }
  } else if (el.type === 'text') {
    const sz = el.fontSize || 18, color = el.defaultColor || '#000000';
    const lines = wrap(stripHtml(el.content), w, sz), lh = sz * 1.3;
    const align = el.align || 'left';
    const anchor = align === 'center' ? 'middle' : align === 'right' ? 'end' : 'start';
    const tx = align === 'center' ? x + w / 2 : align === 'right' ? x + w : x;
    let ty = y + sz;
    if (el.valign === 'middle') ty = y + h / 2 - (lines.length - 1) * lh / 2 + sz * 0.35;
    for (const ln of lines) {
      svg += `<text x="${tx}" y="${ty}" font-size="${sz}" fill="${color}" text-anchor="${anchor}" font-family="sans-serif"${el.bold ? ' font-weight="bold"' : ''}>${esc(ln)}</text>`;
      ty += lh;
    }
  }
}
svg += '</svg>';
const png = new Resvg(svg, { fitTo: { mode: 'width', value: W * 2 } }).render().asPng();
fs.writeFileSync(outPath, png);
console.log('wrote', outPath);
