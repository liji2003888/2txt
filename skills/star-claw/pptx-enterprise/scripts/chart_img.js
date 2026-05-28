#!/usr/bin/env node
// Render a business chart to PNG via SVG + resvg-js (works on the master/python-pptx path).
// usage: chart_img.js <manifest.json>   (manifest: [{type,labels,series,colors,width,height,out,font}, ...])
// types: column | bar | line | pie | donut
const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const DEF = ['#1677FF', '#111111', '#E60012', '#00B0EF', '#FABE0E', '#5C6B7D'];

function axisChart(c, W, H, font) {
  const colors = c.colors && c.colors.length ? c.colors : DEF;
  const labels = c.labels || [];
  const series = c.series || [];
  const horiz = c.type === 'bar';
  const padL = 48, padR = 16, padT = 28, padB = 38;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  let max = 0;
  for (const s of series) for (const v of s.values || []) max = Math.max(max, v);
  max = max || 1;
  const niceMax = Math.ceil(max / 4) * 4 || 4;
  let svg = '';
  // gridlines + y labels
  for (let g = 0; g <= 4; g++) {
    const gy = padT + plotH - (plotH * g) / 4;
    svg += `<line x1="${padL}" y1="${gy}" x2="${padL + plotW}" y2="${gy}" stroke="#E4E9F0" stroke-width="1"/>`;
    svg += `<text x="${padL - 8}" y="${gy + 4}" font-size="11" fill="#8A95A5" text-anchor="end" font-family="${font}">${Math.round((niceMax * g) / 4)}</text>`;
  }
  const ng = labels.length || 1;
  const groupW = plotW / ng;
  if (c.type === 'line' || c.type === 'area') {
    const baseY = padT + plotH;
    // for area, draw larger-sum series first so smaller ones layer on top
    const order = series.map((s, i) => i);
    if (c.type === 'area') order.sort((a, b) => (series[b].values || []).reduce((x, y) => x + y, 0) - (series[a].values || []).reduce((x, y) => x + y, 0));
    order.forEach((si) => {
      const s = series[si];
      const col = colors[si % colors.length];
      const pts = (s.values || []).map((v, i) => [padL + groupW * (i + 0.5), padT + plotH - (plotH * v) / niceMax]);
      if (c.type === 'area') {
        const poly = `${padL + groupW * 0.5},${baseY} ` + pts.map((p) => p.join(',')).join(' ') + ` ${padL + groupW * (pts.length - 0.5)},${baseY}`;
        svg += `<polygon points="${poly}" fill="${col}" fill-opacity="0.85"/>`;
      } else {
        svg += `<polyline points="${pts.map((p) => p.join(',')).join(' ')}" fill="none" stroke="${col}" stroke-width="2.5"/>`;
        pts.forEach((p) => { svg += `<circle cx="${p[0]}" cy="${p[1]}" r="3.5" fill="${col}"/>`; });
      }
    });
  } else {
    const ns = series.length || 1;
    const bw = (groupW * 0.66) / ns;
    labels.forEach((lab, i) => {
      series.forEach((s, si) => {
        const v = (s.values || [])[i] || 0;
        const col = colors[si % colors.length];
        if (horiz) {
          const bh = (plotW * v) / niceMax; // reuse: horizontal not fully impl, fall back vertical
        }
        const bx = padL + groupW * i + groupW * 0.17 + si * bw;
        const bh = (plotH * v) / niceMax;
        const by = padT + plotH - bh;
        svg += `<rect x="${bx}" y="${by}" width="${bw * 0.9}" height="${bh}" fill="${col}" rx="2"/>`;
      });
    });
  }
  // x labels
  labels.forEach((lab, i) => {
    const x = padL + groupW * (i + 0.5);
    svg += `<text x="${x}" y="${H - padB + 18}" font-size="11" fill="#5C6B7D" text-anchor="middle" font-family="${font}">${esc(lab)}</text>`;
  });
  // legend
  series.forEach((s, si) => {
    const lx = padL + si * 110;
    svg += `<rect x="${lx}" y="6" width="12" height="12" rx="2" fill="${colors[si % colors.length]}"/>`;
    svg += `<text x="${lx + 18}" y="16" font-size="11" fill="#333" font-family="${font}">${esc(s.name || '')}</text>`;
  });
  return svg;
}

