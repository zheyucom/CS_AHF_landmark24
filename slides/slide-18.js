const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'summary', index: 18, title: 'Summary & Next Steps' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("总结与下一步计划", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 24, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Left: key takeaways
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 3.5,
    fill: { color: "F8FAFC" },
    line: { color: theme.accent, width: 0.5 }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.0, w: 4.4, h: 0.06,
    fill: { color: theme.secondary }
  });

  slide.addText("当前进展总结", {
    x: 0.7, y: 1.15, w: 4, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const takeaways = [
    "方案演进: DHF 操作性表型 + Fine-Gray 竞争风险主线确定 (ESC 2026 对齐)",
    "v3.3 队列 n=5,555, 三态随访 (454 事件 / 2,935 竞争 / 2,166 删失) 审计通过",
    "45 个无泄露紧凑预测器冻结, 090A-090D QC 全通过",
    "Fine-Gray 48h OOF AUC 0.7622 / Brier 0.0652, 校准良好",
    "person-period 补充模型 AUC 0.7681, 结果一致",
    "106/107 BigQuery radiology: 5,549 有效候选, 4,303 报告, 300/60 盲法标注包就绪"
  ];

  takeaways.forEach((t, i) => {
    const y = 1.55 + i * 0.48;
    slide.addShape(pres.shapes.OVAL, {
      x: 0.75, y: y + 0.06, w: 0.12, h: 0.12,
      fill: { color: theme.secondary }
    });
    slide.addText(t, {
      x: 1.0, y: y, w: 3.8, h: 0.42,
      fontSize: 9.5, fontFace: "Microsoft YaHei",
      color: "334155", bold: false, align: "left", margin: 0, valign: "top"
    });
  });

  // Right: next steps
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.0, w: 4.4, h: 3.5,
    fill: { color: theme.light }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.0, w: 4.4, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("下一步计划", {
    x: 5.4, y: 1.15, w: 4, h: 0.3,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  const nextSteps = [
    { num: "1", title: "完成标注与裁决", desc: "300 条 + 60 条独立复核 → PPV / kappa / 替代解释" },
    { num: "2", title: "冻结 DHF 三层表型", desc: "candidate / radiology-supported / multidomain, 导师确认" },
    { num: "3", title: "重算事件与 EPV", desc: "各表型层事件数、竞争、删失与 EPV" },
    { num: "4", title: "重跑最终模型", desc: "Fine-Gray + person-period + 预设敏感性 (IPCW/complete60 等)" },
    { num: "5", title: "清理旧文档边界", desc: "2,424/334 与旧 outputs 仅作历史/诊断材料" }
  ];

  nextSteps.forEach((s, i) => {
    const y = 1.5 + i * 0.58;
    slide.addShape(pres.shapes.OVAL, {
      x: 5.45, y: y, w: 0.3, h: 0.3,
      fill: { color: theme.primary }
    });
    slide.addText(s.num, {
      x: 5.45, y: y, w: 0.3, h: 0.3,
      fontSize: 12, fontFace: "Georgia",
      color: "FFFFFF", bold: true,
      align: "center", valign: "middle"
    });
    slide.addText(s.title, {
      x: 5.85, y: y, w: 3.6, h: 0.2,
      fontSize: 11, fontFace: "Microsoft YaHei",
      color: theme.primary, bold: true, align: "left", margin: 0
    });
    slide.addText(s.desc, {
      x: 5.85, y: y + 0.2, w: 3.6, h: 0.32,
      fontSize: 9, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "left", margin: 0
    });
  });

  // Bottom bar: decisions needed
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.7, w: 9, h: 0.62,
    fill: { color: theme.primary }
  });
  slide.addText("需导师决策: ① 主队列取 radiology-supported 还是 multidomain DHF  ② 本院外部验证按先审计 → 锁模原样验证 → 再校准三阶段推进  ③ 是否清理旧 2,424/334 入口文档", {
    x: 0.5, y: 4.7, w: 9, h: 0.62,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: "FFFFFF", bold: false, align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("18", {
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
  pres.writeFile({ fileName: "slide-18-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
