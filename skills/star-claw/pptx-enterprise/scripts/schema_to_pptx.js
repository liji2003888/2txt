#!/usr/bin/env node
// Slide JSON -> .pptx via PptxGenJS. Schema is px on 960x540 canvas; output is 13.333x7.5 in (16:9).
const fs = require('fs');
const pptxgen = require('pptxgenjs');

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('usage: schema_to_pptx.js <deck.json> <out.pptx>');
  process.exit(2);
}
const deck = JSON.parse(fs.readFileSync(args[0], 'utf-8'));
const outPath = args[1];

const PPT_W_IN = 13.333;
const PPT_H_IN = 7.5;
const canvasW = (deck.meta && deck.meta.width) || 960;
const canvasH = (deck.meta && deck.meta.height) || 540;
const px2inX = (x) => (x / canvasW) * PPT_W_IN;
const px2inY = (y) => (y / canvasH) * PPT_H_IN;
const stripHash = (c) => (c || '').replace('#', '');

const pres = new pptxgen();
pres.defineLayout({ name: 'OC16x9', width: PPT_W_IN, height: PPT_H_IN });
pres.layout = 'OC16x9';
if (deck.meta && deck.meta.title) pres.title = deck.meta.title;

const themeFont = (deck.meta && deck.meta.theme && deck.meta.theme.fontName) || 'Calibri';

const stripHtml = (html) =>
  String(html)
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|li|div)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim();

const splitBullets = (html) => {
  const items = [...String(html).matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)].map((m) => stripHtml(m[1]));
  return items.length ? items : null;
};

