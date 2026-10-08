// helpers.js —— 深蓝科技风共享布局组件
// 配色取自课程 PPT 科技风（全深色 deck）
// 用法：所有函数第一个参数都是 slide（不是 pres！）

const C = {
  BG:      '0A1E3C',  // 页面底色
  CARD:    '12294F',  // 卡片
  CARD2:   '16305C',  // 卡片2 / 表头
  BORDER:  '24406E',  // 边框
  TXT:     'FFFFFF',  // 标题白
  BODY:    'C9DAF0',  // 正文浅蓝白
  SUB:     '7E93B8',  // 次级灰蓝
  ACCENT:  '00D4FF',  // 强调青
  ACCENT2: '7FE0FF',  // 淡青
  ONACC:   '06283D',  // 青底上的深色字
  OK:      '4ADE80',  // 成功绿
  BAD:     'FF8A8A',  // 失败红
  WARN:    'FFC857',  // 警告黄
};

const FONT = '微软雅黑';
const MONO = 'Consolas';
const PAGE_W = 10, PAGE_H = 5.625;

// ---------- 通用 ----------
function bg(slide) {
  slide.background = { color: C.BG };
}

function decoRings(slide, x, y, s) {
  // 右上角装饰圆环 + 点（全部收进画布内）
  slide.addShape('ellipse', {
    x, y, w: s, h: s, fill: { type: 'none' },
    line: { color: C.ACCENT, width: 1, transparency: 70 },
  });
  slide.addShape('ellipse', {
    x: x + s * 0.22, y: y + s * 0.22, w: s * 0.56, h: s * 0.56, fill: { type: 'none' },
    line: { color: C.ACCENT2, width: 0.75, transparency: 60 },
  });
  slide.addShape('ellipse', {
    x: x + s * 0.44, y: y + s * 0.44, w: s * 0.12, h: s * 0.12,
    fill: { color: C.ACCENT },
  });
}

function dotGrid(slide, x, y, rows, cols, gap, color, size) {
  size = size || 0.035;
  for (let r = 0; r < rows; r++) {
    for (let c2 = 0; c2 < cols; c2++) {
      slide.addShape('ellipse', {
        x: x + c2 * gap, y: y + r * gap, w: size, h: size,
        fill: { color: color || C.BORDER },
      });
    }
  }
}

// ---------- 封面 ----------
function cover(slide, o) {
  bg(slide);
  dotGrid(slide, 0.55, 0.5, 5, 12, 0.16, C.BORDER, 0.03);
  decoRings(slide, 8.15, 0.45, 1.55);

  // 青色竖条
  slide.addShape('rect', { x: 0.62, y: 1.62, w: 0.075, h: 1.5, fill: { color: C.ACCENT } });

  slide.addText(o.kicker || '', {
    x: 0.85, y: 1.55, w: 7.6, h: 0.3,
    fontSize: 12, color: C.ACCENT, fontFace: FONT, charSpacing: 2,
  });
  slide.addText(o.title, {
    x: 0.82, y: 1.86, w: 8.3, h: 0.72,
    fontSize: 31, bold: true, color: C.TXT, fontFace: FONT,
  });
  slide.addText(o.title2 || '', {
    x: 0.85, y: 2.56, w: 8.3, h: 0.5,
    fontSize: 19, color: C.ACCENT2, fontFace: FONT,
  });
  slide.addText(o.desc || '', {
    x: 0.85, y: 3.18, w: 8.1, h: 0.42,
    fontSize: 12.5, color: C.BODY, fontFace: FONT, lineSpacing: 18,
  });

  // 底部信息条
  slide.addShape('rect', { x: 0.85, y: 3.98, w: 8.3, h: 0.02, fill: { color: C.BORDER } });
  slide.addText(o.meta || '', {
    x: 0.85, y: 4.12, w: 8.3, h: 0.35,
    fontSize: 11.5, color: C.SUB, fontFace: FONT,
  });
  slide.addText(o.foot || '', {
    x: 0.85, y: 4.52, w: 8.3, h: 0.3,
    fontSize: 10, color: C.SUB, fontFace: FONT,
  });
}