function pieChart(c, W, H, font, donut) {
  const colors = c.colors && c.colors.length ? c.colors : DEF;
  const series = (c.series && c.series[0] && c.series[0].values) || [];
  const labels = c.labels || [];
  const total = series.reduce((a, b) => a + b, 0) || 1;
  const cx = W * 0.38, cy = H / 2, r = Math.min(W * 0.34, H * 0.4);
  let ang = -Math.PI / 2, svg = '';
  series.forEach((v, i) => {
    const a2 = ang + (2 * Math.PI * v) / total;
    const x1 = cx + r * Math.cos(ang), y1 = cy + r * Math.sin(ang);
    const x2 = cx + r * Math.cos(a2), y2 = cy + r * Math.sin(a2);
    const large = a2 - ang > Math.PI ? 1 : 0;
    svg += `<path d="M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z" fill="${colors[i % colors.length]}"/>`;
    ang = a2;
  });
  if (donut) svg += `<circle cx="${cx}" cy="${cy}" r="${r * 0.55}" fill="#FFFFFF"/>`;
  // legend on right
  labels.forEach((lab, i) => {
    const ly = cy - (labels.length * 22) / 2 + i * 22;
    const pct = Math.round((100 * (series[i] || 0)) / total);
    svg += `<rect x="${W * 0.7}" y="${ly}" width="12" height="12" rx="2" fill="${colors[i % colors.length]}"/>`;
    svg += `<text x="${W * 0.7 + 18}" y="${ly + 10}" font-size="11" fill="#333" font-family="${font}">${esc(lab)}  ${pct}%</text>`;
  });
  return svg;
}

function gaugeChart(c, W, H, font) {
  const colors = c.colors && c.colors.length ? c.colors : DEF;
  const accent = colors[0];
  const pct = Math.max(0, Math.min(100, (c.series && c.series[0] && c.series[0].values && c.series[0].values[0]) || 0));
  const label = (c.labels && c.labels[0]) || '';
  const cx = W / 2, cy = H / 2 + 6, r = Math.min(W, H) * 0.36, sw = Math.max(10, r * 0.22);
  const polar = (deg) => [cx + r * Math.cos((deg - 90) * Math.PI / 180), cy + r * Math.sin((deg - 90) * Math.PI / 180)];
  const a = pct / 100 * 360;
  const [sx, sy] = polar(0), [ex, ey] = polar(a);
  const large = a > 180 ? 1 : 0;
  let svg = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#E4EAF2" stroke-width="${sw}"/>`;
  if (pct > 0) svg += `<path d="M${sx},${sy} A${r},${r} 0 ${large} 1 ${ex},${ey}" fill="none" stroke="${accent}" stroke-width="${sw}" stroke-linecap="round"/>`;
  svg += `<text x="${cx}" y="${cy - 2}" font-size="${r * 0.5}" fill="${accent}" font-weight="bold" text-anchor="middle" dominant-baseline="middle" font-family="${font}">${pct}%</text>`;
  if (label) svg += `<text x="${cx}" y="${cy + r * 0.34}" font-size="${r * 0.18}" fill="#5C6B7D" text-anchor="middle" font-family="${font}">${esc(label)}</text>`;
  return svg;
}

function render(c) {
  const W = c.width || 760, H = c.height || 360;
  const font = c.font || 'sans-serif';
  let inner;
  if (c.type === 'pie') inner = pieChart(c, W, H, font, false);
  else if (c.type === 'donut') inner = pieChart(c, W, H, font, true);
  else if (c.type === 'gauge') inner = gaugeChart(c, W, H, font);
  else inner = axisChart(c, W, H, font);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="#FFFFFF"/>${inner}</svg>`;
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: W * 2 } }).render().asPng();
  fs.writeFileSync(c.out, png);
}

const mf = process.argv[2];
if (!mf) { console.error('usage: chart_img.js <manifest.json>'); process.exit(2); }
const items = JSON.parse(fs.readFileSync(mf, 'utf-8'));
let ok = 0;
for (const c of items) { try { render(c); ok++; } catch (e) { console.error('chart failed:', e.message); } }
console.log(`rendered ${ok}/${items.length} charts`);
