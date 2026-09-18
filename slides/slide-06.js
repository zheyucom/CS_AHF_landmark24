const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'section', index: 6, title: 'Section 02' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.15, h: 5.625,
    fill: { color: theme.secondary }
  });

  slide.addText("02", {
    x: 0.8, y: 1.3, w: 3, h: 1.2,
    fontSize: 80, fontFace: "Georgia",
    color: theme.accent, bold: true, align: "left", margin: 0
  });

  slide.addText("研究设计总纲", {
    x: 0.8, y: 2.5, w: 8, h: 0.7,
    fontSize: 32, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: true, align: "left", margin: 0
  });

  slide.addShape(pres.shapes.LINE, {
    x: 0.8, y: 3.2, w: 3, h: 0,
    line: { color: theme.accent, width: 1.5 }
  });

  slide.addText("T12 landmark  |  预测变量窗 0-12h  |  预测窗 T12–T60/出科  |  三态随访", {
    x: 0.8, y: 3.35, w: 8.4, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei",
    color: theme.light, bold: false, align: "left", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("6", {
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
  pres.writeFile({ fileName: "slide-06-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