// ---------- 内容页标题栏 ----------
function titleBar(slide, o) {
  bg(slide);
  const page = o.page || 0;

  if (o.kicker) {
    slide.addText(o.kicker, {
      x: 0.5, y: 0.26, w: 6.0, h: 0.26,
      fontSize: 10.5, color: C.ACCENT, fontFace: FONT, charSpacing: 1.5,
    });
  }
  slide.addText(o.title, {
    x: 0.5, y: 0.5, w: 7.6, h: 0.42,
    fontSize: 20, bold: true, color: C.TXT, fontFace: FONT,
  });
  slide.addShape('rect', { x: 0.5, y: 0.98, w: 0.85, h: 0.055, fill: { color: C.ACCENT } });

  if (page) {
    slide.addText(String(page).padStart(2, '0'), {
      x: 9.0, y: 0.42, w: 0.6, h: 0.4,
      fontSize: 17, bold: true, color: C.BORDER, fontFace: FONT, align: 'right',
    });
  }

  // 页脚
  slide.addShape('line', {
    x: 0.5, y: 5.24, w: 9.0, h: 0,
    line: { color: C.BORDER, width: 0.75 },
  });
  slide.addText('Qwen3.5-4B 医疗专家模型微调与部署', {
    x: 0.5, y: 5.29, w: 6.0, h: 0.24,
    fontSize: 8.5, color: C.SUB, fontFace: FONT,
  });
  if (o.tagRight) {
    slide.addText(o.tagRight, {
      x: 6.5, y: 5.29, w: 3.0, h: 0.24,
      fontSize: 8.5, color: C.SUB, fontFace: FONT, align: 'right',
    });
  }
}

// ---------- 卡片 ----------
function card(slide, o) {
  slide.addShape('roundRect', {
    x: o.x, y: o.y, w: o.w, h: o.h,
    fill: { color: o.fill || C.CARD },
    line: { color: o.line || C.BORDER, width: 0.75 },
    rectRadius: 0.05,
  });
  if (o.accent) {
    slide.addShape('rect', {
      x: o.x, y: o.y + 0.14, w: 0.05, h: o.h - 0.28, fill: { color: o.accent },
    });
  }
}

function cardTitle(slide, o) {
  slide.addText(o.text, {
    x: o.x, y: o.y, w: o.w, h: 0.3,
    fontSize: o.size || 13, bold: true, color: o.color || C.ACCENT2, fontFace: FONT,
    align: o.align || 'left',
  });
}

// ---------- 列表（不用 bullet option，避免渲染叠影） ----------
function bullets(slide, o) {
  const items = o.items || [];
  const size = o.size || 11.5;
  const gap = o.gap || 0.34;
  const color = o.color || C.BODY;
  const texts = items.map((it, i) => ({
    text: (o.noBullet ? '' : '• ') + it,
    options: {
      fontSize: size, color, fontFace: FONT, breakLine: true,
      paraSpaceAfter: o.spaceAfter === undefined ? 5 : o.spaceAfter,
    },
  }));
  slide.addText(texts, {
    x: o.x, y: o.y, w: o.w, h: o.h || Math.min(items.length * gap + 0.1, 4.0),
    valign: o.valign || 'top', lineSpacing: o.lineSpacing || (size * 1.55),
  });
}

// 带高亮词的列表：每项 [高亮词, 说明]
function bulletsHL(slide, o) {
  const items = o.items || [];
  const runs = [];
  items.forEach(it => {
    runs.push({
      text: '• ' + it[0],
      options: {
        fontSize: o.size || 11.5, bold: true, color: o.hlColor || C.ACCENT2,
        fontFace: FONT, breakLine: true, paraSpaceAfter: 2,
      },
    });
    if (it[1]) {
      runs.push({
        text: '   ' + it[1],
        options: {
          fontSize: (o.size || 11.5) - 1, color: C.BODY, fontFace: FONT,
          breakLine: true, paraSpaceAfter: o.spaceAfter === undefined ? 7 : o.spaceAfter,
        },
      });
    }
  });
  slide.addText(runs, {
    x: o.x, y: o.y, w: o.w, h: o.h || 3.6, valign: 'top',
    lineSpacing: (o.size || 11.5) * 1.5,
  });
}

// ---------- 自定义表格（圆角卡片行，比 addTable 稳） ----------
function table(slide, o) {
  const { x, y, w, headers, rows, colW, rowH } = o;
  const rh = rowH || 0.36;
  const hh = o.headH || 0.36;

  slide.addShape('roundRect', {
    x, y, w, h: hh, fill: { color: C.CARD2 }, line: { color: C.BORDER, width: 0.75 },
    rectRadius: 0.03,
  });
  let cx = x;
  headers.forEach((h, i) => {
    slide.addText(h, {
      x: cx + 0.09, y, w: colW[i] - 0.18, h: hh,
      fontSize: o.headSize || 10.5, bold: true, color: C.ACCENT2, fontFace: FONT,
      valign: 'middle', align: o.align && o.align[i] ? o.align[i] : 'left',
    });
    cx += colW[i];
  });

  rows.forEach((r, ri) => {
    const ry = y + hh + ri * rh;
    slide.addShape('rect', {
      x, y: ry, w, h: rh,
      fill: { color: ri % 2 === 0 ? C.CARD : C.BG },
      line: { color: C.BORDER, width: 0.5 },
    });
    let rx = x;
    r.forEach((cell, ci) => {
      const cellColor = typeof cell === 'string' && cell.startsWith('!')
        ? C.OK : (typeof cell === 'string' && cell.startsWith('x') && o.markBad ? C.BAD : (o.cellColor || C.BODY));
      const txt = typeof cell === 'string' && (cell.startsWith('!') || (cell.startsWith('x') && o.markBad))
        ? cell.slice(1) : cell;
      slide.addText(txt, {
        x: rx + 0.09, y: ry, w: colW[ci] - 0.18, h: rh,
        fontSize: o.size || 10, color: cellColor, fontFace: FONT,
        valign: 'middle', align: o.align && o.align[ci] ? o.align[ci] : 'left',
      });
      rx += colW[ci];
    });
  });
  return y + hh + rows.length * rh;
}

