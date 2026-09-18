const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'cover',
  index: 1,
  title: 'Cover'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.08,
    fill: { color: theme.secondary }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.545, w: 10, h: 0.08,
    fill: { color: theme.secondary }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 1.75, w: 0.06, h: 2.1,
    fill: { color: theme.accent }
  });

  slide.addText("DHF 操作性表型 ICU 患者血流动力学恶化", {
    x: 0.8, y: 1.3, w: 8.6, h: 0.8,
    fontSize: 30, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: true, align: "left", margin: 0
  });

  slide.addText("竞争风险预测: Fine-Gray 主模型", {
    x: 0.8, y: 2.05, w: 8.6, h: 0.7,
    fontSize: 26, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: true, align: "left", margin: 0
  });

  slide.addText("T12 Landmark 后至 T60 / 活着离开 ICU 的 48h 预测  |  基于 MIMIC-IV 开发 + 本院外部验证", {
    x: 0.8, y: 2.75, w: 8.6, h: 0.5,
    fontSize: 15, fontFace: "Microsoft YaHei",
    color: theme.accent, bold: false, align: "left", margin: 0
  });

  slide.addShape(pres.shapes.LINE, {
    x: 0.8, y: 3.35, w: 3.5, h: 0,
    line: { color: theme.accent, width: 1.5 }
  });

  slide.addText("Early prediction of ICU hemodynamic deterioration in patients with a pre-T0 DHF operational phenotype: a competing-risk model (Fine-Gray) using MIMIC-IV, with local external validation", {
    x: 0.8, y: 3.55, w: 8.6, h: 0.8,
    fontSize: 13, fontFace: "Georgia",
    color: "FFFFFF", bold: false, align: "left", margin: 0, italic: true
  });

  slide.addText("组会汇报  |  2026.09.02  |  急诊医学专硕", {
    x: 0.8, y: 4.7, w: 8.4, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, bold: false, align: "left", margin: 0
  });

  slide.addText("数据源: MIMIC-IV (v3.3 eligible n=5,555)  |  主事件 454  |  竞争事件 2,935  |  删失 2,166", {
    x: 0.8, y: 5.05, w: 8.6, h: 0.4,
    fontSize: 11, fontFace: "Microsoft YaHei",
    color: theme.accent, bold: false, align: "left", margin: 0
  });

  return slide;
}

if (require.main === module) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  const theme = { primary: "003049", secondary: "780000", accent: "669bbc", light: "fdf0d5", bg: "FFFFFF" };
  createSlide(pres, theme);
  pres.writeFile({ fileName: "slide-01-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
