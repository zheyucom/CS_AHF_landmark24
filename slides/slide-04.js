const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 4, title: 'Background & Evolution' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("背景: 为什么从 logistic 二分类转向竞争风险框架", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Left panel: ESC 2026 DHF update
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.95, w: 4.4, h: 3.9,
    fill: { color: "F8FAFC" },
    line: { color: theme.accent, width: 0.5 }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.95, w: 4.4, h: 0.06,
    fill: { color: theme.secondary }
  });

  slide.addText("ESC 2026 术语更新", {
    x: 0.7, y: 1.1, w: 4, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const escPoints = [
    "acute HF → decompensated HF (DHF) 术语更新",
    "DHF 方案、术语边界和终点分层新增",
    "主结局仍为 treatment-escalation-based ICU 血流动力学恶化, 而非临床确诊 CS",
    "需以操作性表型 (operational phenotype) 表述, 而非确诊诊断"
  ];
  escPoints.forEach((p, i) => {
    const y = 1.5 + i * 0.55;
    slide.addShape(pres.shapes.OVAL, {
      x: 0.7, y: y + 0.07, w: 0.12, h: 0.12,
      fill: { color: theme.secondary }
    });
    slide.addText(p, {
      x: 0.95, y: y, w: 3.8, h: 0.5,
      fontSize: 11, fontFace: "Microsoft YaHei",
      color: "334155", bold: false, align: "left", margin: 0, valign: "top"
    });
  });

  // Right panel: Why competing risk
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 0.95, w: 4.4, h: 3.9,
    fill: { color: theme.light }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 0.95, w: 4.4, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("为何采用 Fine-Gray 竞争风险", {
    x: 5.3, y: 1.1, w: 4, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  const fgPoints = [
    "ICU 内死亡 + 治疗升级合并为主事件 (composite)",
    "活着离开 index ICU 是重要竞争事件 (2,935 例)",
    "二分类固定窗口会高估/低估累计发生率 (存在偏倚风险)",
    "ICU alive discharge ≠ 48h 无事件, 须按竞争事件处理",
    "主估计目标: ICU-level HD 累计发生率 (CIF)"
  ];
  fgPoints.forEach((p, i) => {
    const y = 1.5 + i * 0.52;
    slide.addShape(pres.shapes.OVAL, {
      x: 5.3, y: y + 0.07, w: 0.12, h: 0.12,
      fill: { color: theme.primary }
    });
    slide.addText(p, {
      x: 5.55, y: y, w: 3.8, h: 0.46,
      fontSize: 11, fontFace: "Microsoft YaHei",
      color: "334155", bold: false, align: "left", margin: 0, valign: "top"
    });
  });

  // Bottom summary
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.0, w: 9, h: 0.45,
    fill: { color: theme.primary }
  });
  slide.addText("early sepsis 不再作为主队列限制, 转为预设亚组  |  DHF 资格变量不进预测器", {
    x: 0.5, y: 5.0, w: 9, h: 0.45,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: true, align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("4", {
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
  pres.writeFile({ fileName: "slide-04-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
