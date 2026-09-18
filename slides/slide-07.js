const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 7, title: 'Design Timeline & States' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("研究设计: Landmark 时间轴与三态随访", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Timeline
  const timelineY = 1.9;
  const tStart = 0.8;
  const tEnd = 9.2;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: tStart, y: timelineY, w: tEnd - tStart, h: 0.06,
    fill: { color: "CBD5E1" }
  });

  const predStart = tStart;
  const predWidth = (tEnd - tStart) * (12 / 60);
  const outStart = predStart + predWidth;
  const outWidth = (tEnd - tStart) * (48 / 60);

  slide.addShape(pres.shapes.RECTANGLE, {
    x: predStart, y: timelineY - 0.03, w: predWidth, h: 0.12,
    fill: { color: theme.secondary }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: outStart, y: timelineY - 0.03, w: outWidth, h: 0.12,
    fill: { color: theme.primary }
  });

  slide.addText("Predictor Window 0-12h", {
    x: predStart, y: timelineY - 0.55, w: predWidth, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "center", margin: 0
  });
  slide.addText("Prediction Window 12-60h (至 alive ICU discharge)", {
    x: outStart, y: timelineY - 0.55, w: outWidth, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "center", margin: 0
  });

  slide.addShape(pres.shapes.RECTANGLE, {
    x: tStart - 0.01, y: timelineY - 0.3, w: 0.03, h: 0.6,
    fill: { color: theme.primary }
  });
  slide.addText("T0 intime", {
    x: tStart - 0.55, y: timelineY + 0.15, w: 1.2, h: 0.25,
    fontSize: 9, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "center", margin: 0
  });

  slide.addShape(pres.shapes.RECTANGLE, {
    x: outStart - 0.01, y: timelineY - 0.35, w: 0.03, h: 0.7,
    fill: { color: theme.secondary }
  });
  slide.addText("T12 landmark", {
    x: outStart - 0.75, y: timelineY - 0.62, w: 1.5, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "center", margin: 0
  });

  slide.addText("T60", {
    x: tEnd - 0.5, y: timelineY + 0.15, w: 1, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "center", margin: 0
  });

  // Three-state follow-up
  slide.addText("三态随访 (v3.3 strict label)", {
    x: 0.5, y: 2.6, w: 9, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const states = [
    { name: "主事件", desc: "支持升级或 NEE 升高持续 >=30 min\n或 ICU 内死亡", n: "454", color: theme.secondary },
    { name: "竞争事件", desc: "活着离开 index ICU\n(ICU alive discharge)", n: "2,935", color: theme.primary },
    { name: "行政删失", desc: "T60 时仍滞留 ICU 且无事件\n(administrative censoring)", n: "2,166", color: "64748B" }
  ];

  states.forEach((s, i) => {
    const x = 0.5 + i * 3.1;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 2.95, w: 2.9, h: 1.6,
      fill: { color: "F8FAFC" },
      line: { color: s.color, width: 1 }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 2.95, w: 2.9, h: 0.06,
      fill: { color: s.color }
    });

    slide.addText(s.n, {
      x: x, y: 3.1, w: 2.9, h: 0.5,
      fontSize: 28, fontFace: "Georgia",
      color: s.color, bold: true, align: "center", margin: 0
    });
    slide.addText(s.name, {
      x: x, y: 3.6, w: 2.9, h: 0.3,
      fontSize: 12, fontFace: "Microsoft YaHei",
      color: theme.primary, bold: true, align: "center", margin: 0
    });
    slide.addText(s.desc, {
      x: x + 0.15, y: 3.9, w: 2.6, h: 0.6,
      fontSize: 9, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "center", margin: 0, valign: "top"
    });
  });

  // Bottom: design parameters
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.75, w: 9, h: 0.55,
    fill: { color: theme.light }
  });
  slide.addText("主模型: Fine-Gray competing-risk  |  补充: 1h person-period landmark survival (176,525 行)  |  主事件 = 治疗升级或 ICU 内死亡 (composite)", {
    x: 0.5, y: 4.75, w: 9, h: 0.55,
    fontSize: 11, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("7", {
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
  pres.writeFile({ fileName: "slide-07-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
