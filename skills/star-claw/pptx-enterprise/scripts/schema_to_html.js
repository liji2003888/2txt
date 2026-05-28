#!/usr/bin/env node
// QA-only HTML fallback. The production HTML renderer is the forked PPTist in web/.
// This standalone fallback exists so the schema can be previewed without spinning up the Vue app.
const fs = require('fs');

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('usage: schema_to_html.js <deck.json> <out.html>');
  process.exit(2);
}
const deck = JSON.parse(fs.readFileSync(args[0], 'utf-8'));
const W = (deck.meta && deck.meta.width) || 960;
const H = (deck.meta && deck.meta.height) || 540;
const theme = (deck.meta && deck.meta.theme) || {};

const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const toDataUri = (src) => {
  if (!src || /^(https?:|data:)/.test(src)) return src;
  try {
    const buf = fs.readFileSync(src);
    const ext = (src.split('.').pop() || 'png').toLowerCase();
    const mime = ext === 'svg' ? 'image/svg+xml' : ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : `image/${ext}`;
    return `data:${mime};base64,${buf.toString('base64')}`;
  } catch {
    return src;
  }
};

const renderEl = (el) => {
  const style =
    `position:absolute;left:${el.left}px;top:${el.top}px;width:${el.width}px;height:${el.height}px;` +
    `transform:rotate(${el.rotate || 0}deg);transform-origin:center;`;
  if (el.type === 'text') {
    const f = el.defaultFontName || theme.fontName || 'sans-serif';
    return `<div style="${style}font-size:${el.fontSize || 18}px;color:${el.defaultColor || '#000'};font-family:${f};overflow:hidden;">${el.content || ''}</div>`;
  }
  if (el.type === 'image') {
    return `<img src="${escapeHtml(toDataUri(el.src))}" style="${style}object-fit:contain;">`;
  }
  if (el.type === 'shape') {
    const radius = el.shapeType === 'roundRect' ? '12px' : el.shapeType === 'ellipse' ? '50%' : '0';
    const inner = el.text && el.text.content
      ? `<div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;color:${(el.text && el.text.defaultColor) || '#000'};">${escapeHtml(el.text.content)}</div>`
      : '';
    return `<div style="${style}background:${el.fill || '#ccc'};border-radius:${radius};">${inner}</div>`;
  }
  if (el.type === 'line') {
    return `<div style="${style}border-top:${el.width || 1}px ${el.style || 'solid'} ${el.color || '#000'};"></div>`;
  }
  if (el.type === 'table') {
    const rows = (el.data || [])
      .map((r) => '<tr>' + r.map((c) => `<td style="border:1px solid #ccc;padding:4px;">${escapeHtml((c && c.text) || '')}</td>`).join('') + '</tr>')
      .join('');
    return `<table style="${style}border-collapse:collapse;font-size:12px;">${rows}</table>`;
  }
  return `<div style="${style}border:1px dashed #999;color:#999;display:flex;align-items:center;justify-content:center;">[${el.type}]</div>`;
};

const slides = deck.slides
  .map((s, i) => {
    const bg = (s.background && s.background.color) || '#fff';
    const body = (s.elements || []).map(renderEl).join('\n');
    return `<section style="width:${W}px;height:${H}px;position:relative;background:${bg};margin:20px auto;box-shadow:0 0 8px rgba(0,0,0,0.2);overflow:hidden;" data-slide="${i}">${body}</section>`;
  })
  .join('\n');

const html = `<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml((deck.meta && deck.meta.title) || 'Deck')}</title></head><body style="background:#eee;margin:0;padding:20px;font-family:sans-serif;">${slides}</body></html>`;
fs.writeFileSync(args[1], html);
console.log(`wrote ${args[1]}`);
