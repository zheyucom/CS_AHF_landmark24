#!/usr/bin/env python3
"""Build a full-cohort, rule-supported DHF phenotype and outcome audit.

This is a deterministic bridge from the 106/107 exports to a patient-level
decision table.  It does not convert regex output into a clinical gold
standard and it does not use post-landmark predictors to define eligibility.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "project_control/bigquery"
CANDIDATES = BASE / "dhf_radiology_candidates.csv"
RAW = BASE / "dhf_radiology_raw_v2.csv"
OUTCOME = ROOT / "project_control/runs/20260827_v3_2_outcome_label_audit/data/096_strict_main_label_v33.csv"
OUTPUT_DIR = BASE / "controlled_annotation_20260830_v2/processed_20260902"
N_PREDICTORS = 45


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def yes(row: dict[str, str], key: str) -> bool:
    return row.get(key, "") == "1"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    candidates = read_csv(CANDIDATES)
    raw = read_csv(RAW)
    outcomes = {r["stay_id"]: r for r in read_csv(OUTCOME)}

    valid = {
        r["stay_id"]: r for r in candidates
        if datetime.fromisoformat(r["admittime"]) <= datetime.fromisoformat(r["intime"])
    }
    if len(valid) != 5549:
        raise SystemExit(f"Expected 5,549 valid candidate stays, got {len(valid)}")

    reports: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        if row["stay_id"] in valid:
            reports[row["stay_id"]].append(row)

    rows: list[dict[str, object]] = []
    for stay_id, candidate in sorted(valid.items(), key=lambda item: int(item[0])):
        stay_reports = reports.get(stay_id, [])
        definite_charttime = [
            r for r in stay_reports
            if yes(r, "positive_congestion_evidence_flag") and not yes(r, "uncertainty_hit")
        ]
        definite_available = [
            r for r in definite_charttime if yes(r, "report_available_pre_t0_flag")
        ]
        positive_charttime = [r for r in stay_reports if yes(r, "positive_congestion_evidence_flag")]
        positive_available = [r for r in positive_charttime if yes(r, "report_available_pre_t0_flag")]
        loop = yes(candidate, "pre_t0_iv_loop_emar_flag")
        ntprobnp = yes(candidate, "pre_t0_ntprobnp_ge300_flag")
        hf_anchor = yes(candidate, "acute_hf_icd_anchor_flag")
        candidate_support = hf_anchor and (loop or ntprobnp)
        radiology_support = hf_anchor and bool(definite_charttime)
        radiology_available_support = hf_anchor and bool(definite_available)
        multidomain_loop = radiology_available_support and loop
        multidomain_loop_or_nt = radiology_available_support and (loop or ntprobnp)
        outcome = outcomes.get(stay_id, {})
        final_state = outcome.get("final_state", "")
        event = final_state == "event"
        compete = final_state == "compete"
        censor = final_state == "censor"
        rows.append({
            "stay_id": stay_id,
            "subject_id": candidate["subject_id"],
            "hadm_id": candidate["hadm_id"],
            "acute_hf_icd_anchor_flag": int(hf_anchor),
            "pre_t0_iv_loop_emar_flag": int(loop),
            "pre_t0_ntprobnp_ge300_flag": int(ntprobnp),
            "n_pre_t0_radiology_reports": len(stay_reports),
            "n_positive_radiology_screen_reports": len(positive_charttime),
            "n_definite_radiology_screen_reports": len(definite_charttime),
            "n_definite_available_pre_t0_reports": len(definite_available),
            "any_positive_radiology_screen_flag": int(bool(positive_charttime)),
            "any_definite_radiology_screen_flag": int(bool(definite_charttime)),
            "any_definite_available_pre_t0_flag": int(bool(definite_available)),
            "any_positive_available_pre_t0_flag": int(bool(positive_available)),
            "dhf_candidate_rule_supported_flag": int(candidate_support),
            "radiology_supported_rule_supported_flag": int(radiology_support),
            "radiology_available_supported_rule_supported_flag": int(radiology_available_support),
            "multidomain_loop_rule_supported_flag": int(multidomain_loop),
            "multidomain_loop_or_ntprobnp_rule_supported_flag": int(multidomain_loop_or_nt),
            "final_state": final_state,
            "event_flag": int(event),
            "competing_alive_icu_discharge_flag": int(compete),
            "administrative_censor_flag": int(censor),
        })

    output = OUTPUT_DIR / "dhf_patient_level_rule_supported_audit_20260902.csv"
    write_csv(output, rows)

    definitions = {
        "dhf_candidate_rule_supported": lambda r: r["dhf_candidate_rule_supported_flag"] == 1,
        "radiology_supported_charttime_rule_supported": lambda r: r["radiology_supported_rule_supported_flag"] == 1,
        "radiology_supported_available_rule_supported": lambda r: r["radiology_available_supported_rule_supported_flag"] == 1,
        "multidomain_loop_rule_supported": lambda r: r["multidomain_loop_rule_supported_flag"] == 1,
        "multidomain_loop_or_ntprobnp_rule_supported": lambda r: r["multidomain_loop_or_ntprobnp_rule_supported_flag"] == 1,
    }
    audit_rows: list[dict[str, object]] = []
    for name, predicate in definitions.items():
        subset = [r for r in rows if predicate(r)]
        n = len(subset)
        events = sum(r["event_flag"] for r in subset)
        competing = sum(r["competing_alive_icu_discharge_flag"] for r in subset)
        censor = sum(r["administrative_censor_flag"] for r in subset)
        audit_rows.append({
            "phenotype": name,
            "rule_status": "rule_supported_operational_phenotype",
            "definition": {
                "dhf_candidate_rule_supported": "HF ICD anchor + pre-T0 IV loop or NT-proBNP >=300",
                "radiology_supported_charttime_rule_supported": "HF ICD anchor + definite congestion screen by report charttime",
                "radiology_supported_available_rule_supported": "HF ICD anchor + definite congestion screen with storetime < ICU intime",
                "multidomain_loop_rule_supported": "available definite congestion + pre-T0 IV loop",
                "multidomain_loop_or_ntprobnp_rule_supported": "available definite congestion + pre-T0 IV loop or NT-proBNP >=300",
            }[name],
            "n_stays": n,
            "events": events,
            "competing_alive_icu_discharge": competing,
            "administrative_censor": censor,
            "event_rate": f"{events / n:.4f}" if n else "NA",
            f"epv_at_{N_PREDICTORS}_predictors": f"{events / N_PREDICTORS:.2f}" if events else "0.00",
            "epv_ge_10_flag": int(events / N_PREDICTORS >= 10),
        })
        if events + competing + censor != n:
            raise SystemExit(f"Outcome states do not sum for {name}: {n}, {events}, {competing}, {censor}")
    audit_path = OUTPUT_DIR / "dhf_patient_level_rule_supported_outcome_epv_audit_20260902.csv"
    write_csv(audit_path, audit_rows)

    report_path = OUTPUT_DIR / "DHF_PATIENT_LEVEL_RULE_SUPPORTED_AUDIT_2026-09-02.md"
    counts = Counter()
    for row in rows:
        counts["all"] += 1
        for name, predicate in definitions.items():
            if predicate(row):
                counts[name] += 1
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# DHF 患者级规则支持表型与结局/EPV 审计\n\n")
        handle.write("日期：2026-09-02\n\n")
        handle.write("## 解释边界\n\n")
        handle.write("本文件把 106/107 的全量 radiology regex 结果汇总到 stay level，供冻结前审计。所有 radiology 层均命名为 `rule-supported operational phenotype`，不是 5,549 个 stay 的人工确诊 DHF。300 条人工标注是报告级分层验证样本，不能直接回填全量患者标签。\n\n")
        handle.write("`multidomain_loop_rule_supported` 使用 IV loop 作为实际治疗证据；另列 `loop_or_ntprobnp` 仅作宽松敏感性口径，不能把 NT-proBNP 写成治疗证据。\n\n")
        handle.write("## 全量队列结果\n\n")
        handle.write("| 表型层 | stays | event | alive ICU discharge compete | censor | EPV (45 predictors) |\n|---|---:|---:|---:|---:|---:|\n")
        for audit in audit_rows:
            handle.write(f"| `{audit['phenotype']}` | {audit['n_stays']} | {audit['events']} | {audit['competing_alive_icu_discharge']} | {audit['administrative_censor']} | {audit[f'epv_at_{N_PREDICTORS}_predictors']} |\n")
        handle.write("\n所有层的 event + compete + censor 应等于该层 stays；EPV 只是当前 45 个候选预测器下的冻结前审计，不代表最终模型已经批准使用 45 个变量。\n\n")
        handle.write("## 交付文件\n\n")
        handle.write("- `dhf_patient_level_rule_supported_audit_20260902.csv`：5,549 个 stay 的逐患者证据和结局字段。\n")
        handle.write("- `dhf_patient_level_rule_supported_outcome_epv_audit_20260902.csv`：各规则支持层的样本量、结局和 EPV。\n")
        handle.write("- `DHF_PATIENT_LEVEL_RULE_SUPPORTED_AUDIT_2026-09-02.md`：本审计说明。\n\n")
        handle.write("## 尚未解决\n\n")
        handle.write("1. 规则阳性层单标注 PPV 为 78.0%，因此全量规则支持层仍存在误触发，不能当作临床金标准。\n")
        handle.write("2. 60 条重复是同标注者复制，未产生独立 inter-rater kappa。\n")
        handle.write("3. 主队列应在导师确认后从上述层中冻结；冻结后才重建最终无泄露预测器并重跑 Fine-Gray。\n")
    print(f"Wrote {output}, {audit_path}, and {report_path}")


if __name__ == "__main__":
    main()