for (const slide of deck.slides) {
  const s = pres.addSlide();
  if (slide.background && slide.background.type === 'solid' && slide.background.color) {
    s.background = { color: stripHash(slide.background.color) };
  } else if (slide.background && slide.background.type === 'image' && slide.background.image) {
    s.background = { path: slide.background.image };
  }
  for (const el of slide.elements || []) {
    const box = {
      x: px2inX(el.left),
      y: px2inY(el.top),
      w: px2inX(el.width),
      h: px2inY(el.height),
      rotate: el.rotate || 0,
    };
    if (el.type === 'text') {
      const bullets = splitBullets(el.content);
      const fill = el.fill ? { color: stripHash(el.fill) } : undefined;
      const baseOpts = {
        ...box,
        fontSize: el.fontSize || 18,
        color: stripHash(el.defaultColor || '#000000'),
        fontFace: el.defaultFontName || themeFont,
        fill,
        valign: el.valign || 'top',
      };
      if (el.lineHeight) baseOpts.lineSpacingMultiple = el.lineHeight;
      if (bullets) {
        s.addText(
          bullets.map((t) => ({ text: t, options: { bullet: true } })),
          { ...baseOpts, align: el.align || 'left' },
        );
      } else {
        const text = stripHtml(el.content);
        const bold = el.bold !== undefined ? !!el.bold : /<strong>|<b>/i.test(el.content || '');
        const italic = el.italic !== undefined ? !!el.italic : /<em>|<i>/i.test(el.content || '');
        const align =
          el.align ||
          (/text-align:\s*center/i.test(el.content || '')
            ? 'center'
            : /text-align:\s*right/i.test(el.content || '')
              ? 'right'
              : 'left');
        s.addText(text, { ...baseOpts, bold, italic, align });
      }
    } else if (el.type === 'image') {
      s.addImage({ ...box, path: el.src });
    } else if (el.type === 'shape') {
      const shapeMap = {
        rect: pres.ShapeType.rect,
        roundRect: pres.ShapeType.roundRect,
        ellipse: pres.ShapeType.ellipse,
        triangle: pres.ShapeType.triangle,
        trapezoid: pres.ShapeType.trapezoid,
        chevron: pres.ShapeType.chevron,
        diamond: pres.ShapeType.diamond,
        arrow: pres.ShapeType.rightArrow,
        star: pres.ShapeType.star5,
      };
      const fill = { color: stripHash(el.fill || '#CCCCCC') };
      const shapeOpts = { ...box, fill };
      if (el.outline) {
        shapeOpts.line = { color: stripHash(el.outline.color || '#000000'), width: el.outline.width || 1 };
      }
      if (el.shapeType === 'roundRect') shapeOpts.rectRadius = el.rectRadius || 0.06;
      if (el.shadow) shapeOpts.shadow = { type: 'outer', blur: 6, offset: 3, angle: 90, color: '8595A8', opacity: 0.35 };
      s.addShape(shapeMap[el.shapeType] || pres.ShapeType.rect, shapeOpts);
      if (el.text && el.text.content) {
        s.addText(stripHtml(el.text.content), {
          ...box,
          fontSize: 16,
          color: stripHash((el.text && el.text.defaultColor) || '#000000'),
          fontFace: (el.text && el.text.defaultFontName) || themeFont,
          align: 'center',
          valign: 'middle',
        });
      }
    } else if (el.type === 'line') {
      const x1 = px2inX(el.left + ((el.start && el.start[0]) || 0));
      const y1 = px2inY(el.top + ((el.start && el.start[1]) || 0));
      const x2 = px2inX(el.left + ((el.end && el.end[0]) || el.width));
      const y2 = px2inY(el.top + ((el.end && el.end[1]) || 0));
      s.addShape(pres.ShapeType.line, {
        x: Math.min(x1, x2),
        y: Math.min(y1, y2),
        w: Math.abs(x2 - x1) || 0.01,
        h: Math.abs(y2 - y1) || 0.01,
        line: {
          color: stripHash(el.color || '#000000'),
          width: el.width || 1,
          dashType: el.style === 'dashed' ? 'dash' : 'solid',
        },
      });
    } else if (el.type === 'table') {
      const rows = (el.data || []).map((row) =>
        row.map((cell) => {
          const c = cell || {};
          const options = {};
          if (c.bold) options.bold = true;
          if (c.color) options.color = stripHash(c.color);
          if (c.fill) options.fill = { color: stripHash(c.fill) };
          if (c.align) options.align = c.align;
          return { text: c.text || '', options };
        }),
      );
      s.addTable(rows, {
        ...box,
        fontSize: 12,
        fontFace: themeFont,
        valign: 'middle',
        border: { type: 'solid', pt: 1, color: 'D9DEE5' },
      });
    } else if (el.type === 'chart') {
      // native, editable charts. column/bar share ChartType.bar with barDir; donut = doughnut.
      const t = el.chartType || 'column';
      const typeMap = {
        column: pres.ChartType.bar, bar: pres.ChartType.bar,
        line: pres.ChartType.line, area: pres.ChartType.area,
        pie: pres.ChartType.pie, donut: pres.ChartType.doughnut, doughnut: pres.ChartType.doughnut,
        radar: pres.ChartType.radar, scatter: pres.ChartType.scatter,
      };
      const seriesIn = (el.data && el.data.series) || [];
      const labels = (el.data && el.data.labels) || [];
      const data = seriesIn.map((ser) => ({ name: ser.name, labels, values: ser.values || [] }));
      const opts = {
        ...box,
        showLegend: seriesIn.length > 1 || t === 'pie' || t === 'donut',
        legendPos: 'b',
        chartColors: (el.themeColors || []).map(stripHash),
      };
      if (t === 'bar') opts.barDir = 'bar';
      if (t === 'column') opts.barDir = 'col';
      if (t === 'donut' || t === 'doughnut') opts.holeSize = 55;
      if (t === 'area') opts.chartColorsOpacity = [60, 80];
      s.addChart(typeMap[t] || pres.ChartType.bar, data, opts);
    } else if (el.type === 'latex') {
      if (el.path) s.addImage({ ...box, data: el.path });
    }
  }
  if (slide.remark) s.addNotes(slide.remark);
}

pres
  .writeFile({ fileName: outPath })
  .then(() => console.log(`wrote ${outPath}`))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
