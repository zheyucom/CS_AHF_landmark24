const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 12, title: 'Fine-Gray Results' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("Fine-Gray 主模型: 5 折 OOF 内部验证", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 24, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Left: metric cards
  const metrics = [
    { v: "0.7622", l: "48h competing-risk AUC", note: "主模型 primary_prespecified" },
    { v: "0.0652", l: "Brier Score", note: "Null model: 0.0724" },
    { v: "~0.0057", l: "校准: 十分位 MAE", note: "predicted vs observed CIF" },
    { v: "37/45", l: "5 折同向特征", note: "32/45 五折完全同向" }
  ];

  metrics.forEach((m, i) => {
    const x = 0.5 + (i % 2) * 2.35;
    const y = 1.0 + Math.floor(i / 2) * 1.15;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 2.2, h: 1.0,
      fill: { color: i < 2 ? theme.light : "F8FAFC" },
      line: { color: theme.accent, width: 0.5 }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 2.2, h: 0.06,
      fill: { color: i === 0 ? theme.secondary : theme.primary }
    });

    slide.addText(m.v, {
      x: x, y: y + 0.12, w: 2.2, h: 0.4,
      fontSize: 20, fontFace: "Georgia",
      color: theme.secondary, bold: true, align: "center", margin: 0
    });
    slide.addText(m.l, {
      x: x + 0.1, y: y + 0.52, w: 2.0, h: 0.22,
      fontSize: 9, fontFace: "Microsoft YaHei",
      color: theme.primary, bold: true, align: "center", margin: 0
    });
    slide.addText(m.note, {
      x: x + 0.1, y: y + 0.74, w: 2.0, h: 0.2,
      fontSize: 8, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "center", margin: 0
    });
  });

  // Right: calibration decile bar chart
  slide.addText("48h 校准: 预测 vs 观测 CIF (十分位)", {
    x: 5.3, y: 0.9, w: 4.3, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const deciles = [
    { p: 0.0162, o: 0.0126 },
    { p: 0.0262, o: 0.0342 },
    { p: 0.0347, o: 0.0378 },
    { p: 0.0435, o: 0.0486 },
    { p: 0.0535, o: 0.0558 },
    { p: 0.0644, o: 0.0685 },
    { p: 0.0788, o: 0.0865 },
    { p: 0.1003, o: 0.0971 },
    { p: 0.1358, o: 0.1351 },
    { p: 0.2606, o: 0.2410 }
  ];

  const chartX = 5.3;
  const chartY = 1.35;
  const chartW = 4.3;
  const chartH = 2.9;
  const maxV = 0.28;
  const barW = 0.17;
  const gap = (chartW - 10 * barW) / 9;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: chartX, y: chartY, w: chartW, h: chartH,
    fill: { color: "F8FAFC" },
    line: { color: "E2E8F0", width: 0.5 }
  });

  deciles.forEach((d, i) => {
    const x = chartX + 0.15 + i * (barW + gap);
    const pH = (d.p / maxV) * (chartH - 0.5);
    const oH = (d.o / maxV) * (chartH - 0.5);

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: chartY + chartH - 0.25 - pH, w: barW / 2 - 0.02, h: pH,
      fill: { color: theme.secondary }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x + barW / 2 + 0.02, y: chartY + chartH - 0.25 - oH, w: barW / 2 - 0.02, h: oH,
      fill: { color: theme.accent }
    });
  });

  // Axis labels
  slide.addText("1", { x: chartX + 0.1, y: chartY + chartH - 0.25, w: 0.3, h: 0.2, fontSize: 7, color: "94A3B8", align: "center", margin: 0 });
  slide.addText("10", { x: chartX + chartW - 0.45, y: chartY + chartH - 0.25, w: 0.35, h: 0.2, fontSize: 7, color: "94A3B8", align: "center", margin: 0 });

  // Legend
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.5, y: 4.35, w: 0.15, h: 0.15, fill: { color: theme.secondary }
  });
  slide.addText("Predicted", {
    x: 5.7, y: 4.33, w: 1.0, h: 0.2, fontSize: 8, color: "334155", align: "left", margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.9, y: 4.35, w: 0.15, h: 0.15, fill: { color: theme.accent }
  });
  slide.addText("Observed", {
    x: 7.1, y: 4.33, w: 1.0, h: 0.2, fontSize: 8, color: "334155", align: "left", margin: 0
  });

  // Bottom interpretation
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.6, w: 9, h: 0.62,
    fill: { color: theme.primary }
  });
  slide.addText([
    { text: "解读: ", options: { bold: true } },
    { text: "主模型校准良好 (十分位 MAE≈0.006); Top 10% 风险组事件率 24.1%, 捕获 29.5% 的事件; 37/45 特征五折同向, 方向稳定。缺失指示器敏感性: AUC 0.7605 / Brier 0.0649。", options: {} }
  ], {
    x: 0.7, y: 4.6, w: 8.6, h: 0.62,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: false, align: "left", margin: 0, valign: "middle"
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("12", {
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
  pres.writeFile({ fileName: "slide-12-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