// ---------- 胶囊标签 ----------
function tag(slide, o) {
  slide.addShape('roundRect', {
    x: o.x, y: o.y, w: o.w, h: o.h || 0.3,
    fill: { color: o.fill || C.ACCENT }, line: { type: 'none' }, rectRadius: 0.12,
  });
  slide.addText(o.text, {
    x: o.x, y: o.y, w: o.w, h: o.h || 0.3,
    fontSize: o.size || 10, bold: true, color: o.color || C.ONACC,
    fontFace: FONT, align: 'center', valign: 'middle',
  });
}

// ---------- 水平流程条 ----------
function flow(slide, o) {
  const items = o.items || [];
  const n = items.length;
  const totalW = o.w;
  const gap = 0.12;
  const chipW = (totalW - gap * (n - 1)) / n;
  items.forEach((t, i) => {
    const cx = o.x + i * (chipW + gap);
    slide.addShape('roundRect', {
      x: cx, y: o.y, w: chipW, h: o.h || 0.46,
      fill: { color: o.hi === i ? C.ACCENT : C.CARD },
      line: { color: o.hi === i ? C.ACCENT : C.BORDER, width: 0.75 },
      rectRadius: 0.06,
    });
    slide.addText(t, {
      x: cx + 0.04, y: o.y, w: chipW - 0.08, h: o.h || 0.46,
      fontSize: o.size || 8.5, color: o.hi === i ? C.ONACC : C.BODY,
      fontFace: FONT, align: 'center', valign: 'middle',
    });
    if (i < n - 1) {
      slide.addText('▸', {
        x: cx + chipW, y: o.y, w: gap, h: o.h || 0.46,
        fontSize: 9, color: C.ACCENT, fontFace: FONT, align: 'center', valign: 'middle',
      });
    }
  });
}

// ---------- 提示条 / 警示条 ----------
function callout(slide, o) {
  slide.addShape('roundRect', {
    x: o.x, y: o.y, w: o.w, h: o.h,
    fill: { color: o.fill || C.CARD2 }, line: { color: o.line || C.ACCENT, width: 0.75 },
    rectRadius: 0.05,
  });
  slide.addText(o.text, {
    x: o.x + 0.14, y: o.y, w: o.w - 0.28, h: o.h,
    fontSize: o.size || 10.5, color: o.color || C.BODY, fontFace: FONT,
    valign: 'middle', lineSpacing: (o.size || 10.5) * 1.5,
  });
}

// ---------- 代码块 ----------
function code(slide, o) {
  slide.addShape('roundRect', {
    x: o.x, y: o.y, w: o.w, h: o.h,
    fill: { color: '061428' }, line: { color: C.BORDER, width: 0.75 }, rectRadius: 0.05,
  });
  slide.addText(o.text, {
    x: o.x + 0.14, y: o.y + 0.08, w: o.w - 0.28, h: o.h - 0.16,
    fontSize: o.size || 9.5, color: C.ACCENT2, fontFace: MONO,
    valign: 'top', lineSpacing: (o.size || 9.5) * 1.45,
  });
}

// ---------- 大数字统计卡 ----------
function statCard(slide, o) {
  slide.addShape('roundRect', {
    x: o.x, y: o.y, w: o.w, h: o.h,
    fill: { color: C.CARD }, line: { color: C.BORDER, width: 0.75 }, rectRadius: 0.06,
  });
  slide.addShape('rect', { x: o.x, y: o.y + 0.12, w: 0.05, h: o.h - 0.24, fill: { color: o.accent || C.ACCENT } });
  slide.addText(o.num, {
    x: o.x + 0.14, y: o.y + 0.1, w: o.w - 0.28, h: 0.42,
    fontSize: o.numSize || 21, bold: true, color: o.accent || C.ACCENT, fontFace: FONT,
  });
  slide.addText(o.label, {
    x: o.x + 0.14, y: o.y + o.h - 0.36, w: o.w - 0.28, h: 0.3,
    fontSize: 9, color: C.SUB, fontFace: FONT,
  });
}

module.exports = {
  C, FONT, MONO, PAGE_W, PAGE_H,
  bg, cover, titleBar, card, cardTitle, bullets, bulletsHL,
  table, tag, flow, callout, code, statCard, decoRings, dotGrid,
};
