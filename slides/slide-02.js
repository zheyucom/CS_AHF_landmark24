const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'toc', index: 2, title: 'Table of Contents' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("汇报提纲", {
    x: 0.5, y: 0.35, w: 9, h: 0.6,
    fontSize: 32, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  slide.addShape(pres.shapes.LINE, {
    x: 0.5, y: 0.95, w: 9, h: 0,
    line: { color: theme.accent, width: 1 }
  });

  const sections = [
    { num: "01", title: "研究背景与方案演进", desc: "ESC 2026 DHF 更新  |  为何转竞争风险模型" },
    { num: "02", title: "研究设计总纲", desc: "T12 landmark  |  三态随访  |  主事件与竞争事件" },
    { num: "03", title: "队列重建与特征冻结", desc: "v3.3 eligible n=5,555  |  45 个无泄露紧凑预测器" },
    { num: "04", title: "主模型与验证结果", desc: "Fine-Gray AUC 0.762  |  person-period 补充" },
    { num: "05", title: "DHF 多域表型验证", desc: "106/107 BigQuery 放射科证据  |  300/60 盲法标注" },
    { num: "06", title: "下一步与需导师决策", desc: "标注裁决 → 冻结队列 → 最终模型与敏感性" }
  ];

  sections.forEach((s, i) => {
    const col = i < 3 ? 0 : 1;
    const row = i % 3;
    const x = 0.5 + col * 4.7;
    const y = 1.3 + row * 1.3;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 0.6, h: 0.6,
      fill: { color: theme.primary }
    });
    slide.addText(s.num, {
      x: x, y: y, w: 0.6, h: 0.6,
      fontSize: 20, fontFace: "Georgia",
      color: "FFFFFF", bold: true,
      align: "center", valign: "middle", margin: 0
    });

    slide.addText(s.title, {
      x: x + 0.75, y: y, w: 3.7, h: 0.35,
      fontSize: 16, fontFace: "Microsoft YaHei",
      color: theme.primary, bold: true, align: "left", margin: 0, valign: "middle"
    });

    slide.addText(s.desc, {
      x: x + 0.75, y: y + 0.35, w: 3.7, h: 0.3,
      fontSize: 10, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "left", margin: 0, valign: "middle"
    });
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("2", {
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
  pres.writeFile({ fileName: "slide-02-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
