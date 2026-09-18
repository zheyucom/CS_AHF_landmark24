const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 8, title: 'Cohort v3.3' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("队列重建: v3.3 eligible cohort", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 24, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Cohort flow steps
  const steps = [
    { n: "5,564", label: "v3.2 AHF-by-T12 候选队列", detail: "每位患者 index hospitalization 内首次 ICU stay", drop: null },
    { n: "9", label: "排除 T12 前/时死亡", detail: "landmark eligibility reconciliation", drop: "-9" },
    { n: "5,555", label: "v3.3 eligible cohort", detail: "strict label + 三态随访 + person-period 对齐", drop: null, highlight: true },
    { n: "454", label: "主事件", detail: "支持升级/NEE>=30min 或 ICU 内死亡", drop: null, sub: true },
    { n: "2,935 / 2,166", label: "竞争事件 / 行政删失", detail: "alive ICU discharge / T60 仍滞留无事件", drop: null, sub: true }
  ];

  const startY = 1.0;
  const stepH = 0.72;
  const stepGap = 0.1;

  steps.forEach((s, i) => {
    const y = startY + i * (stepH + stepGap);
    const isHl = s.highlight;
    const isSub = s.sub;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: isSub ? 1.3 : 0.8, y: y, w: 5.5, h: stepH,
      fill: { color: isHl ? theme.secondary : (isSub ? "FFFFFF" : (i % 2 === 0 ? "F1F5F9" : "F8FAFC")) },
      line: isHl ? { color: theme.secondary, width: 1.2 } : (isSub ? { color: theme.accent, width: 0.5 } : { color: "CBD5E1", width: 0.5 })
    });

    slide.addText(s.n, {
      x: isSub ? 1.5 : 1.0, y: y, w: 1.7, h: stepH,
      fontSize: isHl ? 24 : 17, fontFace: "Georgia",
      color: isHl ? "FFFFFF" : theme.primary, bold: true,
      align: "left", valign: "middle", margin: 0
    });

    slide.addText(s.label, {
      x: isSub ? 3.2 : 2.7, y: y + 0.08, w: 3.5, h: 0.28,
      fontSize: isSub ? 11 : 13, fontFace: "Microsoft YaHei",
      color: isHl ? "FFFFFF" : theme.primary, bold: true, align: "left", margin: 0
    });

    slide.addText(s.detail, {
      x: isSub ? 3.2 : 2.7, y: y + 0.37, w: 3.5, h: 0.3,
      fontSize: 9, fontFace: "Microsoft YaHei",
      color: isHl ? "FECACA" : "64748B", bold: false, align: "left", margin: 0
    });

    if (s.drop) {
      slide.addText(s.drop, {
        x: 6.5, y: y, w: 1.2, h: stepH,
        fontSize: 13, fontFace: "Georgia",
        color: "94A3B8", bold: false, align: "left", valign: "middle", margin: 0
      });
    }

    if (i < steps.length - 1) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 3.5, y: y + stepH, w: 0.12, h: stepGap,
        fill: { color: "CBD5E1" }
      });
    }
  });

  // Right panel: key numbers
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 7.1, y: 1.0, w: 2.6, h: 4.2,
    fill: { color: theme.light }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 7.1, y: 1.0, w: 2.6, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("关键数字", {
    x: 7.25, y: 1.15, w: 2.3, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  const nums = [
    { v: "5,555", l: "eligible stays" },
    { v: "454", l: "主事件 (8.2%)" },
    { v: "2,935", l: "竞争事件 alive ICU discharge" },
    { v: "2,166", l: "行政删失 (T60 no event)" },
    { v: "176,525", l: "person-period 行数" },
    { v: "1,498 / 151", l: "early sepsis 亚组 stays/events" },
    { v: "4,057 / 303", l: "non-sepsis stays/events" }
  ];

  nums.forEach((n, i) => {
    const y = 1.55 + i * 0.5;
    slide.addText(n.v, {
      x: 7.25, y: y, w: 2.3, h: 0.28,
      fontSize: 14, fontFace: "Georgia",
      color: theme.secondary, bold: true, align: "left", margin: 0
    });
    slide.addText(n.l, {
      x: 7.25, y: y + 0.28, w: 2.3, h: 0.2,
      fontSize: 9, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "left", margin: 0
    });
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("8", {
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
  pres.writeFile({ fileName: "slide-08-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
