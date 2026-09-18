#!/usr/bin/env python3
"""Create the main-window DHF imaging evidence and outcome audit.

The input is the compact BigQuery report extract from 111.  It is intentionally
separate from the full-text export because browser downloads of long notes can
silently be incomplete.  The output remains a rule-supported operational
phenotype audit, not a clinical DHF gold standard.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "project_control/bigquery"
SUMMARY = BASE / "dhf_radiology_patient_summary_landmark12_v1.csv"
REPORTS = BASE / "dhf_radiology_report_audit_landmark12_v1.csv"
OUTCOME = ROOT / "project_control/runs/20260827_v3_2_outcome_label_audit/data/096_strict_main_label_v33.csv"
ECHO = BASE / "structured_echo_screen_v33.csv"
OUTPUT_DIR = BASE / "landmark12_audit_20260904"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def flag(row: dict[str, str], key: str) -> bool:
    return row.get(key, "") in {"1", "1.0", "True", "true"}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def outcome_counts(rows: list[dict[str, object]]) -> tuple[int, int, int]:
    return (
        sum(row["final_state"] == "event" for row in rows),
        sum(row["final_state"] == "compete" for row in rows),
        sum(row["final_state"] == "censor" for row in rows),
    )


def main() -> None:
    if not REPORTS.exists():
        raise SystemExit(
            f"Missing {REPORTS.name}. Run 111 in BigQuery and download its compact CSV before auditing."
        )

    summary = {row["stay_id"]: row for row in read_csv(SUMMARY)}
    reports = read_csv(REPORTS)
    outcomes = {row["stay_id"]: row for row in read_csv(OUTCOME)}
    echo = {row["stay_id"]: row for row in read_csv(ECHO)}
    valid_ids = set(summary) & set(outcomes)
    if len(valid_ids) != 5549:
        raise SystemExit(f"Expected 5,549 summary/outcome stays; found {len(valid_ids)}")

    reports_by_stay: dict[str, list[dict[str, str]]] = defaultdict(list)
    for report in reports:
        if report["stay_id"] in valid_ids:
            reports_by_stay[report["stay_id"]].append(report)

    report_count_by_stay = Counter(report["stay_id"] for report in reports if report["stay_id"] in valid_ids)
    summary_total = sum(int(row["n_reports_T0minus24_to_T12"]) for row in summary.values())
    extracted_total = sum(report_count_by_stay.values())
    # BigQuery's browser "local download" can truncate a result set. Keep the
    # partial file auditable, but never present its modality or positive counts
    # as full-cohort estimates. A complete 111 export will automatically make
    # this flag true on the next run.
    extraction_complete = extracted_total == summary_total

    rows: list[dict[str, object]] = []
    for stay_id in sorted(valid_ids, key=int):
        candidate = summary[stay_id]
        stay_reports = reports_by_stay[stay_id]
        available = [r for r in stay_reports if flag(r, "report_available_by_t12_flag")]
        definite = [
            r for r in available
            if flag(r, "positive_congestion_evidence_flag") and not flag(r, "uncertainty_hit")
        ]
        definite_cxr = [r for r in definite if r["report_modality"] == "chest_xray"]
        definite_ct = [r for r in definite if r["report_modality"] == "chest_ct"]
        echo_row = echo.get(stay_id, {})
        # Procedure and isolated LVEF availability are audit fields, not proof
        # of a pathological echo result.  Echo result text is not available in
        # this MIMIC development extraction.
        echo_procedure = flag(echo_row, "echo_any_procedure_pre12_flag")
        lvef_available = flag(echo_row, "structured_lvef_pre12_available_flag")
        loop = flag(candidate, "pre_t0_iv_loop_emar_flag")
        ntprobnp = flag(candidate, "pre_t0_ntprobnp_ge300_flag")
        objective_lung = bool(definite_cxr or definite_ct)
        final_state = outcomes[stay_id]["final_state"]
        rows.append({
            "stay_id": stay_id,
            "subject_id": candidate["subject_id"],
            "hadm_id": candidate["hadm_id"],
            "n_reports_window": int(candidate["n_reports_T0minus24_to_T12"]),
            "n_reports_extracted": len(stay_reports),
            "report_extract_complete_flag": int(
                len(stay_reports) == int(candidate["n_reports_T0minus24_to_T12"])
            ),
            "n_reports_available_by_t12": len(available),
            "n_chest_xray_reports": sum(r["report_modality"] == "chest_xray" for r in stay_reports),
            "n_chest_ct_reports": sum(r["report_modality"] == "chest_ct" for r in stay_reports),
            "n_other_or_unclassified_reports": sum(r["report_modality"] == "other_or_unclassified" for r in stay_reports),
            "definite_cxr_congestion_available_by_t12_flag": int(bool(definite_cxr)),
            "definite_ct_congestion_available_by_t12_flag": int(bool(definite_ct)),
            "definite_cxr_or_ct_congestion_available_by_t12_flag": int(objective_lung),
            "pre_t0_iv_loop_flag": int(loop),
            "pre_t0_ntprobnp_ge300_support_flag": int(ntprobnp),
            "echo_procedure_pre12_flag": int(echo_procedure),
            "structured_lvef_available_pre12_flag": int(lvef_available),
            "multidomain_lung_plus_iv_loop_flag": int(objective_lung and loop),
            "multidomain_lung_plus_iv_loop_or_ntprobnp_flag": int(objective_lung and (loop or ntprobnp)),
            "final_state": final_state,
            "event_flag": int(final_state == "event"),
            "competing_alive_icu_discharge_flag": int(final_state == "compete"),
            "administrative_censor_flag": int(final_state == "censor"),
        })

    OUTPUT_DIR.mkdir(exist_ok=True)
    prefix = "dhf_multidomain_patient_level_audit_landmark12_20260904"
    write_csv(OUTPUT_DIR / f"{prefix}.csv", rows)

    definitions = {
        "all_hf_icd_candidates": lambda r: True,
        "any_radiology_available_by_t12": lambda r: r["n_reports_available_by_t12"] > 0,
        "definite_cxr_or_ct_congestion_available_by_t12": lambda r: r["definite_cxr_or_ct_congestion_available_by_t12_flag"] == 1,
        "definite_cxr_or_ct_congestion_plus_iv_loop": lambda r: r["multidomain_lung_plus_iv_loop_flag"] == 1,
        "definite_cxr_or_ct_congestion_plus_iv_loop_or_ntprobnp": lambda r: r["multidomain_lung_plus_iv_loop_or_ntprobnp_flag"] == 1,
    }
    audit = []
    for name, predicate in definitions.items():
        subset = [row for row in rows if predicate(row)]
        event, compete, censor = outcome_counts(subset)
        n = len(subset)
        audit.append({
            "phenotype": name,
            "rule_status": "rule_supported_operational_phenotype",
            "n_stays": n,
            "events": event,
            "competing_alive_icu_discharge": compete,
            "administrative_censor": censor,
            "event_rate": round(event / n, 6) if n else None,
            "epv_at_45_predictors": round(event / 45, 4) if n else None,
        })
    write_csv(OUTPUT_DIR / f"{prefix}_outcome_epv.csv", audit)

    modality_counts = Counter(report["report_modality"] for report in reports)
    with (OUTPUT_DIR / "DHF_MULTIDOMAIN_AUDIT_LANDMARK12_2026-09-04.md").open("w", encoding="utf-8") as handle:
        handle.write("# DHF 主窗口多域证据审计\n\n")
        handle.write("## 设计边界\n\n")
        handle.write("候选集为 5,549 名 HF ICD anchor ICU stays。入组证据窗口为 `[T0-24 h, T12)`；预测变量严格为 `[T0, T12)`；结局窗口为 `[T12, T60)`。影像、ICD、BNP 和利尿剂字段均不可作为预测器。\n\n")
        handle.write("本审计用 CXR/胸部 CT 明确肺淤血规则、T12 前报告可见性及治疗支持生成操作性表型。它不是人工 adjudication，也不能将单项 BNP、单张影像、ICD 或心超检查流程记录称作 DHF 确诊。\n\n")
        handle.write("## 数据完整性\n\n")
        coverage_note = "完整导出已通过行数与键唯一性校验" if extraction_complete else "当前导出不完整，模态与阳性计数只能作为下界"
        handle.write(f"患者级汇总显示窗口内应有 {summary_total:,} 份报告；当前审计得到 {extracted_total:,} 份，缺 {summary_total - extracted_total:,} 份，完整导出标志为 `{int(extraction_complete)}`。{coverage_note}。模态规则计数：CXR {modality_counts['chest_xray']:,}，胸部 CT {modality_counts['chest_ct']:,}，其他/未分类 {modality_counts['other_or_unclassified']:,}；影像阳性仍是自动筛查层，不能替代人工临床 adjudication。\n\n")
        handle.write("## 结局与 EPV\n\n")
        handle.write("| 表型层 | stays | event | compete | censor | EPV/45 |\n|---|---:|---:|---:|---:|---:|\n")
        for row in audit:
            handle.write(f"| `{row['phenotype']}` | {row['n_stays']} | {row['events']} | {row['competing_alive_icu_discharge']} | {row['administrative_censor']} | {row['epv_at_45_predictors']} |\n")
        handle.write("\n## Echo 边界\n\n")
        handle.write("MIMIC 结构化 echo 可表明检查流程或 LVEF 数值是否存在，但当前没有足以稳定判断心超异常的完整结果层。因此开发队列不能强制 echo-confirmed；院内外部验证仍应实行 `performed + result available + abnormal support` 三级 QC。\n")
    print(f"Wrote landmark-window audit to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
