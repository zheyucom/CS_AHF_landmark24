const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 16, title: 'BigQuery Radiology' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("106/107: BigQuery pre-T0 放射科证据抽取与 QC", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Flow: 5,555 → 5,549 → 4,303 → 3,593
  const flowSteps = [
    { n: "5,555", label: "HF ICD anchors", detail: "v3.3 eligible 全部 HF 锚点入候选" },
    { n: "5,549", label: "有效时间边界", detail: "排除 6 例 admittime > intime 异常" },
    { n: "4,303", label: "pre-T0 radiology 报告", detail: "报告文本原始抽取 (106 v2)" },
    { n: "3,593", label: "ICU 前可见报告", detail: "charttime/storetime 在 T0 前" }
  ];

  const startX = 0.6;
  const boxW = 2.15;
  const boxH = 1.5;
  const gap = 0.12;

  flowSteps.forEach((s, i) => {
    const x = startX + i * (boxW + gap);
    const isHl = i === 2;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.1, w: boxW, h: boxH,
      fill: { color: isHl ? theme.secondary : "F8FAFC" },
      line: { color: isHl ? theme.secondary : theme.accent, width: 0.75 }
    });

    slide.addText(s.n, {
      x: x, y: 1.25, w: boxW, h: 0.5,
      fontSize: isHl ? 26 : 22, fontFace: "Georgia",
      color: isHl ? "FFFFFF" : theme.primary, bold: true,
      align: "center", margin: 0
    });
    slide.addText(s.label, {
      x: x + 0.1, y: 1.75, w: boxW - 0.2, h: 0.3,
      fontSize: 10.5, fontFace: "Microsoft YaHei",
      color: isHl ? "FFFFFF" : theme.primary, bold: true, align: "center", margin: 0
    });
    slide.addText(s.detail, {
      x: x + 0.1, y: 2.05, w: boxW - 0.2, h: 0.5,
      fontSize: 8, fontFace: "Microsoft YaHei",
      color: isHl ? "FECACA" : "64748B", bold: false, align: "center", margin: 0, valign: "top"
    });

    if (i < flowSteps.length - 1) {
      slide.addText("→", {
        x: x + boxW + 0.01, y: 1.55, w: gap - 0.02, h: 0.4,
        fontSize: 16, fontFace: "Georgia",
        color: "94A3B8", bold: true, align: "center", valign: "middle", margin: 0
      });
    }
  });

  // Rule screen results
  slide.addText("规则筛查结果 (weak label, 需人工验证)", {
    x: 0.5, y: 2.9, w: 9, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const ruleStats = [
    { v: "997", l: "规则阳性患者" },
    { v: "877", l: "明确阳性 (definite congestion)" },
    { v: "769", l: "ICU 前可见明确阳性" }
  ];

  ruleStats.forEach((s, i) => {
    const x = 0.5 + i * 3.1;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 3.25, w: 2.9, h: 0.95,
      fill: { color: theme.light }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 3.25, w: 2.9, h: 0.06,
      fill: { color: theme.primary }
    });
    slide.addText(s.v, {
      x: x, y: 3.4, w: 2.9, h: 0.4,
      fontSize: 24, fontFace: "Georgia",
      color: theme.secondary, bold: true, align: "center", margin: 0
    });
    slide.addText(s.l, {
      x: x, y: 3.8, w: 2.9, h: 0.25,
      fontSize: 10, fontFace: "Microsoft YaHei",
      color: "475569", bold: false, align: "center", margin: 0
    });
  });

  // Key messages
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.4, w: 9, h: 0.95,
    fill: { color: "F8FAFC" },
    line: { color: theme.accent, width: 0.5 }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.4, w: 0.08, h: 0.95,
    fill: { color: theme.secondary }
  });

  slide.addText([
    { text: "关键要点: ", options: { bold: true, color: theme.secondary } },
    { text: "关键词规则只能作为 weak label; 需人工标注估计 PPV、漏检/误触发与替代解释。", options: { color: "334155" } },
    { text: "\n106 v2 同时审计 charttime 与 storetime, 排除 6 个异常边界; patient-level 汇总 5,549 行。", options: { color: "334155" } }
  ], {
    x: 0.7, y: 4.45, w: 8.6, h: 0.85,
    fontSize: 10.5, fontFace: "Microsoft YaHei",
    bold: false, align: "left", margin: 0, valign: "middle"
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("16", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fontSize: 12, fontFace: "Georgia",
    color: "FFFFFF", bold: true,
    align: "center", valign: "middle"
  });

  return slide;
}

if (require.main === module) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  const theme = { primary: "003049", secondary: "780000", accent: "669bbc", light: "fdf0d5", bg: "FFFFFF" };
  createSlide(pres, theme);
  pres.writeFile({ fileName: "slide-16-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
