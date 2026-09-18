import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "/Users/zheyu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const ROOT = "/Users/zheyu/Desktop/CS_AHF_landmark24";
const PROJECT = path.join(ROOT, "CS_AHF_hemodynamic_deterioration_ml_project");
const DOCS = path.join(PROJECT, "docs");
const RAW = path.join(PROJECT, "data", "raw");
const OUT_V2 = path.join(PROJECT, "outputs_v2");

const GENERATED_AT = "2026-07-28";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        value += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        value += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(value);
      value = "";
    } else if (ch === "\n") {
      row.push(value);
      rows.push(row);
      row = [];
      value = "";
    } else if (ch !== "\r") {
      value += ch;
    }
  }
  if (value.length > 0 || row.length > 0) {
    row.push(value);
    rows.push(row);
  }
  if (rows.length === 0) return [];
  const header = rows[0];
  return rows.slice(1).filter((r) => r.some((v) => v !== "")).map((r) => {
    const obj = {};
    header.forEach((h, idx) => {
      obj[h] = r[idx] ?? "";
    });
    return obj;
  });
}

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (/[",\n\r]/.test(str)) return `"${str.replaceAll('"', '""')}"`;
  return str;
}

function toCsv(rows, headers) {
  return [
    headers.map(csvEscape).join(","),
    ...rows.map((row) => headers.map((h) => csvEscape(row[h])).join(",")),
  ].join("\n") + "\n";
}

async function readCsv(relPath) {
  const text = await fs.readFile(path.join(PROJECT, relPath), "utf8");
  return parseCsv(text);
}

async function readHeaderOnly(relPath) {
  const file = await fs.open(path.join(PROJECT, relPath));
  try {
    const chunks = [];
    const stream = file.createReadStream({ encoding: "utf8" });
    for await (const chunk of stream) {
      const idx = chunk.indexOf("\n");
      if (idx >= 0) {
        chunks.push(chunk.slice(0, idx));
        break;
      }
      chunks.push(chunk);
    }
    return parseCsv(chunks.join("") + "\n")[0]
      ? Object.keys(parseCsv(chunks.join("") + "\n")[0])
      : chunks.join("").split(",");
  } finally {
    await file.close();
  }
}

function row({
  domain,
  required_for,
  variable_name,
  role,
  priority,
  mimic_source_table,
  mimic_definition,
  mimic_time_window,
  mimic_unit = "",
  hospital_source_system,
  hospital_field_name = "",
  hospital_definition = "",
  hospital_unit = "",
  hospital_time_field = "",
  mapping_status = "not_mapped",
  extraction_difficulty,
  expected_solution,
  comments = "",
  current_v2_missing_pct = "",
  current_v2_kept = "",
  selection_frequency = "",
}) {
  return {
    domain,
    required_for,
    variable_name,
    role,
    priority,
    mimic_source_table,
    mimic_definition,
    mimic_time_window,
    mimic_unit,
    hospital_source_system,
    hospital_field_name,
    hospital_definition,
    hospital_unit,
    hospital_time_field,
    mapping_status,
    extraction_difficulty,
    expected_solution,
    comments,
    current_v2_missing_pct,
    current_v2_kept,
    selection_frequency,
  };
}

function inferDomain(name) {
  if (["subject_id", "hadm_id", "stay_id", "intime", "landmark12_time", "window60_time"].includes(name)) return "identity_time_anchor";
  if (name === "primary_outcome_flag" || name.startsWith("label_")) return "outcome_label";
  if (/^(age|female|male|first_unit_)/.test(name)) return "demographics_icu_unit";
  if (/^(hf_|acute_hf|iv_loop|ntprobnp|ahf_)/.test(name)) return "ahf_cohort_evidence";
  if (/^(early_sepsis|suspected_infection)/.test(name)) return "early_sepsis12";
  if (name.startsWith("charlson_")) return "comorbidity";
  if (/^(hr|sbp|dbp|mbp|rr|temp|spo2|vital_glucose)_/.test(name)) return "vitals_0_12h";
  if (/^(map_lt|shock_index|modified_shock_index|pulse_pressure|.*_slope_per_hour|.*_slope_n|.*_pair_n|vital_burden)/.test(name)) return "vital_burden_080A";
  if (/^(lactate|ph|baseexcess|bg_bicarbonate|po2|pco2|pf_ratio)/.test(name)) return "lactate_acid_base_0_12h";
  if (/^(creatinine|bun|sodium|potassium|chloride|chem_bicarbonate|aniongap|chem_glucose|albumin|wbc|hemoglobin|platelet|rdw|inr|pt|ptt|fibrinogen|d_dimer)/.test(name)) return "labs_0_12h";
  if (/^urineoutput|^low_urineoutput|urineoutput_available/.test(name)) return "urine_output_0_12h";
  if (name.startsWith("gcs_")) return "neurologic_gcs_0_12h";
  if (/^(ventilation|invasive_vent|noninvasive_vent|highflow|oxygen|advanced_respiratory)/.test(name)) return "respiratory_support_0_12h";
  if (/^(vaso|norepinephrine|epinephrine|dopamine|phenylephrine|vasopressin|dobutamine|milrinone|inotrope|nee_)/.test(name)) return "vasoactive_support_0_12h";
  return "other_current_v2_feature";
}

function inferSource(domain) {
  const sources = {
    identity_time_anchor: ["mimiciv_icu.icustays; mimiciv_hosp.admissions; study_ahf.model_080G_modeling_dataset_v2", "ADT/HIS/ICU admission system", "low", "用 ICU 入科时间生成 landmark12_time = ICU intime + 12h；全表统一脱敏 ID。"],
    outcome_label: ["study_ahf.outcome_064_primary_hd_deterioration_v1; study_ahf.audit_079_event_timing_components_v1", "ICU medication/eMAR + ADT death record", "high", "按 12-60h 内首次支持升级、NEE 升级或死亡逐项复刻，并保留事件时间用于审计。"],
    demographics_icu_unit: ["mimiciv_derived.icustay_detail; mimiciv_derived.age", "HIS/ADT/ICU admission system", "low", "年龄、性别、首个 ICU 单元一般可直接映射。"],
    ahf_cohort_evidence: ["mimiciv_hosp.diagnoses_icd; mimiciv_hosp.prescriptions/emar; mimiciv_hosp.labevents; study_ahf.cohort_061A/B", "HIS diagnosis + medication orders/eMAR + LIS", "medium", "诊断编码、急性心衰证据、早期 IV 袢利尿剂和 BNP/NT-proBNP 需统一时间窗和单位。"],
    early_sepsis12: ["mimiciv_derived.suspicion_of_infection; mimiciv_derived.sofa; mimiciv_derived.sepsis3", "抗菌药/培养医嘱 + LIS + ICU flowsheet", "high", "疑似感染时间和 SOFA 分组件必须能追溯到 ICU 入科前后；若无现成 SOFA，需由原始变量重算。"],
    comorbidity: ["mimiciv_derived.charlson; mimiciv_hosp.diagnoses_icd", "HIS diagnosis coding", "low", "使用 ICD 诊断生成 Charlson 分项；本院编码版本需保留 ICD-9/10 或本地映射。"],
    vitals_0_12h: ["mimiciv_derived.vitalsign", "ICU monitor/nursing vital signs", "low", "导出 0-12h 原始生命体征及 charttime，按相同规则清洗并汇总。"],
    vital_burden_080A: ["mimiciv_derived.vitalsign; study_ahf.model_080A_vital_burden_0_12h_v1", "ICU monitor/nursing vital signs", "low", "需要逐条记录的 HR/SBP/DBP/MAP/RR/SpO2 和时间；可重算负荷比例、shock index 和趋势斜率。"],
    lactate_acid_base_0_12h: ["mimiciv_derived.bg", "LIS blood gas/lactate", "medium", "抽取 charttime、lactate、pH、base excess、HCO3、PaO2/PaCO2；注意动静脉样本和单位。"],
    labs_0_12h: ["mimiciv_derived.chemistry; complete_blood_count; coagulation", "LIS", "low", "常规检验可直接映射，需保留采样时间并统一单位。"],
    urine_output_0_12h: ["mimiciv_derived.urine_output; mimiciv_icu.outputevents", "ICU nursing intake/output", "medium", "需要逐条尿量和记录时间；若只有班次汇总，需按 overlap 分摊到 0-12h。"],
    neurologic_gcs_0_12h: ["mimiciv_derived.gcs", "ICU nursing neurologic assessment", "medium", "GCS 总分和分组件需保留；镇静/无法评估需要标志。"],
    respiratory_support_0_12h: ["mimiciv_derived.ventilation; mimiciv_derived.oxygen_delivery", "呼吸机系统/护理记录", "medium", "统一 invasive/NIV/HFNC/oxygen 分类和 0-12h 暴露定义。"],
    vasoactive_support_0_12h: ["mimiciv_derived.vasoactive_agent; mimiciv_derived.norepinephrine_equivalent_dose", "ICU infusion pump/eMAR/medication administration", "high", "必须有药名、剂量、体重、起止时间、单位；按统一公式换算 NEE。"],
    other_current_v2_feature: ["study_ahf.model_080G_modeling_dataset_v2", "待按变量含义映射", "medium", "先回填所在系统、字段名、单位和时间字段，再由脚本审计可用性。"],
  };
  return sources[domain] ?? sources.other_current_v2_feature;
}

function featureDefinition(name, domain) {
  if (name.endsWith("_flag")) return "Binary flag derived before landmark12; 1 = present, 0 = absent.";
  if (name.endsWith("_n")) return "Number of available records in the 0-12h predictor window.";
  if (name.endsWith("_first")) return "First valid value in the 0-12h predictor window.";
  if (name.endsWith("_last")) return "Last valid value before landmark12.";
  if (name.endsWith("_mean")) return "Mean valid value in the 0-12h predictor window.";
  if (name.endsWith("_min")) return "Minimum valid value in the 0-12h predictor window.";
  if (name.endsWith("_max")) return "Maximum valid value in the 0-12h predictor window.";
  if (name.endsWith("_delta")) return "Last minus first valid value in the 0-12h predictor window.";
  if (name.includes("record_prop")) return "Proportion of valid 0-12h records meeting the specified threshold.";
  if (name.includes("slope_per_hour")) return "Linear trend slope per hour using valid 0-12h measurements.";
  if (name.includes("shock_index")) return "Derived hemodynamic index from HR and SBP/MAP before landmark12.";
  if (domain === "ahf_cohort_evidence") return "AHF evidence feature derived in the early 12h cohort definition window.";
  if (domain === "early_sepsis12") return "Early sepsis12 timing or severity feature available by landmark12.";
  if (domain === "comorbidity") return "Charlson comorbidity component derived from historical diagnosis codes.";
  return "Current v2 candidate predictor derived before landmark12.";
}

function featureUnit(name) {
  if (/^(hr|rr)_/.test(name) || name.includes("_slope_per_hour")) return "per source variable";
  if (/^(sbp|dbp|mbp|pulse_pressure)/.test(name)) return "mmHg";
  if (name.startsWith("temp_")) return "degC";
  if (name.startsWith("spo2_")) return "%";
  if (name.startsWith("lactate_")) return "mmol/L";
  if (name.startsWith("ph_")) return "pH unit";
  if (/bicarbonate|baseexcess|aniongap/.test(name)) return "mEq/L or mmol/L";
  if (/creatinine/.test(name)) return "mg/dL";
  if (/bun/.test(name)) return "mg/dL";
  if (/sodium|potassium|chloride/.test(name)) return "mEq/L or mmol/L";
  if (/wbc|platelet/.test(name)) return "K/uL";
  if (/hemoglobin/.test(name)) return "g/dL";
  if (/urineoutput/.test(name)) return "mL";
  if (/nee|norepinephrine|epinephrine|dopamine|phenylephrine|vasopressin|dobutamine|milrinone/.test(name)) return "mcg/kg/min or NEE";
  if (name.includes("record_prop") || name.endsWith("_flag")) return "0/1 or proportion";
  return "";
}

const coreRows = [
  row({ domain: "identity_time_anchor", required_for: "external_validation_current_model", variable_name: "source_patient_id", role: "ID", priority: "required_now", mimic_source_table: "mimiciv_hosp.patients.subject_id", mimic_definition: "Patient identifier, de-identified in the analytic dataset.", mimic_time_window: "whole database", hospital_source_system: "HIS/EMPI", hospital_definition: "院内患者唯一 ID，导出时可脱敏，但必须能联结住院、ICU、检验、用药和结局表。", extraction_difficulty: "low", expected_solution: "信息科生成不可逆脱敏 ID。", comments: "不要导出姓名、身份证号等直接身份信息。" }),
  row({ domain: "identity_time_anchor", required_for: "external_validation_current_model", variable_name: "source_encounter_id", role: "ID", priority: "required_now", mimic_source_table: "mimiciv_hosp.admissions.hadm_id", mimic_definition: "Hospital admission identifier.", mimic_time_window: "index hospitalization", hospital_source_system: "HIS/住院系统", hospital_definition: "住院流水号或就诊号。", extraction_difficulty: "low", expected_solution: "同一住院多次 ICU 时需能联结 ICU stay。" }),
  row({ domain: "identity_time_anchor", required_for: "external_validation_current_model", variable_name: "source_icu_stay_id", role: "ID", priority: "required_now", mimic_source_table: "mimiciv_icu.icustays.stay_id", mimic_definition: "ICU stay identifier.", mimic_time_window: "index ICU stay", hospital_source_system: "ICU/重症系统", hospital_definition: "ICU 入科记录唯一 ID；若无 stay_id，则由患者 ID + ICU 入出科时间生成。", extraction_difficulty: "medium", expected_solution: "按同一次 ICU 连续入科合并规则生成 stay_id。" }),
  row({ domain: "identity_time_anchor", required_for: "external_validation_current_model", variable_name: "icu_intime", role: "time_anchor", priority: "required_now", mimic_source_table: "mimiciv_icu.icustays.intime", mimic_definition: "ICU admission time.", mimic_time_window: "index ICU stay", hospital_source_system: "ICU/ADT", hospital_definition: "ICU 入科时间，精确到分钟或小时。", extraction_difficulty: "low", expected_solution: "作为所有 0-12h 特征和 12-60h 结局窗口的起点。" }),
  row({ domain: "identity_time_anchor", required_for: "external_validation_current_model", variable_name: "landmark12_time", role: "time_anchor", priority: "required_now", mimic_source_table: "derived from icu_intime", mimic_definition: "ICU intime + 12 hours.", mimic_time_window: "12h after ICU admission", hospital_source_system: "derived", hospital_definition: "landmark12_time = ICU 入科时间 + 12 小时。", extraction_difficulty: "low", expected_solution: "由分析脚本统一生成。" }),
  row({ domain: "cohort_definition", required_for: "cohort", variable_name: "adult_first_icu_flag", role: "inclusion", priority: "required_now", mimic_source_table: "study_ahf.cohort_010_adult_first_icu_v1", mimic_definition: "Adult first ICU stay.", mimic_time_window: "index ICU stay", hospital_source_system: "HIS/ICU", hospital_definition: "成人、首次 ICU 入科。", extraction_difficulty: "low", expected_solution: "年龄和 ICU stay 排序生成。" }),
  row({ domain: "cohort_definition", required_for: "cohort", variable_name: "strict_ahf_12h_flag", role: "inclusion", priority: "required_now", mimic_source_table: "study_ahf.cohort_061b_ahf_strict_12h_v1", mimic_definition: "HF diagnosis plus early evidence of acute decompensation by 12h.", mimic_time_window: "before landmark12", hospital_source_system: "HIS diagnosis + eMAR + LIS", hospital_definition: "心衰诊断基础上，结合急性心衰编码、早期 IV 袢利尿剂、BNP/NT-proBNP 等证据。", extraction_difficulty: "medium", expected_solution: "先取诊断编码和 IV 袢利尿剂；BNP/NT-proBNP 作为增强证据。" }),
  row({ domain: "cohort_definition", required_for: "cohort", variable_name: "early_sepsis12_main_flag", role: "inclusion", priority: "required_now", mimic_source_table: "study_ahf.cohort_061d_landmark12_riskset_main_v1; mimiciv_derived.sepsis3", mimic_definition: "Early sepsis evidence available by landmark12.", mimic_time_window: "before landmark12", hospital_source_system: "抗菌药/培养/检验/护理记录", hospital_definition: "疑似感染 + SOFA 升高或本地可复刻的 early sepsis12 定义。", extraction_difficulty: "high", expected_solution: "若没有现成 sepsis 表，导出抗菌药、培养时间和 SOFA 分组件重算。" }),
  row({ domain: "cohort_definition", required_for: "cohort", variable_name: "exclude_pre12_overt_cs_flag", role: "exclusion", priority: "required_now", mimic_source_table: "study_ahf.outcome_061c_pre12_overt_cs_flags_v1", mimic_definition: "Exclude overt shock-like patients before landmark12.", mimic_time_window: "ICU 0-12h", hospital_source_system: "ICU vital + lactate + vasoactive infusion", hospital_definition: "landmark 前已有明显低灌注/升压药/高乳酸等休克 proxy 者排除。", extraction_difficulty: "high", expected_solution: "保留原始 MAP/SBP、乳酸、升压药起止和剂量，按脚本统一生成。" }),
  row({ domain: "outcome_definition", required_for: "primary_outcome", variable_name: "primary_outcome_flag", role: "label", priority: "required_now", mimic_source_table: "study_ahf.outcome_064_primary_hd_deterioration_v1", mimic_definition: "12-60h hemodynamic deterioration: support escalation, NEE >=0.05 increase, or death.", mimic_time_window: "12-60h after ICU admission", hospital_source_system: "ICU infusion/eMAR + ADT death", hospital_definition: "12-60h 内发生血流动力学恶化主结局。", extraction_difficulty: "high", expected_solution: "逐 stay 计算事件时间和组件，先做 label-timing QC。" }),
  row({ domain: "outcome_definition", required_for: "primary_outcome_audit", variable_name: "first_support_escalation_time", role: "event_time", priority: "required_now", mimic_source_table: "study_ahf.audit_079_event_timing_components_v1", mimic_definition: "First new/increased vasoactive or inotrope support after landmark12.", mimic_time_window: "12-60h", hospital_source_system: "ICU infusion/eMAR", hospital_definition: "landmark 后首次新增升压/强心药或药物种类增加时间。", extraction_difficulty: "high", expected_solution: "从给药起止时间和药物类别计算。" }),
  row({ domain: "outcome_definition", required_for: "primary_outcome_audit", variable_name: "first_nee005_escalation_time", role: "event_time", priority: "required_now", mimic_source_table: "study_ahf.audit_079_event_timing_components_v1", mimic_definition: "First post12 NEE increase >=0.05 over pre12 max.", mimic_time_window: "12-60h", mimic_unit: "NEE", hospital_source_system: "ICU infusion/eMAR", hospital_definition: "post12 NEE - pre12 NEE max >=0.05 的首次时间。", extraction_difficulty: "high", expected_solution: "标准化单位后换算 NEE；保留短暂波动持续时间。" }),
  row({ domain: "outcome_definition", required_for: "primary_outcome_audit", variable_name: "death_time_12_60", role: "event_time", priority: "required_now", mimic_source_table: "mimiciv_hosp.admissions.deathtime", mimic_definition: "Death time between landmark12 and window60.", mimic_time_window: "12-60h", hospital_source_system: "ADT/病案首页/死亡登记", hospital_definition: "住院死亡时间，最好精确到小时。", extraction_difficulty: "medium", expected_solution: "若仅有日期，需标注时间精度并做敏感性分析。" }),
];

const futureRows = [
  row({ domain: "future_080B_lactate_acid_base", required_for: "future_incremental_model", variable_name: "lactate_clearance_pct_0_12h", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.bg", mimic_definition: "(first lactate - last lactate) / first lactate * 100 among 0-12h records; requires at least 2 lactate values.", mimic_time_window: "ICU 0-12h", mimic_unit: "%", hospital_source_system: "LIS/blood gas", hospital_definition: "乳酸清除率，至少 2 次乳酸。", extraction_difficulty: "medium", expected_solution: "导出乳酸值、样本类型和采样时间；统一 mmol/L。" }),
  row({ domain: "future_080B_lactate_acid_base", required_for: "future_incremental_model", variable_name: "lactate_persistent_ge2_flag", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.bg", mimic_definition: "Last or sustained lactate >=2 mmol/L before landmark12.", mimic_time_window: "ICU 0-12h", mimic_unit: "0/1", hospital_source_system: "LIS/blood gas", hospital_definition: "0-12h 末次或持续乳酸 >=2。", extraction_difficulty: "medium", expected_solution: "保留逐条乳酸而非只给最大值。" }),
  row({ domain: "future_080B_lactate_acid_base", required_for: "future_incremental_model", variable_name: "ph_slope_per_hour", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.bg", mimic_definition: "0-12h pH linear trend slope.", mimic_time_window: "ICU 0-12h", mimic_unit: "pH/hour", hospital_source_system: "LIS/blood gas", extraction_difficulty: "medium", expected_solution: "导出 pH 与 charttime，脚本统一计算趋势。" }),
  row({ domain: "future_080B_lactate_acid_base", required_for: "future_incremental_model", variable_name: "aniongap_slope_per_hour", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.chemistry", mimic_definition: "0-12h anion gap trend slope.", mimic_time_window: "ICU 0-12h", mimic_unit: "mEq/L/hour", hospital_source_system: "LIS/chemistry", extraction_difficulty: "low", expected_solution: "导出 anion gap 或 Na/Cl/HCO3 重算。" }),
  row({ domain: "future_080C_fluid_diuretic_response", required_for: "future_incremental_model", variable_name: "input_0_12h_total_ml", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_icu.inputevents", mimic_definition: "Total fluid input overlapping ICU 0-12h.", mimic_time_window: "ICU 0-12h", mimic_unit: "mL", hospital_source_system: "ICU intake/output", extraction_difficulty: "medium", expected_solution: "导出液体/药物输入起止时间和容量；按 overlap 分摊。" }),
  row({ domain: "future_080C_fluid_diuretic_response", required_for: "future_incremental_model", variable_name: "net_balance_0_12h_ml", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_icu.inputevents; mimiciv_icu.outputevents", mimic_definition: "Input minus output during ICU 0-12h.", mimic_time_window: "ICU 0-12h", mimic_unit: "mL", hospital_source_system: "ICU intake/output", extraction_difficulty: "medium", expected_solution: "如果只有班次汇总，按记录区间与 0-12h 重叠时间分摊。" }),
  row({ domain: "future_080C_fluid_diuretic_response", required_for: "future_incremental_model", variable_name: "iv_loop_furosemide_equivalent_0_12h_mg", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_hosp.emar; mimiciv_hosp.prescriptions; mimiciv_icu.inputevents", mimic_definition: "IV loop diuretic dose converted to furosemide-equivalent mg.", mimic_time_window: "ICU 0-12h", mimic_unit: "mg", hospital_source_system: "eMAR/medication administration", extraction_difficulty: "high", expected_solution: "抽取实际给药记录而不只医嘱；统一呋塞米/托拉塞米/布美他尼换算。" }),
  row({ domain: "future_080C_fluid_diuretic_response", required_for: "future_incremental_model", variable_name: "urine_ml_per_40mg_furosemide_equiv_0_12h", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.urine_output; medication tables", mimic_definition: "Urine output normalized by loop diuretic exposure.", mimic_time_window: "ICU 0-12h", mimic_unit: "mL/40mg", hospital_source_system: "ICU output + eMAR", extraction_difficulty: "high", expected_solution: "需要尿量与利尿剂真实给药均可按时间关联。" }),
  row({ domain: "future_080D_cardiac_markers", required_for: "future_incremental_model", variable_name: "ntprobnp_first_0_12h", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.cardiac_marker.ntprobnp", mimic_definition: "First NT-proBNP before landmark12.", mimic_time_window: "ICU 0-12h or early admission", mimic_unit: "pg/mL", hospital_source_system: "LIS", extraction_difficulty: "low", expected_solution: "同时导出 BNP 与 NT-proBNP；不要混合单位。" }),
  row({ domain: "future_080D_cardiac_markers", required_for: "future_incremental_model", variable_name: "troponin_t_max_0_12h", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_derived.cardiac_marker.troponin_t", mimic_definition: "Maximum troponin T before landmark12.", mimic_time_window: "ICU 0-12h", hospital_source_system: "LIS", extraction_difficulty: "low", expected_solution: "根据本院检验项目区分 hs-cTnT、cTnI、TnT，保留 assay 和单位。" }),
  row({ domain: "future_080D_cardiac_markers", required_for: "future_incremental_model", variable_name: "ck_mb_max_0_12h", role: "future_candidate_predictor", priority: "optional_next", mimic_source_table: "mimiciv_derived.cardiac_marker.ck_mb", mimic_definition: "Maximum CK-MB before landmark12.", mimic_time_window: "ICU 0-12h", hospital_source_system: "LIS", extraction_difficulty: "low", expected_solution: "导出 CK-MB 数值、单位和采样时间。" }),
  row({ domain: "future_080E_echo", required_for: "future_incremental_model", variable_name: "lvef_pre12_last", role: "future_candidate_predictor", priority: "high_value_next_phase", mimic_source_table: "MIMIC-IV-Note echo/radiology text if installed; current DB has no note schema", mimic_definition: "Last LVEF documented before landmark12; current local structured DB does not contain report text.", mimic_time_window: "before landmark12, preferably closest prior echo", mimic_unit: "%", hospital_source_system: "心超系统/PACS/报告文本", extraction_difficulty: "high", expected_solution: "院内优先导出结构化 LVEF 或报告全文 + 报告时间；MIMIC 需要安装 note/echo report source 才能文本抽取。" }),
  row({ domain: "future_080E_echo", required_for: "future_incremental_model", variable_name: "rv_dysfunction_pre12_flag", role: "future_candidate_predictor", priority: "high_value_next_phase", mimic_source_table: "MIMIC-IV-Note echo/radiology text if installed", mimic_definition: "RV dysfunction mentioned before landmark12.", mimic_time_window: "before landmark12", mimic_unit: "0/1", hospital_source_system: "心超报告文本", extraction_difficulty: "high", expected_solution: "用报告结构化字段优先；无结构化字段时做中文/英文关键词抽取并人工抽样验证。" }),
  row({ domain: "future_080E_echo", required_for: "future_incremental_model", variable_name: "echo_any_pre12_flag", role: "future_candidate_predictor_or_audit", priority: "optional_structured_now", mimic_source_table: "mimiciv_icu.procedureevents itemid 225432/221255", mimic_definition: "TTE/TEE procedure occurred before landmark12. This does not provide LVEF.", mimic_time_window: "ICU -24h to landmark12 or 0-12h", mimic_unit: "0/1", hospital_source_system: "超声预约/执行记录", extraction_difficulty: "low", expected_solution: "作为检查强度/可得性变量，不等同于心功能指标。" }),
  row({ domain: "future_infection_source", required_for: "future_incremental_model", variable_name: "infection_source_category", role: "future_candidate_predictor", priority: "strongly_recommended_next", mimic_source_table: "mimiciv_hosp.microbiologyevents; diagnosis/procedure; antibiotics", mimic_definition: "Pulmonary, urinary, abdominal, bloodstream, skin/soft tissue, catheter, unknown.", mimic_time_window: "before landmark12", hospital_source_system: "病历诊断/感染会诊/培养部位/抗菌药", extraction_difficulty: "high", expected_solution: "先用培养标本部位和诊断编码生成粗分类，再人工抽样验证。" }),
];

function currentFeatureRow(name, featureQcByName, selectedByName, top80Set) {
  const domain = inferDomain(name);
  const [mimicSource, hospitalSystem, difficulty, solution] = inferSource(domain);
  const qc = featureQcByName.get(name) ?? {};
  const selected = selectedByName.get(name) ?? {};
  const isTop80 = top80Set.has(name);
  const isLabel = name === "primary_outcome_flag" || name.startsWith("label_");
  const isId = ["subject_id", "hadm_id", "stay_id", "intime", "landmark12_time", "window60_time"].includes(name);
  return row({
    domain,
    required_for: isId ? "external_validation_current_model" : isLabel ? "outcome_qc_excluded_from_predictors" : isTop80 ? "current_top80_model_predictor" : "current_v2_candidate_or_qc",
    variable_name: name,
    role: isId ? "ID_or_time_anchor" : isLabel ? "label_or_label_component" : "predictor",
    priority: isId || isLabel ? "required_now" : isTop80 ? "required_for_current_top80_model" : qc.kept === "True" ? "recommended_for_retraining" : "optional_qc_or_excluded",
    mimic_source_table: mimicSource,
    mimic_definition: featureDefinition(name, domain),
    mimic_time_window: isId ? "index ICU stay" : isLabel ? "12-60h after ICU admission" : "ICU 0-12h unless noted",
    mimic_unit: featureUnit(name),
    hospital_source_system: hospitalSystem,
    hospital_definition: "请回填本院对应字段、计算规则、单位和时间字段。",
    extraction_difficulty: difficulty,
    expected_solution: solution,
    comments: isTop80 ? "当前 v2 top80 elastic-net 反复验证主模型特征之一。" : "",
    current_v2_missing_pct: qc.missing_pct ?? "",
    current_v2_kept: qc.kept ?? "",
    selection_frequency: selected.selection_frequency ?? "",
  });
}

function makeAuditRows(mappingRows) {
  return mappingRows.map((r) => ({
    domain: r.domain,
    variable_name: r.variable_name,
    priority: r.priority,
    hospital_source_system: r.hospital_source_system,
    hospital_field_name: "",
    mapping_status: "not_mapped",
    available_flag: "",
    n_total_nonmissing: "",
    missing_pct: "",
    unit_confirmed: "",
    time_window_confirmed: "",
    definition_match_level: "",
    extraction_difficulty: r.extraction_difficulty,
    blocker: "",
    proposed_resolution: r.expected_solution,
    reviewer_notes: "",
  }));
}

function sheetRows(headers, rows) {
  return [headers, ...rows.map((r) => headers.map((h) => r[h] ?? ""))];
}

async function addSheet(workbook, name, headers, rows) {
  const sheet = workbook.worksheets.add(name);
  const matrix = sheetRows(headers, rows);
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  range.values = matrix;
  try {
    sheet.freezePanes.freezeRows(1);
    sheet.showGridLines = false;
    const headerRange = sheet.getRangeByIndexes(0, 0, 1, headers.length);
    headerRange.format.fill.color = "#1F4E79";
    headerRange.format.font.color = "#FFFFFF";
    headerRange.format.font.bold = true;
    range.format.wrapText = true;
    sheet.getUsedRange().format.autofitColumns();
  } catch {
    // Formatting is helpful but not required for the workbook contents.
  }
  return sheet;
}

async function main() {
  await fs.mkdir(DOCS, { recursive: true });
  await fs.mkdir(RAW, { recursive: true });

  const datasetColumns = await readHeaderOnly("data/raw/model_080G_modeling_dataset_v2.csv");
  const featureQc = await readCsv("outputs_v2/qc/071_feature_qc.csv");
  const selectedFinal = await readCsv("outputs_v2/tables/072C_selected_features_final.csv");
  const featureSets = await readCsv("outputs_v2/tables/072D_feature_sets_long.csv");

  const featureQcByName = new Map(featureQc.map((r) => [r.column, r]));
  const selectedByName = new Map(selectedFinal.map((r) => [r.selected_feature, r]));
  const top80Features = featureSets
    .filter((r) => r.feature_set === "top80_compact")
    .sort((a, b) => Number(a.rank_in_feature_set) - Number(b.rank_in_feature_set))
    .map((r) => r.feature);
  const top80Set = new Set(top80Features);

  const top80Rows = top80Features.map((name) => currentFeatureRow(name, featureQcByName, selectedByName, top80Set));
  const allV2Rows = datasetColumns.map((name) => currentFeatureRow(name, featureQcByName, selectedByName, top80Set));
  const mainMappingRows = [...coreRows, ...top80Rows, ...futureRows];
  const auditRows = makeAuditRows(mainMappingRows);

  const echoStatusRows = [
    {
      item: "Current local MIMIC DB note schema",
      status: "not_available",
      evidence: "information_schema contains mimiciv_hosp, mimiciv_icu, mimiciv_derived, study_ahf; no mimiciv_note/radiology/discharge/echo report table found.",
      implication: "Cannot extract report-text LVEF/RV dysfunction from the current local DB.",
      action: "If MIMIC-IV-Note is installed later, add text extraction SQL/Python and manual validation sample.",
    },
    {
      item: "Structured TTE procedure flag",
      status: "available_low_content",
      evidence: "mimiciv_icu.procedureevents itemid 225432 captured 216 stays from ICU -24h to landmark12 in current cohort audit.",
      implication: "Can indicate echo performed, but not cardiac function result.",
      action: "Use only as audit/availability feature unless clinically justified.",
    },
    {
      item: "Structured TEE procedure flag",
      status: "available_low_content",
      evidence: "mimiciv_icu.procedureevents itemid 221255 captured 13 stays from ICU -24h to landmark12 in current cohort audit.",
      implication: "Can indicate TEE performed, but not LVEF/RV function.",
      action: "Use as procedure/availability feature only.",
    },
    {
      item: "Structured APACHE ejection fraction",
      status: "not_observed_in_current_db",
      evidence: "mimiciv_icu.d_items has itemid 227008 Ejection Fraction, but chartevents audit returned 0 rows in current DB.",
      implication: "Not usable as a MIMIC structured LVEF predictor here.",
      action: "Prioritize院内结构化心超字段 or report text extraction.",
    },
    {
      item: "Cardiac output / cardiac index",
      status: "sparse_available",
      evidence: "0-12h chartevents audit found cardiac output in about 42-43 stays and cardiac index in about 20 stays.",
      implication: "Too sparse for main model; can be kept in QC/future exploratory features.",
      action: "Extract in 081A table, review missingness before modeling.",
    },
  ];

  const mappingHeaders = [
    "domain",
    "required_for",
    "variable_name",
    "role",
    "priority",
    "mimic_source_table",
    "mimic_definition",
    "mimic_time_window",
    "mimic_unit",
    "hospital_source_system",
    "hospital_field_name",
    "hospital_definition",
    "hospital_unit",
    "hospital_time_field",
    "mapping_status",
    "extraction_difficulty",
    "expected_solution",
    "comments",
    "current_v2_missing_pct",
    "current_v2_kept",
    "selection_frequency",
  ];
  const auditHeaders = [
    "domain",
    "variable_name",
    "priority",
    "hospital_source_system",
    "hospital_field_name",
    "mapping_status",
    "available_flag",
    "n_total_nonmissing",
    "missing_pct",
    "unit_confirmed",
    "time_window_confirmed",
    "definition_match_level",
    "extraction_difficulty",
    "blocker",
    "proposed_resolution",
    "reviewer_notes",
  ];
  const echoHeaders = ["item", "status", "evidence", "implication", "action"];
  const readmeRows = [
    { section: "Purpose", note: "院内外部验证变量映射清单，用于将本院数据逐项映射到当前 MIMIC v2 模型和后续增量特征。" },
    { section: "Current model", note: "当前主模型建议以 v2 top80 elastic-net platt 为外部验证起点；需要身份/时间锚点、主结局和 top80 predictors。" },
    { section: "Feasibility audit", note: "本院回填 hospital_field_name、mapping_status、unit/time/definition 等字段后，发回给我做可提取性审计。" },
    { section: "Echo note", note: "当前本机 MIMIC DB 无 note/echo 报告文本；结构化库只能提 TTE/TEE 检查标志、稀疏心输出量/心指数，不能可靠提 LVEF/RV dysfunction。" },
    { section: "Generated at", note: GENERATED_AT },
  ];

  await fs.writeFile(path.join(DOCS, "external_validation_variable_mapping_v2.csv"), toCsv(mainMappingRows, mappingHeaders), "utf8");
  await fs.writeFile(path.join(DOCS, "external_validation_current_top80_features_v2.csv"), toCsv(top80Rows, mappingHeaders), "utf8");
  await fs.writeFile(path.join(DOCS, "external_validation_all_v2_dataset_columns_mapping.csv"), toCsv(allV2Rows, mappingHeaders), "utf8");
  await fs.writeFile(path.join(DOCS, "external_validation_feasibility_audit_template_v2.csv"), toCsv(auditRows, auditHeaders), "utf8");
  await fs.writeFile(path.join(DOCS, "mimic_echo_lvef_availability_note_v2.csv"), toCsv(echoStatusRows, echoHeaders), "utf8");

  const returnTemplateHeaders = [
    "source_patient_id",
    "source_encounter_id",
    "source_icu_stay_id",
    "icu_intime",
    "icu_outtime",
    "landmark12_time",
    "window60_time",
    "primary_outcome_flag",
    "first_support_escalation_time",
    "first_nee005_escalation_time",
    "first_nee010_escalation_time",
    "death_time_12_60",
    ...top80Features,
    "lactate_clearance_pct_0_12h",
    "net_balance_0_12h_ml",
    "iv_loop_furosemide_equivalent_0_12h_mg",
    "ntprobnp_first_0_12h",
    "troponin_t_max_0_12h",
    "lvef_pre12_last",
    "rv_dysfunction_pre12_flag",
    "infection_source_category",
  ];
  await fs.writeFile(path.join(RAW, "hospital_external_validation_data_template_v2.csv"), returnTemplateHeaders.map(csvEscape).join(",") + "\n", "utf8");

  const notes = `# 院内外部验证变量映射说明 v2

生成日期：${GENERATED_AT}

## 推荐执行顺序

1. 先用当前 v2 top80 特征清单做院内字段映射，判断能否外部验证现有 MIMIC 模型。
2. 同步在 MIMIC 和院内推进结构化高价值特征：乳酸/酸碱趋势、容量与利尿反应、心肌损伤/心衰标志物。
3. 心超/LVEF 单独作为下一阶段重点：院内如果能拿到结构化心超系统字段或报告文本，将比当前本机 MIMIC 结构化库更有价值。

## 什么叫“本院字段提不出来或定义不同”

- 时间粒度不同：MIMIC 有逐条 charttime/starttime/endtime，本院可能只有班次汇总或日期。
- 单位不同：BNP/NT-proBNP、troponin、升压药剂量可能单位或 assay 不一致。
- 记录语义不同：医嘱不等于实际执行，输液泵记录不等于药房开立记录。
- 结局定义难复刻：NEE 升级需要药名、剂量、体重、起止时间；缺任一项都会影响标签。
- 文本/结构化差异：心超报告若只有 PDF/自由文本，需要抽取和人工验证；若有结构化 LVEF 字段则最好。

## 返还给我的材料

- 填好的 external_validation_variable_mapping_v2.xlsx 或 CSV。
- 院内字段样例字典：字段名、单位、时间字段、取值范围、缺失编码。
- 抽样 20-50 例脱敏长表数据，用于检查时间窗、单位和 join 逻辑。
`;
  await fs.writeFile(path.join(DOCS, "external_validation_mapping_notes_v2.md"), notes, "utf8");

  const workbook = Workbook.create();
  await addSheet(workbook, "00_Readme", ["section", "note"], readmeRows);
  await addSheet(workbook, "01_MainMapping", mappingHeaders, mainMappingRows);
  await addSheet(workbook, "02_CurrentTop80", mappingHeaders, top80Rows);
  await addSheet(workbook, "03_AllV2Columns", mappingHeaders, allV2Rows);
  await addSheet(workbook, "04_FutureFeatures", mappingHeaders, futureRows);
  await addSheet(workbook, "05_AuditReturn", auditHeaders, auditRows);
  await addSheet(workbook, "06_EchoStatus", echoHeaders, echoStatusRows);

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(path.join(DOCS, "external_validation_variable_mapping_v2.xlsx"));

  try {
    const preview = await workbook.render({ sheetName: "01_MainMapping", autoCrop: "all", scale: 1, format: "png" });
    const previewBytes = new Uint8Array(await preview.arrayBuffer());
    await fs.writeFile(path.join(DOCS, "external_validation_variable_mapping_v2_preview.png"), previewBytes);
  } catch (err) {
    await fs.writeFile(path.join(DOCS, "external_validation_variable_mapping_v2_render_warning.txt"), String(err), "utf8");
  }

  console.log(`Wrote mapping workbook and templates to ${DOCS}`);
  console.log(`Top80 feature count: ${top80Features.length}`);
  console.log(`Main mapping rows: ${mainMappingRows.length}`);
  console.log(`All v2 column rows: ${allV2Rows.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
