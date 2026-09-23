#!/usr/bin/env python3
"""Build the internal DHF Study-1 G3 A/B/C evidence ledger.

The algorithmic phenotype contract is frozen before outcomes are reconstructed.
This script adds age-stratified NT-proBNP rule-in evidence, restricts treatment
support to explicit pre-T12 IV loop order proxies, preserves strict objective
and broad treatment-supported layers, and prepares a deterministic clinical
calibration sample. It does not create a clinical gold standard or run models.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_internal_stage1_g3_phenotype"
OUT = CONTROL / "runs" / RUN_ID

PHENO = CONTROL / "internal_validation/20260916_semantic_corrected/dhf_phenotype_pre_review.csv"
TIME_EVIDENCE = CONTROL / "internal_validation/20260916_semantic_corrected/time_gated_evidence.csv"
BNP = CONTROL / "internal_validation/20260916_semantic_corrected/bnp_general_lab_evidence.csv"
ORDERS = CONTROL / "internal_validation/20260916_semantic_corrected/treatment_orders_targeted.csv"
MASTER = CONTROL / "internal_validation/20260912/icu_stay_master_20260912.csv"
G2 = CONTROL / "runs/20260924_internal_stage1_g2_chronology/episode_chronology_reconciled.csv"
CONTRACT = CONTROL / "INTERNAL_DHF_PHENOTYPE_CONTRACT_V1.md"
SAP = CONTROL / "STATISTICAL_ANALYSIS_PLAN_INTERNAL_DHF_STUDY1_V1.md"

SAMPLING_SEED = "internal_dhf_g3_review_v1_20260924"
REVIEW_TARGETS = {
    "main_supported_objective_C": 60,
    "main_supported_treatment_only_C": 60,
    "algorithmic_unknown": 50,
    "near_boundary_A_B_without_C": 60,
    "rule_not_supported_random": 60,
}


def read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_true(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ntprobnp_threshold(age):
    age = parse_float(age)
    if age is None:
        return None
    if age < 50:
        return 450.0
    if age <= 75:
        return 900.0
    return 1800.0


def ntprobnp_rule_in(age, raw_value):
    threshold = ntprobnp_threshold(age)
    raw = str(raw_value or "").strip().replace(",", "")
    qualifier = ">" if ">" in raw or "≥" in raw else "<" if "<" in raw or "≤" in raw else "="
    match = re.search(r"[-+]?\d+(?:\.\d+)?", raw)
    if threshold is None:
        return {
            "threshold_pg_ml": None,
            "qualifier": qualifier,
            "numeric_bound_pg_ml": float(match.group()) if match else None,
            "status": "unknown_age",
        }
    if not match:
        return {
            "threshold_pg_ml": threshold,
            "qualifier": qualifier,
            "numeric_bound_pg_ml": None,
            "status": "unknown_unparseable",
        }
    value = float(match.group())
    if qualifier == ">":
        status = "rule_in" if value >= threshold else "indeterminate_lower_bound"
    elif qualifier == "<":
        status = "below_rule_in" if value <= threshold else "indeterminate_upper_bound"
    else:
        status = "rule_in" if value >= threshold else "below_rule_in"
    return {
        "threshold_pg_ml": threshold,
        "qualifier": qualifier,
        "numeric_bound_pg_ml": value,
        "status": status,
    }


def classify_phenotype(evidence):
    a = bool(evidence.get("a_hf_anchor"))
    b = bool(evidence.get("b_decompensation"))
    c_nt = bool(evidence.get("c_ntprobnp_rule_in"))
    c_echo = bool(evidence.get("c_echo_abnormal"))
    c_iv = bool(evidence.get("c_iv_loop_order_proxy"))
    objective = c_nt or c_echo
    any_c = objective or c_iv
    main = a and b and any_c
    strict = a and b and objective
    if objective and c_iv:
        c_type = "objective_C_plus_treatment"
    elif objective:
        c_type = "objective_C"
    elif c_iv:
        c_type = "treatment_proxy_only_C"
    else:
        c_type = "C_not_supported"

    if main:
        label = "algorithmic_rule_supported"
    elif evidence.get("old_pre_review_label") == "unknown":
        label = "algorithmic_unknown"
    else:
        label = "algorithmic_rule_not_supported"

    alternative = bool(evidence.get("alternative_mentioned"))
    clinical_priority = alternative or c_type == "treatment_proxy_only_C" or label == "algorithmic_unknown"
    reasons = []
    if alternative:
        reasons.append("alternative_explanation_present")
    if c_type == "treatment_proxy_only_C":
        reasons.append("treatment_proxy_only_C")
    if label == "algorithmic_unknown":
        reasons.append("uncertain_or_missing_anchor")
    return {
        "main_rule_supported": main,
        "strict_objective_rule_supported": strict,
        "c_support_type": c_type,
        "algorithmic_label": label,
        "clinical_review_priority": clinical_priority,
        "clinical_review_priority_reason": "|".join(reasons) if reasons else "routine_sampling",
    }


def compact(values, limit=3):
    output = []
    for value in values:
        value = str(value or "").strip()
        if value and value not in output:
            output.append(value)
        if len(output) >= limit:
            break
    return " || ".join(output)


def deterministic_rank(visit_id: str):
    return hashlib.sha256(f"{SAMPLING_SEED}|{visit_id}".encode("utf-8")).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pheno_rows = read_csv(PHENO)
    master_rows = read_csv(MASTER)
    bnp_rows = read_csv(BNP)
    order_rows = read_csv(ORDERS)
    time_evidence = read_csv(TIME_EVIDENCE)
    g2_rows = read_csv(G2)

    pheno = {row["visit_id"]: row for row in pheno_rows}
    master = {row["visit_id"]: row for row in master_rows}
    g2 = {row["visit_id"]: row for row in g2_rows}
    if not (len(pheno) == len(g2) == 8385):
        raise ValueError(f"expected 8385 rows in phenotype and G2 inputs; got {len(pheno)} and {len(g2)}")

    bnp_by_visit = defaultdict(list)
    bnp_audit = []
    for row in bnp_rows:
        if row.get("window") != "pre12":
            continue
        visit_id = row["visit_id"]
        age = master.get(visit_id, {}).get("age_at_encounter") or master.get(visit_id, {}).get("age_structured")
        result = ntprobnp_rule_in(age, row.get("raw_result"))
        audit = {
            "patient_id": row.get("patient_id", ""),
            "visit_id": visit_id,
            "age": age or "",
            "analyte": row.get("analyte", ""),
            "raw_result": row.get("raw_result", ""),
            "qualifier": result["qualifier"],
            "numeric_bound_pg_ml": "" if result["numeric_bound_pg_ml"] is None else result["numeric_bound_pg_ml"],
            "threshold_pg_ml": "" if result["threshold_pg_ml"] is None else result["threshold_pg_ml"],
            "rule_in_status": result["status"],
            "unit_contract": "pg/mL_user_confirmed_source_unit_not_exported",
            "report_time": row.get("report_time", ""),
            "time_basis": row.get("time_basis", ""),
            "source_ref": f"{row.get('source_file', '')}#row={row.get('source_row', '')}",
        }
        bnp_audit.append(audit)
        bnp_by_visit[visit_id].append(audit)

    iv_by_visit = defaultdict(list)
    for row in order_rows:
        if (
            row.get("drug_group") == "iv_loop"
            and is_true(row.get("valid_order_flag"))
            and is_true(row.get("pre_T12_proxy_flag"))
        ):
            iv_by_visit[row["visit_id"]].append(row)

    evidence_by_visit_domain = defaultdict(lambda: defaultdict(list))
    for row in time_evidence:
        if row.get("assertion") not in {"affirmed", "measured", "available", "order_proxy"}:
            continue
        evidence_by_visit_domain[row["visit_id"]][row["domain"]].append(row)

    ledger = []
    for visit_id, old in sorted(pheno.items()):
        m = master[visit_id]
        timeline = g2[visit_id]
        nt_rows = bnp_by_visit.get(visit_id, [])
        nt_rule_in = any(row["rule_in_status"] == "rule_in" for row in nt_rows)
        iv_rows = iv_by_visit.get(visit_id, [])

        a = is_true(old.get("hf_anchor_affirmed"))
        b_congestion = is_true(old.get("congestion_affirmed"))
        b_symptom = is_true(old.get("symptom_affirmed"))
        b = b_congestion or b_symptom
        echo_abnormal = is_true(old.get("echo_abnormal_rule_support"))
        alt = is_true(old.get("alternative_mentioned"))
        classification = classify_phenotype({
            "a_hf_anchor": a,
            "b_decompensation": b,
            "c_ntprobnp_rule_in": nt_rule_in,
            "c_echo_abnormal": echo_abnormal,
            "c_iv_loop_order_proxy": bool(iv_rows),
            "old_pre_review_label": old.get("phenotype_tier_pre_review", ""),
            "alternative_mentioned": alt,
        })

        main = classification["main_rule_supported"]
        strict = classification["strict_objective_rule_supported"]
        strict_time = is_true(timeline.get("strict_t12_eligible_flag"))
        broad_time = is_true(timeline.get("broad_t12_eligible_flag"))

        if main and strict:
            review_stratum = "main_supported_objective_C"
        elif main:
            review_stratum = "main_supported_treatment_only_C"
        elif classification["algorithmic_label"] == "algorithmic_unknown":
            review_stratum = "algorithmic_unknown"
        elif a and b:
            review_stratum = "near_boundary_A_B_without_C"
        else:
            review_stratum = "rule_not_supported_random"

        domains = evidence_by_visit_domain.get(visit_id, {})
        a_ev = domains.get("hf", [])
        b_ev = domains.get("congestion", []) + domains.get("symptom", [])
        echo_ev = domains.get("echo_abnormal", [])
        alt_ev = domains.get("alternative", [])
        nt_rule_rows = [row for row in nt_rows if row["rule_in_status"] == "rule_in"]
        nt_rule_rows.sort(key=lambda row: (float(row["numeric_bound_pg_ml"] or 0), row["report_time"]), reverse=True)

        ledger.append({
            "patient_id": old.get("patient_id", ""),
            "sex": old.get("sex", ""),
            "visit_id": visit_id,
            "age": m.get("age_at_encounter") or m.get("age_structured") or "",
            "t0_time": old.get("t0_time", ""),
            "old_pre_review_label": old.get("phenotype_tier_pre_review", ""),
            "algorithmic_label_v1": classification["algorithmic_label"],
            "main_rule_supported_flag": int(main),
            "strict_objective_rule_supported_flag": int(strict),
            "c_support_type": classification["c_support_type"],
            "a_hf_anchor_flag": int(a),
            "b_decompensation_flag": int(b),
            "b_congestion_flag": int(b_congestion),
            "b_symptom_flag": int(b_symptom),
            "c_ntprobnp_rule_in_flag": int(nt_rule_in),
            "c_ntprobnp_pre12_measured_flag": int(bool(nt_rows)),
            "c_ntprobnp_threshold_pg_ml": ntprobnp_threshold(m.get("age_at_encounter") or m.get("age_structured")) or "",
            "c_ntprobnp_rule_in_summary": compact([
                f"{row['qualifier']}{row['numeric_bound_pg_ml']}@{row['report_time']}"
                for row in nt_rule_rows
            ]),
            "c_ntprobnp_source_refs": compact([row["source_ref"] for row in nt_rule_rows]),
            "c_echo_abnormal_flag": int(echo_abnormal),
            "c_echo_result_available_flag": int(is_true(old.get("echo_result_available"))),
            "c_iv_loop_order_proxy_flag": int(bool(iv_rows)),
            "c_iv_loop_order_summary": compact([
                f"{row.get('medication', '')}|{row.get('route', '')}|{row.get('start_time', '')}"
                for row in iv_rows
            ]),
            "c_iv_loop_source_refs": compact([
                f"{row.get('source_file', '')}#row={row.get('source_row', '')}" for row in iv_rows
            ]),
            "aux_management_text_flag": int(is_true(old.get("management_proxy"))),
            "alternative_mentioned_flag": int(alt),
            "clinical_review_priority_flag": int(classification["clinical_review_priority"]),
            "clinical_review_priority_reason": classification["clinical_review_priority_reason"],
            "review_stratum": review_stratum,
            "strict_t12_time_eligible_flag": int(strict_time),
            "broad_t12_time_eligible_flag": int(broad_time),
            "main_strict_t12_riskset_flag": int(main and strict_time),
            "main_broad_t12_riskset_flag": int(main and broad_time),
            "strict_objective_t12_riskset_flag": int(strict and strict_time),
            "calendar_2024_incomplete_flag": timeline.get("calendar_2024_incomplete_flag", "0"),
            "a_source_refs": compact([f"{row.get('source_file', '')}#row={row.get('source_row', '')}" for row in a_ev]),
            "a_evidence_excerpt": compact([row.get("excerpt", "")[:180] for row in a_ev], limit=2),
            "b_source_refs": compact([f"{row.get('source_file', '')}#row={row.get('source_row', '')}" for row in b_ev]),
            "b_evidence_excerpt": compact([row.get("excerpt", "")[:180] for row in b_ev], limit=2),
            "echo_source_refs": compact([f"{row.get('source_file', '')}#row={row.get('source_row', '')}" for row in echo_ev]),
            "alternative_source_refs": compact([f"{row.get('source_file', '')}#row={row.get('source_row', '')}" for row in alt_ev]),
            "algorithmic_label_is_clinical_confirmation": 0,
            "interpretation": "algorithmic phenotype ledger; clinical calibration pending",
        })

    write_csv(OUT / "dhf_abc_evidence_ledger_v1.csv", ledger, list(ledger[0]))
    write_csv(
        OUT / "ntprobnp_rule_in_audit.csv",
        bnp_audit,
        list(bnp_audit[0]) if bnp_audit else [
            "patient_id", "visit_id", "age", "analyte", "raw_result", "qualifier",
            "numeric_bound_pg_ml", "threshold_pg_ml", "rule_in_status", "unit_contract",
            "report_time", "time_basis", "source_ref",
        ],
    )

    flow_metrics = [
        ("source_echo_assessed_adult_icu_candidates", len(ledger)),
        ("A_hf_anchor_supported", sum(row["a_hf_anchor_flag"] for row in ledger)),
        ("B_decompensation_supported", sum(row["b_decompensation_flag"] for row in ledger)),
        ("C_ntprobnp_rule_in", sum(row["c_ntprobnp_rule_in_flag"] for row in ledger)),
        ("C_echo_abnormal", sum(row["c_echo_abnormal_flag"] for row in ledger)),
        ("C_iv_loop_order_proxy", sum(row["c_iv_loop_order_proxy_flag"] for row in ledger)),
        ("main_algorithmic_rule_supported", sum(row["main_rule_supported_flag"] for row in ledger)),
        ("strict_objective_rule_supported", sum(row["strict_objective_rule_supported_flag"] for row in ledger)),
        ("main_strict_T12_riskset", sum(row["main_strict_t12_riskset_flag"] for row in ledger)),
        ("main_broad_T12_sensitivity_riskset", sum(row["main_broad_t12_riskset_flag"] for row in ledger)),
        ("strict_objective_T12_riskset", sum(row["strict_objective_t12_riskset_flag"] for row in ledger)),
    ]
    flow = [
        {
            "stage": name,
            "n": count,
            "status": "algorithmic_not_clinical_gold_standard",
        }
        for name, count in flow_metrics
    ]
    write_csv(OUT / "phenotype_flow_counts.csv", flow, ["stage", "n", "status"])

    change_counts = Counter((row["old_pre_review_label"], row["algorithmic_label_v1"]) for row in ledger)
    changes = [
        {"old_pre_review_label": old, "algorithmic_label_v1": new, "n": count}
        for (old, new), count in sorted(change_counts.items())
    ]
    write_csv(OUT / "phenotype_label_change_matrix.csv", changes, ["old_pre_review_label", "algorithmic_label_v1", "n"])

    review_rows = []
    sampled_counts = {}
    for stratum, target in REVIEW_TARGETS.items():
        candidates = [row for row in ledger if row["review_stratum"] == stratum]
        candidates.sort(key=lambda row: deterministic_rank(row["visit_id"]))
        selected = candidates[: min(target, len(candidates))]
        sampled_counts[stratum] = {
            "available_n": len(candidates),
            "target_n": target,
            "sampled_n": len(selected),
        }
        for row in selected:
            review_rows.append({
                "sample_stratum": stratum,
                "sampling_rank_hash": deterministic_rank(row["visit_id"]),
                "patient_id": row["patient_id"],
                "sex": row["sex"],
                "visit_id": row["visit_id"],
                "age": row["age"],
                "t0_time": row["t0_time"],
                "algorithmic_label_v1": row["algorithmic_label_v1"],
                "c_support_type": row["c_support_type"],
                "a_hf_anchor_flag": row["a_hf_anchor_flag"],
                "b_decompensation_flag": row["b_decompensation_flag"],
                "c_ntprobnp_rule_in_flag": row["c_ntprobnp_rule_in_flag"],
                "c_echo_abnormal_flag": row["c_echo_abnormal_flag"],
                "c_iv_loop_order_proxy_flag": row["c_iv_loop_order_proxy_flag"],
                "alternative_mentioned_flag": row["alternative_mentioned_flag"],
                "a_source_refs": row["a_source_refs"],
                "a_evidence_excerpt": row["a_evidence_excerpt"],
                "b_source_refs": row["b_source_refs"],
                "b_evidence_excerpt": row["b_evidence_excerpt"],
                "c_ntprobnp_rule_in_summary": row["c_ntprobnp_rule_in_summary"],
                "c_ntprobnp_source_refs": row["c_ntprobnp_source_refs"],
                "echo_source_refs": row["echo_source_refs"],
                "c_iv_loop_order_summary": row["c_iv_loop_order_summary"],
                "c_iv_loop_source_refs": row["c_iv_loop_source_refs"],
                "alternative_source_refs": row["alternative_source_refs"],
                "reviewer_dhf_label": "",
                "reviewer_A_domain": "",
                "reviewer_B_domain": "",
                "reviewer_C_domain": "",
                "reviewer_evidence_sufficient": "",
                "reviewer_comments": "",
                "second_reviewer_label": "",
                "adjudicated_label": "",
            })
    review_rows.sort(key=lambda row: (row["sample_stratum"], row["sampling_rank_hash"]))
    write_csv(OUT / "clinical_review_sample_v1.csv", review_rows, list(review_rows[0]))

    sampling_manifest = {
        "run_id": RUN_ID,
        "seed": SAMPLING_SEED,
        "selection_uses_outcomes": False,
        "ranking": "sha256(seed|visit_id)",
        "strata": sampled_counts,
        "total_sampled_n": len(review_rows),
        "review_status": "prepared_not_completed",
    }
    (OUT / "review_sampling_manifest.json").write_text(
        json.dumps(sampling_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inputs = [PHENO, TIME_EVIDENCE, BNP, ORDERS, MASTER, G2, CONTRACT, SAP]
    snapshot = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": [{"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size} for path in inputs],
    }
    (OUT / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    qc = {
        "run_id": RUN_ID,
        "status": "PASS_ALGORITHMIC_RULE_FROZEN_CLINICAL_CALIBRATION_PENDING",
        "source_rows": len(ledger),
        "unique_patient_ids": len({row["patient_id"] for row in ledger}),
        "unique_visit_ids": len({row["visit_id"] for row in ledger}),
        "old_rule_supported_n": sum(row["old_pre_review_label"] in {"probable_dhf", "confirmed_dhf"} for row in ledger),
        "main_algorithmic_rule_supported_n": sum(row["main_rule_supported_flag"] for row in ledger),
        "strict_objective_rule_supported_n": sum(row["strict_objective_rule_supported_flag"] for row in ledger),
        "main_strict_T12_riskset_n": sum(row["main_strict_t12_riskset_flag"] for row in ledger),
        "main_broad_T12_sensitivity_riskset_n": sum(row["main_broad_t12_riskset_flag"] for row in ledger),
        "strict_objective_T12_riskset_n": sum(row["strict_objective_t12_riskset_flag"] for row in ledger),
        "ntprobnp_pre12_measured_visit_n": sum(row["c_ntprobnp_pre12_measured_flag"] for row in ledger),
        "ntprobnp_rule_in_visit_n": sum(row["c_ntprobnp_rule_in_flag"] for row in ledger),
        "iv_loop_order_proxy_visit_n": sum(row["c_iv_loop_order_proxy_flag"] for row in ledger),
        "structured_echo_abnormal_visit_n": sum(row["c_echo_abnormal_flag"] for row in ledger),
        "clinical_review_sample_n": len(review_rows),
        "clinical_review_completed": False,
        "clinical_gold_standard": False,
        "formal_outcomes_generated": False,
        "model_run": False,
        "raw_data_modified": False,
        "next_gate": "G4_endpoint_observability_and_three_state_reconstruction_can_run; final clinical phenotype claims remain pending review",
    }
    (OUT / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "run_id": RUN_ID,
        "status": qc["status"],
        "old_rule_supported_n": qc["old_rule_supported_n"],
        "main_algorithmic_rule_supported_n": qc["main_algorithmic_rule_supported_n"],
        "strict_objective_rule_supported_n": qc["strict_objective_rule_supported_n"],
        "main_strict_T12_riskset_n": qc["main_strict_T12_riskset_n"],
        "main_broad_T12_sensitivity_riskset_n": qc["main_broad_T12_sensitivity_riskset_n"],
        "clinical_review_sample_n": qc["clinical_review_sample_n"],
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
