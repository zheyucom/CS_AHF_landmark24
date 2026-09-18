const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 17, title: 'Blinded Annotation' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("盲法人工标注包: 300 条 + 60 条独立复核", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Annotation workflow
  const steps = [
    { n: "1", title: "分层抽样 300 条", desc: "预抽取样本, 覆盖三层结构\n(controlled_annotation_20260830_v2)" },
    { n: "2", title: "临床盲法标注", desc: "按标注指南逐条阅读 report_text\n填写 congestion / 替代解释 / 可用性" },
    { n: "3", title: "60 条独立复核", desc: "第二轮 blinded 复核\n不先查看第一轮标签" },
    { n: "4", title: "冲突裁决", desc: "分歧案例裁决\n估计 PPV / kappa / 替代解释" }
  ];

  steps.forEach((s, i) => {
    const x = 0.5 + i * 2.3;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.0, w: 2.1, h: 1.9,
      fill: { color: "F8FAFC" },
      line: { color: theme.accent, width: 0.5 }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.0, w: 2.1, h: 0.06,
      fill: { color: theme.primary }
    });

    slide.addShape(pres.shapes.OVAL, {
      x: x + 0.75, y: 1.15, w: 0.6, h: 0.6,
      fill: { color: theme.secondary }
    });
    slide.addText(s.n, {
      x: x + 0.75, y: 1.15, w: 0.6, h: 0.6,
      fontSize: 22, fontFace: "Georgia",
      color: "FFFFFF", bold: true,
      align: "center", valign: "middle"
    });

    slide.addText(s.title, {
      x: x + 0.1, y: 1.85, w: 1.9, h: 0.25,
      fontSize: 11.5, fontFace: "Microsoft YaHei",
      color: theme.primary, bold: true, align: "center", margin: 0
    });
    slide.addText(s.desc, {
      x: x + 0.1, y: 2.1, w: 1.9, h: 0.75,
      fontSize: 8.5, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "center", margin: 0, valign: "top"
    });

    if (i < steps.length - 1) {
      slide.addText("→", {
        x: x + 2.1, y: 1.6, w: 0.2, h: 0.4,
        fontSize: 14, fontFace: "Georgia",
        color: "94A3B8", bold: true, align: "center", valign: "middle", margin: 0
      });
    }
  });

  // Annotation variables
  slide.addText("标注变量 (按 DHF_RADIOLOGY_ANNOTATION_GUIDE)", {
    x: 0.5, y: 3.1, w: 9, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const vars = [
    "reviewer_id  |  congestion_label (是/否/不确定)  |  alternative_explanation_label  |  report_available_pre_t0_label  |  comments",
    "不能确定时标为 indeterminate / unclear, 不强行判定阳性",
    "保留原列名、行数、annotation_id 与 report_text"
  ];

  vars.forEach((v, i) => {
    const y = 3.45 + i * 0.35;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: y, w: 9, h: 0.3,
      fill: { color: i === 0 ? theme.light : (i % 2 === 0 ? "F8FAFC" : "FFFFFF") },
      line: { color: "E2E8F0", width: 0.3 }
    });
    slide.addText(v, {
      x: 0.7, y: y, w: 8.6, h: 0.3,
      fontSize: 9.5, fontFace: "Microsoft YaHei",
      color: "475569", bold: i === 0, align: "left", margin: 0, valign: "middle"
    });
  });

  // Deliverables after annotation
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.55, w: 9, h: 0.72,
    fill: { color: theme.primary }
  });
  slide.addText([
    { text: "标注完成后将自动计算: ", options: { bold: true } },
    { text: "规则筛查 PPV  |  漏检/误触发  |  Cohen kappa  |  patient-level 分层  |  三层 DHF 表型 (candidate / radiology-supported / multidomain)", options: {} }
  ], {
    x: 0.7, y: 4.55, w: 8.6, h: 0.72,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: false, align: "left", margin: 0, valign: "middle"
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("17", {
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
  pres.writeFile({ fileName: "slide-17-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
