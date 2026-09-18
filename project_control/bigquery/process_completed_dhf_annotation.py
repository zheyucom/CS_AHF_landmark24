#!/usr/bin/env python3
"""Import the completed annotation workbook and produce auditable QC outputs.

The workbook is treated as the completed first annotation.  The requested
second annotation is copied from the first annotation and is explicitly
reported as a same-reviewer repeat, not independent inter-rater validation.
"""

from __future__ import annotations

import csv
import argparse
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "project_control/bigquery"
ANNOTATION_DIR = BASE / "controlled_annotation_20260830_v2"
WORKBOOK = ANNOTATION_DIR / "工作簿1_标注完成版.xlsx"
RAW_SAMPLE = BASE / "dhf_radiology_annotation_sample300_v2.csv"
RAW_ALL = BASE / "dhf_radiology_raw_v2.csv"
PATIENT_SUMMARY = BASE / "dhf_radiology_patient_summary_v2.csv"
OUTCOME = ROOT / "project_control/runs/20260827_v3_2_outcome_label_audit/data/096_strict_main_label_v33.csv"
OUTPUT_DIR = ANNOTATION_DIR / "processed_20260902"
REPORT_DATE = "2026-09-03"

ORIGINAL_COLUMNS = [
    "annotation_id", "stay_id", "note_id", "charttime", "storetime", "report_text",
    "rule_positive_congestion", "rule_uncertainty", "rule_negation", "reviewer_id",
    "congestion_label", "alternative_explanation_label", "report_available_pre_t0_label",
    "comments", "adjudication_label",
]
CONGESTION = {"definite_congestion", "possible_congestion", "no_congestion", "indeterminate"}
ALTERNATIVES = {"none_apparent", "pneumonia_ards", "pulmonary_embolism_or_rv_strain",
                "postoperative_or_technical", "other", "unclear"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def excel_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return str(value).strip()


def load_completed_workbook(path: Path) -> list[dict[str, str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows = list(sheet.values)
    headers = [excel_value(value) for value in rows[0]]
    while headers and not headers[-1]:
        headers.pop()
    required = {
        "annotation_id", "stay_id", "note_id", "charttime", "storetime", "report_text",
        "rule_positive_congestion", "rule_uncertainty", "rule_negation", "final_congestion_label",
        "final_alternative_explanation_label", "final_comments",
    }
    missing = sorted(required - set(headers))
    if missing:
        raise ValueError(f"Workbook missing required columns: {missing}")
    result = []
    for raw_row in rows[1:]:
        values = list(raw_row[: len(headers)])
        row = {headers[index]: excel_value(values[index] if index < len(values) else None)
               for index in range(len(headers))}
        if row.get("annotation_id"):
            result.append(row)
    return result


def stratum(row: dict[str, str]) -> str:
    if row["rule_positive_congestion"] == "1" and row["rule_uncertainty"] == "0":
        return "definite_positive_rule_screen"
    if row["rule_uncertainty"] == "1" or row["rule_negation"] == "1":
        return "negated_or_uncertain_screen"
    return "no_hit_screen"


def wilson(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return (float("nan"), float("nan"))
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return centre - half, centre + half


def pct(value: float) -> str:
    return "NA" if math.isnan(value) else f"{value * 100:.1f}%"


def metric_row(name: str, value: float, denominator: str, note: str = "") -> dict[str, str]:
    return {"metric": name, "estimate": pct(value), "denominator": denominator, "note": note}


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ANNOTATION_DIR / "processed_20260903",
        help="New output directory; must not already exist.",
    )
    args = parser.parse_args()

    first = load_completed_workbook(WORKBOOK)
    raw_sample = read_csv(RAW_SAMPLE)
    raw_all = read_csv(RAW_ALL)
    summary = {row["stay_id"]: row for row in read_csv(PATIENT_SUMMARY)}
    outcome = {row["stay_id"]: row for row in read_csv(OUTCOME)}
    raw_by_key = {(row["stay_id"], row["note_id"]): row for row in raw_sample}

    errors: list[str] = []
    if len(first) != 300:
        errors.append(f"workbook row count is {len(first)}, expected 300")
    if len({row["annotation_id"] for row in first}) != len(first):
        errors.append("duplicate annotation_id in workbook")
    if len({(row["stay_id"], row["note_id"]) for row in first}) != len(first):
        errors.append("duplicate stay_id/note_id in workbook")

    completed: list[dict[str, str]] = []
    for row in first:
        key = (row["stay_id"], row["note_id"])
        raw = raw_by_key.get(key)
        if raw is None:
            errors.append(f"workbook row not found in raw sample: {key}")
            continue
        congestion = row["final_congestion_label"]
        alternative = row["final_alternative_explanation_label"]
        if congestion not in CONGESTION:
            errors.append(f"{row['annotation_id']}: invalid congestion label {congestion!r}")
        if alternative not in ALTERNATIVES:
            errors.append(f"{row['annotation_id']}: invalid alternative label {alternative!r}")
        availability = "yes" if raw["report_available_pre_t0_flag"] == "1" else "no"
        completed.append({
            "annotation_id": row["annotation_id"],
            "stay_id": row["stay_id"],
            "note_id": row["note_id"],
            "charttime": row["charttime"],
            "storetime": row["storetime"],
            "report_text": row["report_text"],
            "rule_positive_congestion": row["rule_positive_congestion"],
            "rule_uncertainty": row["rule_uncertainty"],
            "rule_negation": row["rule_negation"],
            "reviewer_id": row.get("reviewer_id") or "human_1",
            "congestion_label": congestion,
            "alternative_explanation_label": alternative,
            "report_available_pre_t0_label": availability,
            "comments": row.get("final_comments", ""),
            "adjudication_label": row.get("adjudication_label", ""),
        })
    if errors:
        raise SystemExit("Validation failed:\n" + "\n".join(errors[:30]))

    output_dir = args.output_dir
    output_dir.mkdir(exist_ok=False)
    write_csv(output_dir / "dhf_radiology_annotation_round1_completed.csv", completed, ORIGINAL_COLUMNS)

    completed_by_key = {(row["stay_id"], row["note_id"]): row for row in completed}
    original_round2 = read_csv(ANNOTATION_DIR / "dhf_radiology_annotation_round2_blinded.csv")
    repeat = []
    for row in original_round2:
        source = completed_by_key.get((row["stay_id"], row["note_id"]))
        if source is None:
            raise SystemExit(f"Round-2 key not found in completed workbook: {row['annotation_id']}")
        copied = dict(source)
        copied["annotation_id"] = row["annotation_id"]
        copied["reviewer_id"] = "human_1_repeat_same_as_round1"
        copied["comments"] = "Copied from first annotation per user instruction; same-reviewer repeat, not independent review."
        repeat.append(copied)
    if len(repeat) != 60:
        raise SystemExit(f"Expected 60 round-2 records, got {len(repeat)}")
    write_csv(output_dir / "dhf_radiology_annotation_round2_same_reviewer.csv", repeat, ORIGINAL_COLUMNS)

    full_counts = Counter(stratum({
        "rule_positive_congestion": row["positive_congestion_evidence_flag"],
        "rule_uncertainty": row["uncertainty_hit"],
        "rule_negation": str(int(row["pulmonary_edema_negation_hit"] == "1" or row["vascular_congestion_negation_hit"] == "1")),
    }) for row in raw_all)
    sample_counts = Counter(stratum(row) for row in completed)
    labels_by_stratum = defaultdict(Counter)
    for row in completed:
        labels_by_stratum[stratum(row)][row["congestion_label"]] += 1

    positive_stratum = [row for row in completed if stratum(row) == "definite_positive_rule_screen"]
    definite_positive = sum(row["congestion_label"] == "definite_congestion" for row in positive_stratum)
    definite_or_possible = sum(row["congestion_label"] in {"definite_congestion", "possible_congestion"} for row in positive_stratum)
    lo, hi = wilson(definite_positive, len(positive_stratum))

    # Stratified-sample estimate for a binary reference of definite congestion.
    weighted = Counter()
    for key, rows in labels_by_stratum.items():
        weight = full_counts[key] / sample_counts[key]
        algorithm_positive = key == "definite_positive_rule_screen"
        for label, count in rows.items():
            reference_positive = label == "definite_congestion"
            cell = ("tp" if algorithm_positive and reference_positive else
                    "fp" if algorithm_positive else
                    "fn" if reference_positive else "tn")
            weighted[cell] += count * weight
    sensitivity = weighted["tp"] / (weighted["tp"] + weighted["fn"])
    specificity = weighted["tn"] / (weighted["tn"] + weighted["fp"])
    ppv = weighted["tp"] / (weighted["tp"] + weighted["fp"])
    npv = weighted["tn"] / (weighted["tn"] + weighted["fn"])

    # Same-reviewer repeat agreement is mathematically perfect by construction.
    aligned_source = [completed_by_key[(r["stay_id"], r["note_id"])] for r in original_round2]
    repeat_agreement = sum(copied["congestion_label"] == source["congestion_label"]
                           for copied, source in zip(repeat, aligned_source, strict=True)) / len(repeat)
    kappa = 1.0 if repeat_agreement == 1 else float("nan")
    metrics = [
        metric_row("positive_screen_definite_congestion_confirmation", definite_positive / len(positive_stratum), "78/100 sampled positive-stratum reports", "Report-level PPV proxy; stratified sample."),
        metric_row("positive_screen_definite_or_possible_confirmation", definite_or_possible / len(positive_stratum), "84/100 sampled positive-stratum reports", "Possible is not definite DHF evidence."),
        metric_row("positive_screen_definite_confirmation_wilson95_low", lo, "100 sampled positive-stratum reports"),
        metric_row("positive_screen_definite_confirmation_wilson95_high", hi, "100 sampled positive-stratum reports"),
        metric_row("weighted_report_level_sensitivity", sensitivity, "stratum-weighted 300-report validation sample", "Reference = definite_congestion; not a patient-level sensitivity estimate."),
        metric_row("weighted_report_level_specificity", specificity, "stratum-weighted 300-report validation sample", "Reference = definite_congestion; not a patient-level specificity estimate."),
        metric_row("weighted_report_level_ppv", ppv, "stratum-weighted 300-report validation sample", "Reference = definite_congestion."),
        metric_row("weighted_report_level_npv", npv, "stratum-weighted 300-report validation sample", "Reference = definite_congestion."),
        metric_row("same_reviewer_repeat_agreement", repeat_agreement, "60 copied repeat records", "Not independent inter-rater agreement."),
        metric_row("same_reviewer_repeat_kappa", kappa, "60 copied repeat records", "Kappa=1 by construction; do not report as independent inter-rater reliability."),
    ]
    write_csv(output_dir / "dhf_annotation_validation_metrics.csv", metrics, ["metric", "estimate", "denominator", "note"])

    # Patient-level labels are validation-sample labels only, not a full-cohort label.
    patient_rows = []
    by_stay = defaultdict(list)
    for row in completed:
        by_stay[row["stay_id"]].append(row)
    for stay_id, reports in sorted(by_stay.items()):
        patient = summary.get(stay_id, {})
        definite_any = any(r["congestion_label"] == "definite_congestion" for r in reports)
        definite_available = any(r["congestion_label"] == "definite_congestion" and r["report_available_pre_t0_label"] == "yes" for r in reports)
        support = patient.get("pre_t0_iv_loop_emar_flag") == "1" or patient.get("pre_t0_ntprobnp_ge300_flag") == "1"
        final = outcome.get(stay_id, {})
        patient_rows.append({
            "stay_id": stay_id,
            "n_annotated_reports": str(len(reports)),
            "radiology_definite_any_charttime": str(int(definite_any)),
            "radiology_definite_available_pre_t0": str(int(definite_available)),
            "pre_t0_loop_or_ntprobnp_support": str(int(support)),
            "multidomain_dhf_validation_sample_flag": str(int(definite_available and support)),
            "final_state": final.get("final_state", ""),
            "event_type": final.get("event_type", ""),
        })
    write_csv(output_dir / "dhf_annotation_patient_level_validation_sample.csv", patient_rows, list(patient_rows[0]))

    patient_counts = Counter({
        "annotated_stays": len(patient_rows),
        "radiology_definite_any_charttime": sum(r["radiology_definite_any_charttime"] == "1" for r in patient_rows),
        "radiology_definite_available_pre_t0": sum(r["radiology_definite_available_pre_t0"] == "1" for r in patient_rows),
        "multidomain_dhf_validation_sample": sum(r["multidomain_dhf_validation_sample_flag"] == "1" for r in patient_rows),
        "events_in_annotated_stays": sum(r["final_state"] == "event" for r in patient_rows),
        "competing_events_in_annotated_stays": sum(r["final_state"] == "compete" for r in patient_rows),
        "censoring_in_annotated_stays": sum(r["final_state"] == "censor" for r in patient_rows),
    })

    report = output_dir / f"DHF_ANNOTATION_VALIDATION_REPORT_{REPORT_DATE}.md"
    with report.open("w", encoding="utf-8") as handle:
        handle.write("# DHF 300 条影像标注验证报告\n\n")
        handle.write(f"日期：{REPORT_DATE}\n\n")
        handle.write("## 结论\n\n")
        handle.write("Excel 第一张表作为第一位标注者的完成结果导入并通过 ID/标签 QC。第二位标注者按用户指示复制第一位结果，因此重复一致率和 kappa 为构造性结果，不能作为独立双盲 inter-rater reliability；正式论文应将该验证降级说明，不能声称完成独立双标注。\n\n")
        handle.write("## 报告级结果\n\n")
        handle.write("| 筛查层 | 全部报告数 | 抽样数 | definite | possible | no | indeterminate |\n|---|---:|---:|---:|---:|---:|---:|\n")
        for key in ["definite_positive_rule_screen", "negated_or_uncertain_screen", "no_hit_screen"]:
            c = labels_by_stratum[key]
            handle.write(f"| {key} | {full_counts[key]} | {sample_counts[key]} | {c['definite_congestion']} | {c['possible_congestion']} | {c['no_congestion']} | {c['indeterminate']} |\n")
        handle.write("\n阳性规则层中明确充血比例为 **78/100 = 78.0%**（Wilson 95% CI：")
        handle.write(f"{pct(lo)}–{pct(hi)}）；若将 possible 合并为非确定性支持，则为 84/100 = 84.0%。这些是报告级、分层抽样估计，不是 DHF 确诊率。\n\n")
        handle.write(f"按完整报告层规模加权、以 `definite_congestion` 为参考，报告级敏感度约 **{pct(sensitivity)}**、特异度约 **{pct(specificity)}**、PPV **{pct(ppv)}**、NPV **{pct(npv)}**。由于标注样本是报告级分层抽样，且同一患者可有多份报告，这些数字不能替代患者级表型验证。\n\n")
        handle.write("## 患者级验证样本\n\n")
        missing_comments = sum(not row.get("comments", "").strip() for row in completed)
        handle.write(f"300 条报告涉及 {patient_counts['annotated_stays']} 个 stay。至少一份明确充血报告（按 charttime）为 {patient_counts['radiology_definite_any_charttime']} 个；按 `storetime < intime` 的可见性要求为 {patient_counts['radiology_definite_available_pre_t0']} 个；同时满足影像明确充血和 pre-T0 loop/NT-proBNP 支持的 multidomain 验证样本为 {patient_counts['multidomain_dhf_validation_sample']} 个。该结果仅适用于 300 条验证报告涉及的患者，不能外推为 5,549 个候选 stay 的完整队列。\n\n")
        handle.write(f"工作簿中 `final_comments` 缺失 {missing_comments}/300 条；不对缺失备注补写临床判断，保留为空并在 QC 中记录。\n\n")
        handle.write(f"这些 stay 中已有结局标签审计：event {patient_counts['events_in_annotated_stays']}、alive ICU discharge compete {patient_counts['competing_events_in_annotated_stays']}、censor {patient_counts['censoring_in_annotated_stays']}；仅作验证样本描述，不用于冻结主模型。\n\n")
        handle.write("## 文件\n\n")
        handle.write("- `dhf_radiology_annotation_round1_completed.csv`：Excel 第一张表规范化结果。\n")
        handle.write("- `dhf_radiology_annotation_round2_same_reviewer.csv`：按用户要求复制的 60 条重复复核。\n")
        handle.write("- `dhf_annotation_validation_metrics.csv`：报告级性能和一致性指标。\n")
        handle.write("- `dhf_annotation_patient_level_validation_sample.csv`：验证样本患者级分层与结局审计。\n\n")
        handle.write("## 下一步\n\n")
        handle.write("1. 不把同一标注者复制结果写成独立 inter-rater kappa。\n2. 如需正式方法学验证，补充一位真正独立的临床标注者对 60 条报告的盲法复核；否则把影像域定位为人工复核的单标注验证/weak-label sensitivity。\n3. 在导师确认证据层级后，必须从完整 5,549 个候选重新构建患者级 radiology-supported/multidomain DHF 表型，不能仅用这 300 条抽样报告构建最终主队列。\n")

    print(f"Wrote processed annotation outputs to {output_dir}")


if __name__ == "__main__":
    main()
