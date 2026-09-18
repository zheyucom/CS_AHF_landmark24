const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 10, title: 'Feature Freeze' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("特征冻结合同: 45 个预设紧凑预测器 (090A-090D)", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Three feature groups
  const groups = [
    {
      title: "1. 基线人口学 & 就诊入口",
      items: ["age, female/male", "首次 ICU unit 类型 (MICU/CCU/CVICU/SICU)", "CHF 表现: pre-T0 DHF candidate"],
      color: theme.primary
    },
    {
      title: "2. 0-12h 临床状态摘要",
      items: ["生命体征: HR/SBP/MBP/RR/SpO2 mean,min,max,delta", "灌注: lactate, baseexcess, ph, shock index", "肾: creatinine, BUN  |  电解质  |  血象"],
      color: theme.secondary
    },
    {
      title: "3. 0-12h 支持治疗结构",
      items: ["vasoactive/inotrope 有无与结构", "呼吸支持摘要", "尿量/液体平衡摘要"],
      color: theme.accent
    }
  ];

  groups.forEach((g, i) => {
    const x = 0.5 + i * 3.1;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 0.95, w: 2.9, h: 2.2,
      fill: { color: "F8FAFC" },
      line: { color: g.color, width: 0.75 }
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 0.95, w: 2.9, h: 0.06,
      fill: { color: g.color }
    });

    slide.addText(g.title, {
      x: x + 0.15, y: 1.1, w: 2.6, h: 0.5,
      fontSize: 12, fontFace: "Microsoft YaHei",
      color: g.color, bold: true, align: "left", margin: 0, valign: "top"
    });

    g.items.forEach((item, j) => {
      const y = 1.65 + j * 0.5;
      slide.addShape(pres.shapes.OVAL, {
        x: x + 0.15, y: y + 0.06, w: 0.1, h: 0.1,
        fill: { color: g.color }
      });
      slide.addText(item, {
        x: x + 0.35, y: y, w: 2.4, h: 0.45,
        fontSize: 9, fontFace: "Microsoft YaHei",
        color: "334155", bold: false, align: "left", margin: 0, valign: "top"
      });
    });
  });

  // Blacklist principles
  slide.addText("建模合同: 黑名单与无泄露原则", {
    x: 0.5, y: 3.3, w: 9, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const blacklist = [
    "ID / 时间锚点 / 结局列: subject_id, stay_id, intime, landmark12_time, final_state, event_type",
    "AHF 资格变量: hf_icd_*, iv_loop_rx_early12, ntprobnp_ge300 等一律不进预测器",
    "感染/脓毒症资格变量: suspected_infection_*, early_sepsis12_* 仅作亚组标记",
    "outcome-derived baseline: nee_0_12h_max, vasoactive_agent_count 等不进主模型",
    "所有 preprocessing / 变量选择 / 插补 / 权重模型均在训练折内完成 (无泄露)"
  ];

  blacklist.forEach((b, i) => {
    const y = 3.65 + i * 0.27;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: y, w: 9, h: 0.24,
      fill: { color: i % 2 === 0 ? "F8FAFC" : "FFFFFF" },
      line: { color: "E2E8F0", width: 0.3 }
    });
    slide.addText(b, {
      x: 0.65, y: y, w: 8.7, h: 0.24,
      fontSize: 9.5, fontFace: "Microsoft YaHei",
      color: "475569", bold: false, align: "left", margin: 0, valign: "middle"
    });
  });

  // Bottom note
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.05, w: 9, h: 0.42,
    fill: { color: theme.light }
  });
  slide.addText("090D QC 全通过: 唯一性 / 白名单 / manifest / 缺失矩阵 / 特征×标签×person-period 三表连接", {
    x: 0.5, y: 5.05, w: 9, h: 0.42,
    fontSize: 10.5, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("10", {
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
  pres.writeFile({ fileName: "slide-10-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
