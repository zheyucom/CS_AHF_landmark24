import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "/Users/zheyu/Desktop/CS_AHF_landmark24";
const inputPath = `${root}/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_reviewed.csv`;
const outputPath = `${root}/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_reviewed.xlsx`;
const csvText = await fs.readFile(inputPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "人工核对" });
const sheet = workbook.worksheets.getItem("人工核对");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(4);

const header = sheet.getRange("A1:AM1");
header.format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF", size: 10 },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#1F4E78" },
};
header.format.rowHeight = 34;

const sourceRange = sheet.getRange("A2:Q51");
sourceRange.format = {
  font: { color: "#374151", size: 9 },
  verticalAlignment: "top",
  wrapText: true,
};
const reviewRange = sheet.getRange("R2:AM51");
reviewRange.format = {
  fill: "#FFF2CC",
  font: { color: "#111827", size: 9 },
  verticalAlignment: "top",
  wrapText: true,
};
sheet.getRange("R1:AM1").format.fill = "#9A6700";
sheet.getRange("R1:AM1").format.font = { bold: true, color: "#FFFFFF", size: 10 };

for (const [range, width] of [
  ["A:A", 11], ["B:B", 12], ["C:C", 7], ["D:D", 15],
  ["E:J", 18], ["K:L", 28], ["M:N", 55], ["O:Q", 18],
  ["R:R", 14], ["S:T", 20], ["U:U", 32], ["V:X", 16], ["Y:Y", 25],
  ["Z:AA", 18], ["AB:AD", 22], ["AE:AE", 24], ["AF:AG", 20],
  ["AH:AL", 22], ["AM:AM", 36],
]) sheet.getRange(range).format.columnWidth = width;

sheet.getRange("E2:J51").setNumberFormat("yyyy-mm-dd hh:mm:ss");
sheet.getRange("S2:S51").setNumberFormat("yyyy-mm-dd hh:mm:ss");
sheet.getRange("AF2:AF51").setNumberFormat("yyyy-mm-dd hh:mm:ss");
sheet.getRange("AI2:AL51").setNumberFormat("yyyy-mm-dd hh:mm:ss");

const validations = [
  ["T2:T51", ["nursing_event_time", "icu_document_event_time", "structured_proxy_uncertain", "uncertain_conflict"]],
  ["V2:V51", ["yes", "no", "uncertain"]],
  ["W2:W51", ["yes", "no", "uncertain"]],
  ["X2:X51", ["yes", "no", "uncertain"]],
  ["Z2:Z51", ["report_time", "completion_time", "unknown"]],
  ["AA2:AA51", ["valid", "revised_final", "void", "uninterpretable"]],
  ["AB2:AB51", ["yes", "no", "uncertain"]],
  ["AD2:AD51", ["yes", "no", "uncertain"]],
  ["AE2:AE51", ["candidate", "multidomain_draft", "echo_supported_draft", "not_supported", "unknown"]],
  ["AG2:AG51", ["icu_document_out", "icu_transfer_note", "structured_proxy", "death_record", "unknown"]],
  ["AH2:AH51", ["alive_transfer", "death_in_icu", "death_after_icu", "automatic_discharge", "hospital_discharge", "transfer_out", "unknown"]],
  ["AJ2:AJ51", ["treatment_escalation", "icu_death", "composite", "unknown"]],
];
for (const [range, values] of validations) {
  sheet.getRange(range).dataValidation = { rule: { type: "list", values } };
}

const notes = workbook.worksheets.add("填写说明");
notes.showGridLines = false;
notes.getRange("A1:D1").merge();
notes.getRange("A1").values = [["Gate 3 人工核对说明"]];
notes.getRange("A1:D1").format = { font: { bold: true, size: 14, color: "#1F2937" }, verticalAlignment: "center" };
notes.getRange("A1:D1").format.rowHeight = 26;
const guide = [
  ["步骤", "需要填写的字段", "可选值/填写规则", "审稿风险控制"],
  ["1. T0", "reviewer_id; t0_time_final; t0_source_final; t0_discrepancy_reason", "来源：nursing_event / icu_document / structured_proxy / unresolved", "普通病程录入病房时间、出ICU记录中的入院时间不能直接作 ICU T0"],
  ["2. 心超三态", "echo_completed_final; echo_result_available_final; echo_abnormal_support_final", "yes / no / uncertain", "不要使用数据库“是否异常”字段替代正文判读"],
  ["3. 异常域", "echo_abnormal_domains", "LV_systolic, diastolic_filling, RV_PH, valve, pericardium, other", "LVEF >=50% 不能单独排除 HFpEF"],
  ["4. DHF 层级", "hf_anchor_support_final; decompensation_domain_final; management_evidence_final; dhf_tier_final", "按病例可追溯证据填写；BNP 单独不能确诊", "资格证据与未来结局变量分开"],
  ["5. ICU 结局", "icu_out_time_final; icu_out_source_final; outcome_status_final", "区分转病房、死亡、自动出院、最终出院和未知", "出ICU不等于最终出院"],
  ["6. T12 后事件", "event_time_final; event_component_final; competing_time_final; censor_time_final", "只记录 T12 后新发生/相对基线持续升高的实际升级或 ICU 死亡", "仅有医嘱区间时在 review_comments 说明，不能声称执行级 eMAR"],
  ["7. 备注", "review_comments", "写文书名称、时间冲突、无法判断原因", "保留最小可复核证据，不改动源字段"],
];
notes.getRange("A3:D10").values = guide;
notes.getRange("A3:D3").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center" };
notes.getRange("A4:D10").format = { font: { size: 10, color: "#374151" }, wrapText: true, verticalAlignment: "top" };
notes.getRange("A:A").format.columnWidth = 16;
notes.getRange("B:B").format.columnWidth = 52;
notes.getRange("C:C").format.columnWidth = 54;
notes.getRange("D:D").format.columnWidth = 58;
notes.getRange("A3:D10").format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
notes.getRange("A3:D10").format.rowHeight = 36;

await workbook.recalculate();
const inspect = await workbook.inspect({ kind: "sheet,region", maxChars: 4000, tableMaxRows: 3, tableMaxCols: 8 });
console.log(inspect.ndjson ?? inspect);
const preview = await workbook.render({ sheetName: "填写说明", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(`${root}/project_control/internal_validation/20260912/internal_gate3_manual_review_20260913_preview.png`, new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`saved ${outputPath}`);
