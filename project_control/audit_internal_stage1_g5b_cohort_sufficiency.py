#!/usr/bin/env python3
"""Audit cohort sufficiency and phenotype sensitivity after方案B approval.

The audit quantifies A/B/C intersections without relaxing the frozen main
phenotype for sample-size reasons.  Supplemental near-boundary chart-review
sampling is deterministic and outcome-blind.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_internal_stage1_g5b_cohort_sufficiency"
OUT = CONTROL / "runs" / RUN_ID

G3 = CONTROL / "runs/20260924_internal_stage1_g3_phenotype/dhf_abc_evidence_ledger_v1.csv"
G4 = CONTROL / "runs/20260924_internal_stage1_g4_outcomes/hospital_disposition_ledger_v1.csv"
EXISTING_REVIEW = CONTROL / "runs/20260924_internal_stage1_g3_phenotype/clinical_review_sample_v1.csv"
AMENDMENT = CONTROL / "designs/INTERNAL_DHF_STAGE1_PROTOCOL_AMENDMENT_B_T0_V1_20260924.md"

SAMPLING_SEED = "internal_dhf_g5b_near_boundary_v1_20260924"
SUPPLEMENTAL_TARGETS = {"BC_without_A": 60, "AC_without_B": 40}


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


def c_supported(row):
    return any(
        is_true(row.get(field))
        for field in (
            "c_ntprobnp_rule_in_flag",
            "c_echo_abnormal_flag",
            "c_iv_loop_order_proxy_flag",
        )
    )


def abc_pattern(row):
    a = is_true(row.get("a_hf_anchor_flag"))
    b = is_true(row.get("b_decompensation_flag"))
    c = c_supported(row)
    mapping = {
        (True, True, True): "ABC",
        (True, True, False): "AB_without_C",
        (False, True, True): "BC_without_A",
        (True, False, True): "AC_without_B",
        (True, False, False): "A_only",
        (False, True, False): "B_only",
        (False, False, True): "C_only",
        (False, False, False): "none",
    }
    return mapping[(a, b, c)]


def effective_df_cap(events):
    return min(10, max(0, int(events) // 15))


def assess_cohort_sufficiency(*, n, events):
    cap = effective_df_cap(events)
    if n >= 300 and events >= 45:
        assessment = "adequate_for_description_and_low_dimensional_association"
    elif n >= 100:
        assessment = "adequate_for_description_association_limited_by_events"
    else:
        assessment = "precision_limited_requires_scope_review"
    return {
        "n": int(n),
        "events": int(events),
        "effective_df_cap": cap,
        "assessment": assessment,
        "prediction_model_development_supported": False,
        "relax_phenotype_for_sample_size": False,
    }


def summarize_ab_without_c(rows):
    boundary = [row for row in rows if abc_pattern(row) == "AB_without_C"]
    return {
        "AB_without_C_n": len(boundary),
        "ntprobnp_not_available_n": sum(
            not is_true(row.get("c_ntprobnp_pre12_measured_flag")) for row in boundary
        ),
        "ntprobnp_measured_below_rule_in_n": sum(
            is_true(row.get("c_ntprobnp_pre12_measured_flag")) for row in boundary
        ),
        "echo_not_available_n": sum(
            not is_true(row.get("c_echo_result_available_flag")) for row in boundary
        ),
        "echo_available_not_abnormal_n": sum(
            is_true(row.get("c_echo_result_available_flag")) for row in boundary
        ),
        "iv_loop_order_proxy_absent_n": sum(
            not is_true(row.get("c_iv_loop_order_proxy_flag")) for row in boundary
        ),
        "alternative_diagnosis_mentioned_n": sum(
            is_true(row.get("alternative_mentioned_flag")) for row in boundary
        ),
        "interpretation": (
            "mixed near-boundary group: unavailable objective evidence and available-but-not-supportive "
            "evidence must remain distinct; alternative diagnoses require blinded review"
        ),
    }


def wilson_interval(events, n, z=1.959963984540054):
    events = int(events)
    n = int(n)
    if n <= 0:
        return None, None
    proportion = events / n
    denominator = 1 + z * z / n
    centre = (proportion + z * z / (2 * n)) / denominator
    half = z * math.sqrt(proportion * (1 - proportion) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def deterministic_rank(visit_id):
    return hashlib.sha256(f"{SAMPLING_SEED}|{visit_id}".encode("utf-8")).hexdigest()


def build_review_row(row, stratum):
    return {
        "patient_id": row.get("patient_id", ""),
        "visit_id": row.get("visit_id", ""),
        "sex": row.get("sex", ""),
        "age": row.get("age", ""),
        "t0_time": row.get("t0_time", ""),
        "review_stratum": stratum,
        "old_pre_review_label": row.get("old_pre_review_label", ""),
        "algorithmic_label_v1": row.get("algorithmic_label_v1", ""),
        "a_hf_anchor_flag": row.get("a_hf_anchor_flag", ""),
        "b_decompensation_flag": row.get("b_decompensation_flag", ""),
        "c_ntprobnp_rule_in_flag": row.get("c_ntprobnp_rule_in_flag", ""),
        "c_echo_abnormal_flag": row.get("c_echo_abnormal_flag", ""),
        "c_iv_loop_order_proxy_flag": row.get("c_iv_loop_order_proxy_flag", ""),
        "a_source_refs": row.get("a_source_refs", ""),
        "a_evidence_excerpt": row.get("a_evidence_excerpt", ""),
        "b_source_refs": row.get("b_source_refs", ""),
        "b_evidence_excerpt": row.get("b_evidence_excerpt", ""),
        "c_ntprobnp_rule_in_summary": row.get("c_ntprobnp_rule_in_summary", ""),
        "c_ntprobnp_source_refs": row.get("c_ntprobnp_source_refs", ""),
        "echo_source_refs": row.get("echo_source_refs", ""),
        "c_iv_loop_order_summary": row.get("c_iv_loop_order_summary", ""),
        "c_iv_loop_source_refs": row.get("c_iv_loop_source_refs", ""),
        "alternative_mentioned_flag": row.get("alternative_mentioned_flag", ""),
        "review_question": (
            "Does the complete encounter support acute decompensated heart failure, "
            "non-DHF, or insufficient evidence? Review without outcome information."
        ),
        "clinician_reference_label": "",
        "evidence_sufficient": "",
        "adjudication_note": "",
    }


def select_supplemental_review(rows, existing_visit_ids, targets=None):
    targets = targets or SUPPLEMENTAL_TARGETS
    selected = []
    preferred_order = ["BC_without_A", "AC_without_B"]
    remaining = sorted(set(targets) - set(preferred_order))
    for stratum in preferred_order + remaining:
        if stratum not in targets:
            continue
        candidates = [
            row for row in rows
            if abc_pattern(row) == stratum and row.get("visit_id", "") not in existing_visit_ids
        ]
        candidates.sort(key=lambda row: deterministic_rank(row.get("visit_id", "")))
        target = int(targets[stratum])
        if len(candidates) < target:
            raise ValueError(f"insufficient {stratum} candidates: {len(candidates)} < {target}")
        selected.extend(build_review_row(row, stratum) for row in candidates[:target])
    return selected


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mortality_row(layer, ids, outcomes, interpretation):
    known = [outcomes[visit_id] for visit_id in ids if visit_id in outcomes]
    deaths = sum(row.get("hospital_outcome_status") == "hospital_death" for row in known)
    n = len(known)
    low, high = wilson_interval(deaths, n)
    return {
        "layer": layer,
        "n": n,
        "hospital_death_n": deaths,
        "hospital_death_percent": round(100 * deaths / n, 3) if n else "",
        "wilson_95ci_low_percent": round(100 * low, 3) if low is not None else "",
        "wilson_95ci_high_percent": round(100 * high, 3) if high is not None else "",
        "interpretation": interpretation,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    g3_rows = read_csv(G3)
    g4_rows = read_csv(G4)
    existing_review_rows = read_csv(EXISTING_REVIEW)
    if len(g3_rows) != 8385:
        raise ValueError(f"expected 8,385 G3 rows, got {len(g3_rows)}")
    if len(g4_rows) != 773:
        raise ValueError(f"expected 773 G4 hospital outcomes, got {len(g4_rows)}")

    pattern_counts = Counter(abc_pattern(row) for row in g3_rows)
    pattern_rows = [
        {
            "pattern": pattern,
            "n": count,
            "percent_of_source_frame": round(100 * count / len(g3_rows), 3),
            "role": {
                "ABC": "main_phenotype",
                "AB_without_C": "high_sensitivity_near_boundary",
                "BC_without_A": "supplemental_blinded_review",
                "AC_without_B": "supplemental_blinded_review",
            }.get(pattern, "not_main_phenotype"),
        }
        for pattern, count in sorted(pattern_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    write_csv(OUT / "abc_intersection_counts.csv", pattern_rows)

    main_ids = {row["visit_id"] for row in g3_rows if abc_pattern(row) == "ABC"}
    strict_ids = {
        row["visit_id"] for row in g3_rows if is_true(row.get("strict_objective_rule_supported_flag"))
    }
    treatment_only_ids = {
        row["visit_id"] for row in g3_rows if row.get("c_support_type") == "treatment_proxy_only_C"
        and abc_pattern(row) == "ABC"
    }
    high_sensitivity_ab_ids = {
        row["visit_id"] for row in g3_rows
        if is_true(row.get("a_hf_anchor_flag")) and is_true(row.get("b_decompensation_flag"))
    }
    layer_rows = [
        {"layer": "source_echo_assessed_adult_ICU", "n": len(g3_rows), "formal_role": "source_sampling_frame"},
        {"layer": "main_ABC", "n": len(main_ids), "formal_role": "方案B_primary_cohort"},
        {"layer": "strict_objective_ABC", "n": len(strict_ids), "formal_role": "pre_specified_specificity_sensitivity"},
        {"layer": "treatment_proxy_only_ABC", "n": len(treatment_only_ids), "formal_role": "circularity_sensitivity"},
        {"layer": "high_sensitivity_A_plus_B", "n": len(high_sensitivity_ab_ids), "formal_role": "sensitivity_only_pending_clinical_calibration"},
        {"layer": "AB_without_C", "n": pattern_counts["AB_without_C"], "formal_role": "highest_priority_possible_false_negatives"},
        {"layer": "BC_without_A", "n": pattern_counts["BC_without_A"], "formal_role": "anchor_missing_near_boundary_review"},
        {"layer": "AC_without_B", "n": pattern_counts["AC_without_B"], "formal_role": "decompensation_evidence_missing_review"},
        {"layer": "algorithmic_unknown", "n": sum(row.get("algorithmic_label_v1") == "algorithmic_unknown" for row in g3_rows), "formal_role": "unknown_not_negative"},
    ]
    write_csv(OUT / "phenotype_sensitivity_layers.csv", layer_rows)

    ab_without_c_profile = summarize_ab_without_c(g3_rows)
    (OUT / "ab_without_c_evidence_profile.json").write_text(
        json.dumps(ab_without_c_profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    calendar_counts = Counter()
    for row in g3_rows:
        year = row.get("t0_time", "")[:4] or "missing"
        calendar_counts[("source_frame", year)] += 1
        if row["visit_id"] in main_ids:
            calendar_counts[("main_ABC", year)] += 1
        if row["visit_id"] in strict_ids:
            calendar_counts[("strict_objective_ABC", year)] += 1
        if row["visit_id"] in high_sensitivity_ab_ids:
            calendar_counts[("high_sensitivity_A_plus_B", year)] += 1
    calendar_rows = [
        {
            "layer": layer,
            "calendar_year": year,
            "n": count,
            "calendar_status": "incomplete_calendar_period" if year == "2024" else "no_annual_trend_claim",
        }
        for (layer, year), count in sorted(calendar_counts.items())
    ]
    write_csv(OUT / "calendar_distribution_by_layer.csv", calendar_rows)

    outcomes = {row["visit_id"]: row for row in g4_rows}
    main_excluding_2024_ids = {
        row["visit_id"] for row in g3_rows
        if row["visit_id"] in main_ids and not row.get("t0_time", "").startswith("2024-")
    }
    mortality_rows = [
        mortality_row("main_ABC", main_ids, outcomes, "方案B primary descriptive mortality"),
        mortality_row("strict_objective_ABC", strict_ids, outcomes, "specificity sensitivity; not selected by outcome"),
        mortality_row("treatment_proxy_only_ABC", treatment_only_ids, outcomes, "circularity sensitivity; not causal treatment effect"),
        mortality_row("main_ABC_excluding_2024", main_excluding_2024_ids, outcomes, "pre-specified incomplete-calendar sensitivity"),
    ]
    write_csv(OUT / "mortality_precision_by_frozen_layer.csv", mortality_rows)

    existing_ids = {row.get("visit_id", "") for row in existing_review_rows}
    supplemental = select_supplemental_review(g3_rows, existing_ids, SUPPLEMENTAL_TARGETS)
    write_csv(OUT / "supplemental_near_boundary_review_sample_v1.csv", supplemental)
    review_manifest = {
        "sampling_seed": SAMPLING_SEED,
        "existing_review_n": len(existing_ids),
        "supplemental_review_n": len(supplemental),
        "targets": SUPPLEMENTAL_TARGETS,
        "overlap_with_existing_review_n": len(existing_ids & {row["visit_id"] for row in supplemental}),
        "outcome_fields_in_sampling_or_review_package": [],
        "sampling_independent_of_hospital_death": True,
        "clinical_reference_standard_completed": False,
    }
    (OUT / "review_sampling_manifest.json").write_text(
        json.dumps(review_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    primary_mortality = mortality_rows[0]
    sufficiency = assess_cohort_sufficiency(n=primary_mortality["n"], events=primary_mortality["hospital_death_n"])
    decision = {
        "run_id": RUN_ID,
        "status": "KEEP_ABC_MAIN_ADD_PRE_SPECIFIED_SENSITIVITY_AND_REVIEW_LAYERS",
        "方案B_primary_cohort_n": len(main_ids),
        "方案B_hospital_death_n": primary_mortality["hospital_death_n"],
        "方案B_hospital_death_percent": primary_mortality["hospital_death_percent"],
        "方案B_hospital_death_wilson_95ci_percent": [
            primary_mortality["wilson_95ci_low_percent"],
            primary_mortality["wilson_95ci_high_percent"],
        ],
        **sufficiency,
        "main_phenotype_change_required": False,
        "reason": (
            "773 participants and 62 deaths support descriptive estimates and a pre-specified low-dimensional "
            "association analysis, but not broad predictor screening or a second prediction model"
        ),
        "possible_false_negative_audit": {
            "AB_without_C_n": pattern_counts["AB_without_C"],
            "BC_without_A_n": pattern_counts["BC_without_A"],
            "AC_without_B_n": pattern_counts["AC_without_B"],
            "AB_without_C_evidence_profile": ab_without_c_profile,
            "clinical_calibration_required_before_reclassification": True,
        },
        "frozen_layers": {
            "main": "ABC_773",
            "strict": f"objective_ABC_{len(strict_ids)}",
            "high_sensitivity": f"A_plus_B_{len(high_sensitivity_ab_ids)}",
        },
        "eMAR_plan": "replace_short_outcome_execution_layer_when_available_without_reopening_ABC_or_T0_death_design",
        "models_run": False,
        "raw_data_modified": False,
        "next_gate": "G6_descriptive_analysis_and_T0_candidate_factor_availability_audit",
    }
    (OUT / "cohort_sufficiency_decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    expected = {
        "ABC": 773,
        "AB_without_C": 340,
        "BC_without_A": 766,
        "AC_without_B": 271,
        "A_only": 651,
        "B_only": 1289,
        "C_only": 859,
        "none": 3436,
    }
    if dict(pattern_counts) != expected:
        raise ValueError(f"unexpected A/B/C intersections: {dict(pattern_counts)}")
    if len(strict_ids) != 594 or len(high_sensitivity_ab_ids) != 1113 or len(treatment_only_ids) != 179:
        raise ValueError("frozen phenotype layer counts changed unexpectedly")
    if primary_mortality["hospital_death_n"] != 62 or primary_mortality["n"] != 773:
        raise ValueError("G4 main mortality count changed unexpectedly")
    expected_ab_profile = {
        "AB_without_C_n": 340,
        "ntprobnp_not_available_n": 300,
        "ntprobnp_measured_below_rule_in_n": 40,
        "echo_not_available_n": 280,
        "echo_available_not_abnormal_n": 60,
        "iv_loop_order_proxy_absent_n": 340,
        "alternative_diagnosis_mentioned_n": 333,
    }
    if any(ab_without_c_profile[key] != value for key, value in expected_ab_profile.items()):
        raise ValueError(f"unexpected AB-without-C evidence profile: {ab_without_c_profile}")
    if review_manifest["overlap_with_existing_review_n"] != 0 or len(supplemental) != 100:
        raise ValueError("supplemental review sample is not independent or complete")

    snapshot_paths = [G3, G4, EXISTING_REVIEW, AMENDMENT]
    snapshot = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in snapshot_paths
        ],
    }
    (OUT / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    qc = {
        "run_id": RUN_ID,
        "status": decision["status"],
        "source_rows": len(g3_rows),
        "main_ABC_n": len(main_ids),
        "strict_objective_ABC_n": len(strict_ids),
        "high_sensitivity_A_plus_B_n": len(high_sensitivity_ab_ids),
        "AB_without_C_n": pattern_counts["AB_without_C"],
        "AB_without_C_ntprobnp_not_available_n": ab_without_c_profile["ntprobnp_not_available_n"],
        "AB_without_C_echo_not_available_n": ab_without_c_profile["echo_not_available_n"],
        "AB_without_C_alternative_diagnosis_mentioned_n": ab_without_c_profile["alternative_diagnosis_mentioned_n"],
        "BC_without_A_n": pattern_counts["BC_without_A"],
        "AC_without_B_n": pattern_counts["AC_without_B"],
        "main_hospital_death_n": primary_mortality["hospital_death_n"],
        "effective_df_cap": sufficiency["effective_df_cap"],
        "supplemental_review_n": len(supplemental),
        "clinical_calibration_completed": False,
        "phenotype_relaxed_for_sample_size": False,
        "models_run": False,
        "raw_data_modified": False,
    }
    (OUT / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "run_id": RUN_ID,
        "status": qc["status"],
        "main_ABC_n": qc["main_ABC_n"],
        "main_hospital_death_n": qc["main_hospital_death_n"],
        "effective_df_cap": qc["effective_df_cap"],
        "AB_without_C_n": qc["AB_without_C_n"],
        "supplemental_review_n": qc["supplemental_review_n"],
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
