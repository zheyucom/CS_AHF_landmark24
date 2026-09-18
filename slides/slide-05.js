const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 5, title: 'Study Question' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("研究问题与目标人群界定", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 24, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Left panel: Study question
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.3, h: 4.1,
    fill: { color: "F8FAFC" },
    line: { color: theme.accent, width: 0.5 }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.3, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("一句话研究问题", {
    x: 0.7, y: 1.2, w: 4, h: 0.35,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  slide.addText(
    "在 pre-T0 DHF 操作性表型的成人首次 ICU 患者中,\n\n" +
    "能否使用 ICU 入科 0-12h 可获得的结构化信息,\n\n" +
    "预测 T12 至 min(T60, 活着离开 index ICU) 期间\n" +
    "ICU 内血流动力学恶化 (治疗升级或死亡) 的累计发生率?",
    {
      x: 0.7, y: 1.6, w: 3.9, h: 3.3,
      fontSize: 12, fontFace: "Microsoft YaHei",
      color: "334155", bold: false, align: "left", margin: 0, valign: "top"
    }
  );

  // Right panel: Key design components
  slide.addText("核心设计要素", {
    x: 5.1, y: 1.0, w: 4.5, h: 0.35,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const conditions = [
    { num: "1", title: "分析单位", desc: "每位患者 index hospitalization 内首次 ICU stay, 每患者一行" },
    { num: "2", title: "主估计目标", desc: "ICU-level HD cumulative incidence (CIF), 非简单二分类概率" },
    { num: "3", title: "竞争事件", desc: "活着离开 index ICU (n=2,935), 与主事件竞争" },
    { num: "4", title: "主方法", desc: "Fine-Gray competing-risk; 补充 1h person-period landmark" },
    { num: "5", title: "表型立场", desc: "DHF 为操作性表型; early sepsis 为预设亚组" }
  ];

  conditions.forEach((c, i) => {
    const y = 1.4 + i * 0.75;

    slide.addShape(pres.shapes.OVAL, {
      x: 5.1, y: y, w: 0.4, h: 0.4,
      fill: { color: theme.secondary }
    });
    slide.addText(c.num, {
      x: 5.1, y: y, w: 0.4, h: 0.4,
      fontSize: 15, fontFace: "Georgia",
      color: "FFFFFF", bold: true,
      align: "center", valign: "middle"
    });

    slide.addText(c.title, {
      x: 5.6, y: y, w: 3.9, h: 0.2,
      fontSize: 12, fontFace: "Microsoft YaHei",
      color: theme.primary, bold: true, align: "left", margin: 0
    });

    slide.addText(c.desc, {
      x: 5.6, y: y + 0.21, w: 3.9, h: 0.35,
      fontSize: 9.5, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "left", margin: 0
    });
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("5", {
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
  pres.writeFile({ fileName: "slide-05-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
