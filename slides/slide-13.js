const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 13, title: 'Person-period & Sensitivity' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("补充模型: 1h Person-period Landmark Survival", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Top comparison table
  slide.addText("主模型 vs 补充模型 (5 折 OOF, 48h)", {
    x: 0.5, y: 0.9, w: 9, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: true, align: "left", margin: 0
  });

  const tableHeaders = ["模型", "结构", "AUC", "Brier", "说明"];
  const colWs = [2.0, 2.2, 1.2, 1.2, 2.4];
  const rows = [
    { cells: ["Fine-Gray (主)", "competing-risk CIF", "0.7622", "0.0652", "主估计目标, 直接输出累计发生率"], hl: true },
    { cells: ["1h person-period", "离散 landmark 生存", "0.7681", "0.0655", "概率递推误差 <1e-14, 一致性验证"], hl: false },
    { cells: ["缺失指示器敏感性", "主模型 + missing ind", "0.7605", "0.0649", "结果与主模型接近"], hl: false }
  ];

  // Header
  let xPos = 0.5;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.25, w: 9.0, h: 0.35,
    fill: { color: theme.primary }
  });
  xPos = 0.5;
  tableHeaders.forEach((h, i) => {
    slide.addText(h, {
      x: xPos + 0.1, y: 1.25, w: colWs[i] - 0.1, h: 0.35,
      fontSize: 10, fontFace: "Microsoft YaHei",
      color: "FFFFFF", bold: true, align: "left", valign: "middle", margin: 0
    });
    xPos += colWs[i];
  });

  rows.forEach((r, i) => {
    const y = 1.6 + i * 0.55;
    const bg = r.hl ? theme.light : (i % 2 === 0 ? "F8FAFC" : "FFFFFF");
    xPos = 0.5;
    r.cells.forEach((c, j) => {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: xPos, y: y, w: colWs[j], h: 0.55,
        fill: { color: bg },
        line: { color: "E2E8F0", width: 0.4 }
      });
      if (r.hl && j === 0) {
        slide.addShape(pres.shapes.RECTANGLE, {
          x: xPos, y: y, w: 0.05, h: 0.55,
          fill: { color: theme.secondary }
        });
      }
      slide.addText(c, {
        x: xPos + 0.12, y: y, w: colWs[j] - 0.12, h: 0.55,
        fontSize: j === 2 || j === 3 ? 13 : 9.5,
        fontFace: j === 2 || j === 3 ? "Georgia" : "Microsoft YaHei",
        color: r.hl && j === 0 ? theme.secondary : (j === 2 || j === 3 ? theme.primary : "334155"),
        bold: r.hl && (j === 0 || j === 2 || j === 3),
        align: "left", valign: "middle", margin: 0
      });
      xPos += colWs[j];
    });
  });

  // Bottom: stability review summary
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.5, w: 9, h: 1.7,
    fill: { color: "F8FAFC" },
    line: { color: theme.accent, width: 0.5 }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.5, w: 0.08, h: 1.7,
    fill: { color: theme.primary }
  });

  slide.addText("第一版稳定性审阅要点", {
    x: 0.7, y: 3.6, w: 8.6, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  const stabilityPoints = [
    "45 个预测器中 37/45 在 5 折保持同一系数方向, 32/45 五折完全同向",
    "主模型 top 10% 风险组事件率 24.1%, 捕获 29.5% 事件 (风险富集有效)",
    "十分位校准平均绝对误差约 0.0057, 校准良好",
    "缺失指示器、三态随访标签均与主结果一致"
  ];
  stabilityPoints.forEach((p, i) => {
    const y = 3.95 + i * 0.3;
    slide.addShape(pres.shapes.OVAL, {
      x: 0.7, y: y + 0.06, w: 0.11, h: 0.11,
      fill: { color: theme.secondary }
    });
    slide.addText(p, {
      x: 0.95, y: y, w: 8.3, h: 0.26,
      fontSize: 10, fontFace: "Microsoft YaHei",
      color: "334155", bold: false, align: "left", margin: 0
    });
  });

  // Bottom note
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.25, w: 9, h: 0.25,
    fill: { color: theme.light }
  });
  slide.addText("注: 以上为第一版结果, 供方向确认; 表型冻结后将重跑最终模型, 所有论文数字以冻结 run 为准", {
    x: 0.5, y: 5.25, w: 9, h: 0.25,
    fontSize: 9, fontFace: "Microsoft YaHei",
    color: theme.secondary, bold: false, align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("13", {
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
  pres.writeFile({ fileName: "slide-13-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
