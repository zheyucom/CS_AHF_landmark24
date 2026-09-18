const pptxgen = require("pptxgenjs");

const slideConfig = { type: 'content', index: 14, title: 'Top Predictors' };

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: theme.primary }
  });

  slide.addText("Fine-Gray 主模型: 关键预测因子 (全模型系数)", {
    x: 0.5, y: 0.25, w: 9, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: true, align: "left", margin: 0
  });

  // Top predictors by |coefficient| from Fine-Gray full model
  const features = [
    { name: "advanced_respiratory_support", hr: 1.563, dir: "↑ 风险" },
    { name: "rr_mean", hr: 1.379, dir: "↑ 风险" },
    { name: "first_unit_ccu_cicu", hr: 1.277, dir: "↑ 风险" },
    { name: "hr_mean", hr: 1.239, dir: "↑ 风险" },
    { name: "mbp_min", hr: 1.232, dir: "↑ 风险" },
    { name: "sbp_lt90_record_prop", hr: 1.132, dir: "↑ 风险" },
    { name: "map_lt65_record_prop", hr: 1.118, dir: "↑ 风险" },
    { name: "dbp_min", hr: 1.125, dir: "↑ 风险" },
    { name: "bun_max", hr: 1.148, dir: "↑ 风险" },
    { name: "urineoutput_0_12h_total", hr: 0.808, dir: "↓ 风险" },
    { name: "mbp_mean", hr: 0.793, dir: "↓ 风险" },
    { name: "sbp_min", hr: 0.730, dir: "↓ 风险" }
  ];

  const maxHR = 1.6;
  const barStartX = 4.3;
  const barMaxW = 4.0;
  const rowH = 0.34;
  const startY = 1.0;

  features.forEach((f, i) => {
    const y = startY + i * rowH;
    const isUp = f.hr >= 1;
    const barW = (Math.log(f.hr) / Math.log(maxHR)) * barMaxW;

    slide.addText(f.name, {
      x: 0.5, y: y, w: 3.6, h: rowH - 0.04,
      fontSize: 9, fontFace: "Georgia",
      color: "334155", bold: false, align: "right", margin: 0, valign: "middle"
    });

    const color = isUp ? theme.secondary : theme.primary;
    if (isUp) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: barStartX, y: y + 0.04, w: barW, h: rowH - 0.08,
        fill: { color: color }
      });
    } else {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: barStartX + barMaxW - barW, y: y + 0.04, w: barW, h: rowH - 0.08,
        fill: { color: color }
      });
    }

    slide.addText("HR " + f.hr.toFixed(3), {
      x: barStartX + barMaxW + 0.1, y: y, w: 1.3, h: rowH - 0.04,
      fontSize: 9, fontFace: "Georgia",
      color: color, bold: true, align: "left", margin: 0, valign: "middle"
    });
    slide.addText(f.dir, {
      x: 8.6, y: y, w: 1.0, h: rowH - 0.04,
      fontSize: 8.5, fontFace: "Microsoft YaHei",
      color: "64748B", bold: false, align: "left", margin: 0, valign: "middle"
    });
  });

  // Legend
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.05, w: 0.15, h: 0.15, fill: { color: theme.secondary }
  });
  slide.addText("↑ 风险 (SHR>1)", {
    x: 0.7, y: 5.03, w: 1.2, h: 0.2, fontSize: 9, color: "334155", margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 2.0, y: 5.05, w: 0.15, h: 0.15, fill: { color: theme.primary }
  });
  slide.addText("↓ 风险 (SHR<1)", {
    x: 2.2, y: 5.03, w: 1.2, h: 0.2, fontSize: 9, color: "334155", margin: 0
  });

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.3, y: 5.0, w: 5.2, h: 0.28,
    fill: { color: theme.light }
  });
  slide.addText("生理信号: 呼吸支持、低血压负担、肾功能、尿量  |  源自 0-12h 窗口, 无泄露", {
    x: 4.4, y: 5.0, w: 5.0, h: 0.28,
    fontSize: 9, fontFace: "Microsoft YaHei",
    color: theme.primary, bold: false, align: "center", valign: "middle", margin: 0
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText("14", {
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
  pres.writeFile({ fileName: "slide-14-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
