#!/usr/bin/env python3
"""Build Study-1 G6 descriptive outputs without fitting association models.

The script uses the frozen ABC cohort and frozen outcome ledgers.  It also
audits which T0 factors are actually available before any effect estimates are
computed, so unavailable or post-T0 variables cannot silently enter G7.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_internal_stage1_g6_descriptive"
OUT = CONTROL / "runs" / RUN_ID

G2 = CONTROL / "runs/20260924_internal_stage1_g2_chronology/episode_chronology_reconciled.csv"
G3 = CONTROL / "runs/20260924_internal_stage1_g3_phenotype/dhf_abc_evidence_ledger_v1.csv"
G4_HOSPITAL = CONTROL / "runs/20260924_internal_stage1_g4_outcomes/hospital_disposition_ledger_v1.csv"
G4_SHORT = CONTROL / "runs/20260924_internal_stage1_g4_outcomes/t12_short_outcome_proxy_ledger_v1.csv"
G5B = CONTROL / "runs/20260924_internal_stage1_g5b_cohort_sufficiency/cohort_sufficiency_decision.json"
AMENDMENT = CONTROL / "designs/INTERNAL_DHF_STAGE1_PROTOCOL_AMENDMENT_B_T0_V1_20260924.md"
HOMEPAGE_FILES = [
    ROOT / "DHF_SRR/DHF--男_病案首页20260911203904117/02_rdr_emr_inp_homepage.csv",
    ROOT / "DHF_SRR/DHF--女_病案首页20260911195949092/02_rdr_emr_inp_homepage.csv",
]
DIAGNOSIS_FILES = [
    ROOT / "DHF_SRR/DHF--男_诊断信息20260911203952612/02_rdr_diagnosis.csv",
    ROOT / "DHF_SRR/DHF--女_诊断信息20260911211222860/02_rdr_diagnosis.csv",
]
ADMISSION_HISTORY_FILES = [
    ROOT / "DHF_SRR/DHF--男_入院病史20260911204028934/02_rdr_admit_info.csv",
    ROOT / "DHF_SRR/DHF--女_入院病史20260911200821856/02_rdr_admit_info.csv",
]


def read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    if not rows and not fields:
        raise ValueError(f"cannot infer fields for empty output: {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def is_true(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def as_float(value):
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def numeric_summary(values):
    observed = sorted(value for raw in values if (value := as_float(raw)) is not None)
    if not observed:
        return {"available_n": 0, "median": None, "q1": None, "q3": None, "min": None, "max": None}
    if len(observed) == 1:
        q1 = q3 = observed[0]
    else:
        q1, _, q3 = statistics.quantiles(observed, n=4, method="inclusive")
    return {
        "available_n": len(observed),
        "median": round(statistics.median(observed), 3),
        "q1": round(q1, 3),
        "q3": round(q3, 3),
        "min": round(observed[0], 3),
        "max": round(observed[-1], 3),
    }


def normalize_admission_route(value):
    text = str(value or "").strip()
    if "急诊" in text:
        return "emergency"
    if "门诊" in text:
        return "outpatient"
    if "转诊" in text:
        return "transfer"
    return "unknown"


def latest_homepage_by_visit(rows):
    latest = {}
    for row in rows:
        visit_id = row.get("就诊号", "")
        if not visit_id:
            continue
        if visit_id not in latest or row.get("更新时间", "") > latest[visit_id].get("更新时间", ""):
            latest[visit_id] = row
    return latest


def audit_comorbidity_sources(main_by_id, diagnosis_rows, admission_rows):
    main_ids = set(main_by_id)
    diagnosis_visit_ids = {
        row.get("就诊号", "") for row in diagnosis_rows
        if row.get("就诊号", "") in main_ids
        and row.get("诊断时间", "")
        and row["诊断时间"] <= main_by_id[row["就诊号"]].get("t0_time", "")
    }
    admission_visit_ids = {
        row.get("就诊号", "") for row in admission_rows if row.get("就诊号", "") in main_ids
    }
    admission_by_t0_ids = {
        row.get("就诊号", "") for row in admission_rows
        if row.get("就诊号", "") in main_ids
        and row.get("创建日期", "")
        and row["创建日期"] <= main_by_id[row["就诊号"]].get("t0_time", "")
    }
    return {
        "cohort_n": len(main_ids),
        "pre_T0_diagnosis_visit_n": len(diagnosis_visit_ids),
        "no_pre_T0_diagnosis_record_n": len(main_ids - diagnosis_visit_ids),
        "admission_history_visit_n": len(admission_visit_ids),
        "admission_history_created_by_T0_n": len(admission_by_t0_ids),
        "admission_history_created_after_T0_or_time_missing_n": len(admission_visit_ids - admission_by_t0_ids),
        "absence_can_be_interpreted_as_no_comorbidity": False,
        "gate_status": "mapping_and_missing_semantics_required_before_G7",
    }


def summarize_main_cohort(rows):
    age = numeric_summary(row.get("age") for row in rows)
    sex = Counter(row.get("sex", "").strip() or "unknown" for row in rows)
    outcomes = Counter(row.get("hospital_outcome_status", "").strip() or "outcome_unknown" for row in rows)
    return {
        "n": len(rows),
        **{f"age_{key}": value for key, value in age.items()},
        "male_n": sex.get("男", 0),
        "female_n": sex.get("女", 0),
        "sex_unknown_n": len(rows) - sex.get("男", 0) - sex.get("女", 0),
        "hospital_death_n": outcomes.get("hospital_death", 0),
        "alive_hospital_discharge_n": outcomes.get("alive_hospital_discharge", 0),
        "outcome_unknown_n": outcomes.get("outcome_unknown", 0),
    }


def build_t0_factor_manifest(rows):
    n = len(rows)
    age_n = sum(as_float(row.get("age")) is not None for row in rows)
    sex_n = sum(row.get("sex", "").strip() in {"男", "女"} for row in rows)
    route_n = sum(normalize_admission_route(row.get("admission_route")) != "unknown" for row in rows)
    route_gate = (
        "eligible_for_pre_effect_freeze" if n and route_n == n
        else "incomplete_mapping" if route_n else "not_yet_mapped"
    )
    return [
        {
            "factor": "age",
            "available_n": age_n,
            "available_percent": round(100 * age_n / n, 3) if n else 0,
            "time_status": "known_at_T0",
            "gate_status": "eligible_for_pre_effect_freeze",
            "df_if_selected": 1,
            "reason": "continuous linear form only unless extra df are explicitly budgeted",
        },
        {
            "factor": "sex",
            "available_n": sex_n,
            "available_percent": round(100 * sex_n / n, 3) if n else 0,
            "time_status": "known_at_T0",
            "gate_status": "eligible_for_pre_effect_freeze",
            "df_if_selected": 1,
            "reason": "binary coding with unknown retained if present",
        },
        {
            "factor": "chronic_comorbidity_set",
            "available_n": 0,
            "available_percent": 0,
            "time_status": "pre_ICU_in_principle",
            "gate_status": "not_yet_mapped",
            "df_if_selected": "pending",
            "reason": "requires diagnosis/history source mapping before effect inspection",
        },
        {
            "factor": "admission_route",
            "available_n": route_n,
            "available_percent": round(100 * route_n / n, 3) if n else 0,
            "time_status": "known_at_T0_in_principle",
            "gate_status": route_gate,
            "df_if_selected": 1 if route_gate == "eligible_for_pre_effect_freeze" else "pending",
            "reason": "pre-specify emergency versus non-emergency to avoid spending two df on three sparse categories",
        },
        {
            "factor": "early_laboratory_or_vital_values",
            "available_n": 0,
            "available_percent": 0,
            "time_status": "observed_after_T0",
            "gate_status": "excluded_post_T0",
            "df_if_selected": 0,
            "reason": "cannot be relabelled as T0 baseline; needs a separately registered early window",
        },
        {
            "factor": "phenotype_components_A_B_C",
            "available_n": n,
            "available_percent": 100 if n else 0,
            "time_status": "cohort_definition",
            "gate_status": "excluded_conditioning_and_circularity",
            "df_if_selected": 0,
            "reason": "defines cohort membership and is not a candidate baseline prognostic factor",
        },
    ]


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    g2_rows = read_csv(G2)
    g3_rows = read_csv(G3)
    hospital_rows = read_csv(G4_HOSPITAL)
    short_rows = read_csv(G4_SHORT)
    homepage_rows = []
    for path in HOMEPAGE_FILES:
        homepage_rows.extend(read_csv(path))
    homepage_by_id = latest_homepage_by_visit(homepage_rows)
    diagnosis_rows = []
    for path in DIAGNOSIS_FILES:
        diagnosis_rows.extend(read_csv(path))
    admission_rows = []
    for path in ADMISSION_HISTORY_FILES:
        admission_rows.extend(read_csv(path))

    main_g3 = [row for row in g3_rows if is_true(row.get("main_rule_supported_flag"))]
    hospital_by_id = {row["visit_id"]: row for row in hospital_rows}
    g2_by_id = {row["visit_id"]: row for row in g2_rows}
    merged = []
    for row in main_g3:
        visit_id = row["visit_id"]
        if visit_id not in hospital_by_id or visit_id not in g2_by_id or visit_id not in homepage_by_id:
            raise ValueError(f"missing frozen outcome, chronology, or homepage for {visit_id}")
        merged.append({**row, **{f"outcome_{k}": v for k, v in hospital_by_id[visit_id].items()},
                       "hospital_outcome_status": hospital_by_id[visit_id].get("hospital_outcome_status", ""),
                       "t0_source_quality": g2_by_id[visit_id].get("t0_source_quality", ""),
                       "chronology_conflict": g2_by_id[visit_id].get("chronology_conflict", ""),
                       "admission_route": homepage_by_id[visit_id].get("入院途径", "")})

    summary = summarize_main_cohort(merged)
    descriptive_rows = [
        {"domain": "cohort", "measure": "main_ABC_n", "value": summary["n"], "denominator": summary["n"]},
        {"domain": "demography", "measure": "age_available_n", "value": summary["age_available_n"], "denominator": summary["n"]},
        {"domain": "demography", "measure": "age_median", "value": summary["age_median"], "denominator": summary["age_available_n"]},
        {"domain": "demography", "measure": "age_q1", "value": summary["age_q1"], "denominator": summary["age_available_n"]},
        {"domain": "demography", "measure": "age_q3", "value": summary["age_q3"], "denominator": summary["age_available_n"]},
        {"domain": "demography", "measure": "male_n", "value": summary["male_n"], "denominator": summary["n"]},
        {"domain": "demography", "measure": "female_n", "value": summary["female_n"], "denominator": summary["n"]},
        {"domain": "outcome", "measure": "hospital_death_n", "value": summary["hospital_death_n"], "denominator": summary["n"]},
        {"domain": "outcome", "measure": "alive_hospital_discharge_n", "value": summary["alive_hospital_discharge_n"], "denominator": summary["n"]},
        {"domain": "outcome", "measure": "outcome_unknown_n", "value": summary["outcome_unknown_n"], "denominator": summary["n"]},
    ]
    for item in descriptive_rows:
        denominator = int(item["denominator"] or 0)
        value = item["value"]
        item["percent_if_count"] = (
            round(100 * float(value) / denominator, 3)
            if denominator and str(item["measure"]).endswith("_n") else ""
        )
    write_csv(OUT / "descriptive_summary_v1.csv", descriptive_rows)

    c_support = Counter(row.get("c_support_type", "") or "unknown" for row in main_g3)
    b_support = Counter(
        ("congestion+symptom" if is_true(row.get("b_congestion_flag")) and is_true(row.get("b_symptom_flag"))
         else "congestion_only" if is_true(row.get("b_congestion_flag"))
         else "symptom_only" if is_true(row.get("b_symptom_flag")) else "unknown")
        for row in main_g3
    )
    phenotype_rows = [
        {"domain": "C_support_type", "category": key, "n": value, "percent": round(100 * value / len(main_g3), 3)}
        for key, value in sorted(c_support.items())
    ] + [
        {"domain": "B_support_type", "category": key, "n": value, "percent": round(100 * value / len(main_g3), 3)}
        for key, value in sorted(b_support.items())
    ] + [{
        "domain": "alternative_diagnosis",
        "category": "mentioned",
        "n": sum(is_true(row.get("alternative_mentioned_flag")) for row in main_g3),
        "percent": round(100 * sum(is_true(row.get("alternative_mentioned_flag")) for row in main_g3) / len(main_g3), 3),
    }]
    write_csv(OUT / "phenotype_evidence_summary_v1.csv", phenotype_rows)

    year_counts = Counter(row.get("t0_time", "")[:4] or "missing" for row in main_g3)
    admission_route_counts = Counter(normalize_admission_route(row.get("admission_route")) for row in merged)
    t0_quality_counts = Counter(row.get("t0_source_quality", "") or "unknown" for row in merged)
    chronology_conflict_n = sum(bool(row.get("chronology_conflict", "").strip()) for row in merged)
    quality_rows = [
        {"domain": "calendar_year", "category": year, "n": count,
         "status": "incomplete_calendar_period" if year == "2024" else "no_annual_incidence_claim"}
        for year, count in sorted(year_counts.items())
    ] + [
        {"domain": "admission_route", "category": route, "n": count, "status": "known_at_T0"}
        for route, count in sorted(admission_route_counts.items())
    ] + [
        {"domain": "t0_source_quality", "category": quality, "n": count, "status": "descriptive_only"}
        for quality, count in sorted(t0_quality_counts.items())
    ] + [{
        "domain": "chronology", "category": "conflict_flag_nonempty", "n": chronology_conflict_n,
        "status": "retain_for_sensitivity_and_review",
    }]
    write_csv(OUT / "data_quality_summary_v1.csv", quality_rows)

    short_counts = Counter(row.get("short_outcome_status", "") or "outcome_unknown" for row in short_rows)
    short_component_counts = Counter(row.get("short_outcome_component", "") or "none" for row in short_rows)
    short_summary_rows = [
        {"domain": "short_outcome_status", "category": key, "n": value,
         "evidence_level": "order_or_tube_proxy_not_eMAR"}
        for key, value in sorted(short_counts.items())
    ] + [
        {"domain": "short_outcome_component", "category": key, "n": value,
         "evidence_level": "order_or_tube_proxy_not_eMAR"}
        for key, value in sorted(short_component_counts.items())
    ]
    write_csv(OUT / "short_outcome_proxy_summary_v1.csv", short_summary_rows)

    flow_rows = [
        {"step": 1, "population": "source_echo_assessed_adult_ICU", "n": len(g3_rows), "role": "sampling_frame"},
        {"step": 2, "population": "main_ABC", "n": len(main_g3), "role": "方案B_primary_cohort"},
        {"step": 3, "population": "strict_objective_ABC", "n": sum(is_true(row.get("strict_objective_rule_supported_flag")) for row in g3_rows), "role": "specificity_sensitivity"},
        {"step": 4, "population": "strict_T12_riskset", "n": len(short_rows), "role": "short_pathway_and_study2_3"},
        {"step": 5, "population": "hospital_death", "n": summary["hospital_death_n"], "role": "方案B_outcome"},
    ]
    write_csv(OUT / "cohort_flow_counts.csv", flow_rows)

    factor_manifest = build_t0_factor_manifest(merged)
    write_csv(OUT / "t0_candidate_factor_availability_v1.csv", factor_manifest)
    main_by_id = {row["visit_id"]: row for row in main_g3}
    comorbidity_audit = audit_comorbidity_sources(main_by_id, diagnosis_rows, admission_rows)
    comorbidity_rows = [
        {"measure": key, "value": value,
         "interpretation": (
             "absence_is_unknown_not_no_comorbidity" if key == "no_pre_T0_diagnosis_record_n"
             else "source_coverage_only_not_final_comorbidity_label"
         )}
        for key, value in comorbidity_audit.items()
    ]
    write_csv(OUT / "comorbidity_source_coverage_v1.csv", comorbidity_rows)
    eligible_factors = [row["factor"] for row in factor_manifest if row["gate_status"] == "eligible_for_pre_effect_freeze"]
    decision = {
        "run_id": RUN_ID,
        "status": "G6_DESCRIPTION_COMPLETE_T0_FACTOR_FREEZE_PENDING",
        "main_ABC_n": summary["n"],
        "hospital_death_n": summary["hospital_death_n"],
        "descriptive_analysis_completed": True,
        "association_models_run": False,
        "t0_candidate_contract_ready": False,
        "currently_audited_eligible_factors": eligible_factors,
        "reason_not_ready": "admission route is mapped, but chronic comorbidity labels and their unknown semantics are not yet frozen",
        "comorbidity_source_audit": comorbidity_audit,
        "effective_df_cap": 4,
        "phenotype_change_required": False,
        "eMAR_required_to_complete_G6": False,
        "eMAR_role_when_available": "upgrade_T12_short_outcome_execution_layer_only",
        "next_gate": "map_pre_existing_comorbidities_with_unknown_preserved_then_freeze_max_4_df_before_effects",
        "raw_data_modified": False,
    }
    (OUT / "gate_decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")

    if summary["n"] != 773 or summary["hospital_death_n"] != 62 or summary["outcome_unknown_n"] != 0:
        raise ValueError(f"frozen方案B counts changed: {summary}")
    if len(short_rows) != 558 or short_counts != Counter({
        "administrative_censor": 273, "competing_event": 150, "target_event": 81, "outcome_unknown": 54
    }):
        raise ValueError(f"frozen short-outcome counts changed: n={len(short_rows)} counts={short_counts}")
    if sum(row["n"] for row in phenotype_rows if row["domain"] == "C_support_type") != 773:
        raise ValueError("C-support categories do not sum to the main cohort")

    inputs = [
        G2, G3, G4_HOSPITAL, G4_SHORT, G5B, AMENDMENT,
        *HOMEPAGE_FILES, *DIAGNOSIS_FILES, *ADMISSION_HISTORY_FILES,
    ]
    snapshot = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in inputs
        ],
    }
    (OUT / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    qc = {
        "run_id": RUN_ID,
        "status": decision["status"],
        "main_ABC_n": summary["n"],
        "hospital_death_n": summary["hospital_death_n"],
        "short_riskset_n": len(short_rows),
        "eligible_T0_factors_currently_audited": eligible_factors,
        "t0_candidate_contract_ready": False,
        "association_models_run": False,
        "raw_data_modified": False,
    }
    (OUT / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**qc, "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
