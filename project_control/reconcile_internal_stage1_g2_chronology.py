#!/usr/bin/env python3
"""Reconcile the internal DHF Study-1 index-ICU chronology (G2).

The corrected 20260916 timeline is preserved as the broad working layer. This
script independently derives a fail-closed strict T12 layer from explicit
entry/exit/death/discharge times. Later death without a documented ICU exit is
kept as an inferred sensitivity layer, not promoted to direct ICU presence.
No phenotype or outcome model is run.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_internal_stage1_g2_chronology"
OUT = CONTROL / "runs" / RUN_ID

TIME_AUDIT = CONTROL / "internal_validation/20260916_semantic_corrected/encounter_icu_time_audit.csv"
EPISODES = CONTROL / "internal_validation/20260916_semantic_corrected/icu_episode_candidates.csv"
TIME_QC = CONTROL / "internal_validation/20260916_semantic_corrected/qc.json"
L1_CANDIDATES = CONTROL / "runs/20260923_internal_stage1_l1/internal_stage1_cohort_candidate.csv"
G1_SCOPE = CONTROL / "runs/20260923_internal_stage1_g1_scope/scope_contract.json"
DESIGN = CONTROL / "designs/INTERNAL_DHF_STAGE1_STUDY_DESIGN_V1_20260923.md"
SAP = CONTROL / "STATISTICAL_ANALYSIS_PLAN_INTERNAL_DHF_STUDY1_V1.md"


def read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_dt(value: str):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def fmt_dt(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_true(value):
    return str(value).strip().lower() in {"1", "true", "yes"}


def classify_t0_source(source: str):
    if source in {"explicit_document_event", "nursing_entry_record_time", "user_confirmed_document_time"}:
        return "direct"
    if source in {
        "icu_discharge_note_admission_field",
        "AI_review_explicit_retrospective_transfer",
        "AI_review_corroborated_discharge_admission",
    }:
        return "retrospective_explicit"
    if source == "directional_document_transfer":
        return "directional"
    if source == "AI_review_contextual_admission":
        return "contextual"
    if source == "structured_proxy":
        return "proxy"
    return "unknown_source_quality"


def derive_t12_state(row):
    t0 = parse_dt(row.get("t0_time", ""))
    t12 = parse_dt(row.get("t12_time", "")) or (t0 + timedelta(hours=12) if t0 else None)
    out = parse_dt(row.get("index_icu_outtime", ""))
    death = parse_dt(row.get("hospital_death_time", ""))
    discharge = parse_dt(row.get("hospital_discharge_time", ""))
    current = row.get("landmark_presence_status", "unknown") or "unknown"
    flags = row.get("time_review_flags", "")

    result = {
        "strict_t12_state": "unknown_missing_t0",
        "broad_t12_state": "unknown",
        "strict_riskset_status": "not_eligible_missing_t0",
        "broad_riskset_status": "not_eligible_or_unknown",
        "t12_evidence_tier": "unknown",
        "chronology_conflict": "",
    }
    if not t0 or not t12:
        return result

    valid_out = out if out and out >= t0 else None
    valid_death = death if death and death >= t0 else None
    valid_discharge = discharge if discharge and discharge >= t0 else None

    if valid_death and valid_death <= t12:
        result.update({
            "strict_t12_state": "died_by_T12",
            "broad_t12_state": "died_by_T12",
            "strict_riskset_status": "not_eligible_pre_t12_death",
            "broad_riskset_status": "not_eligible_pre_t12_death",
            "t12_evidence_tier": "direct_death_time",
        })
        return result

    if valid_out and valid_out <= t12:
        result.update({
            "strict_t12_state": "left_index_icu_by_T12",
            "broad_t12_state": "left_index_icu_by_T12",
            "strict_riskset_status": "not_eligible_pre_t12_icu_exit",
            "broad_riskset_status": "not_eligible_pre_t12_icu_exit",
            "t12_evidence_tier": "direct_icu_exit_time",
        })
        return result

    if valid_discharge and valid_discharge <= t12:
        if valid_out and valid_out > t12:
            result.update({
                "strict_t12_state": "unknown_conflicting_exit_evidence",
                "broad_t12_state": current,
                "strict_riskset_status": "not_eligible_time_conflict",
                "broad_riskset_status": "existing_working_layer_requires_sensitivity",
                "t12_evidence_tier": "conflicting_hospital_and_icu_exit",
                "chronology_conflict": "hospital_discharge_before_T12_but_ICU_exit_after_T12",
            })
        else:
            result.update({
                "strict_t12_state": "left_index_icu_by_T12",
                "broad_t12_state": current if current != "unknown" else "left_index_icu_by_T12",
                "strict_riskset_status": "not_eligible_pre_t12_hospital_exit",
                "broad_riskset_status": "not_eligible_pre_t12_hospital_exit",
                "t12_evidence_tier": "direct_hospital_exit_time",
            })
        return result

    if valid_out and valid_out > t12:
        result.update({
            "strict_t12_state": "present_at_T12_direct",
            "broad_t12_state": "present_at_T12_direct",
            "strict_riskset_status": "eligible",
            "broad_riskset_status": "eligible",
            "t12_evidence_tier": "direct_icu_exit_after_T12",
        })
        return result

    if not valid_out and valid_death and valid_death > t12 and current == "present_at_T12_by_document_timeline":
        result.update({
            "strict_t12_state": "unknown_no_direct_icu_presence",
            "broad_t12_state": "present_at_T12_inferred_from_later_death",
            "strict_riskset_status": "exclude_strict_include_broad_sensitivity",
            "broad_riskset_status": "eligible_inferred_sensitivity",
            "t12_evidence_tier": "later_death_without_documented_icu_exit",
        })
        return result

    if current == "present_at_T12_by_document_timeline":
        result.update({
            "strict_t12_state": "unknown_no_direct_icu_presence",
            "broad_t12_state": "present_at_T12_existing_document_timeline",
            "strict_riskset_status": "exclude_strict_include_broad_sensitivity",
            "broad_riskset_status": "eligible_existing_document_timeline",
            "t12_evidence_tier": "existing_timeline_without_direct_exit_proof",
        })
        return result

    result.update({
        "strict_t12_state": "unknown_no_direct_icu_presence",
        "broad_t12_state": current,
        "strict_riskset_status": "not_eligible_unknown",
        "broad_riskset_status": "not_eligible_unknown",
        "t12_evidence_tier": "no_direct_icu_presence_at_T12",
    })
    return result


def build_rows(time_rows, candidate_rows):
    candidate_by_visit = {row["visit_id"]: row for row in candidate_rows}
    if len(candidate_by_visit) != len(candidate_rows):
        raise ValueError("candidate visit_id must be unique")

    output = []
    for time_row in time_rows:
        visit_id = time_row["visit_id"]
        candidate = candidate_by_visit.get(visit_id)
        if candidate is None:
            raise ValueError(f"time audit visit missing from L1 candidates: {visit_id}")
        derived = derive_t12_state(time_row)
        rule_supported = is_true(candidate.get("candidate_rule_support_flag"))
        current_broad_riskset = is_true(candidate.get("candidate_riskset_flag"))
        strict_eligible = derived["strict_riskset_status"] == "eligible"
        inferred_eligible = derived["broad_riskset_status"] in {
            "eligible",
            "eligible_inferred_sensitivity",
            "eligible_existing_document_timeline",
        }
        output.append({
            "patient_id": time_row.get("patient_id", ""),
            "sex": time_row.get("sex", ""),
            "visit_id": visit_id,
            "episode_id": time_row.get("episode_id", ""),
            "t0_time": time_row.get("t0_time", ""),
            "t0_source": time_row.get("t0_source", ""),
            "t0_source_quality": classify_t0_source(time_row.get("t0_source", "")),
            "t12_time": time_row.get("t12_time", ""),
            "t60_time": time_row.get("t60_time", ""),
            "entry_clusters": time_row.get("entry_clusters", ""),
            "readmission_with_exit_flag": time_row.get("readmission_with_exit_flag", ""),
            "index_icu_outtime": time_row.get("index_icu_outtime", ""),
            "icu_out_source": time_row.get("icu_out_source", ""),
            "hospital_death_time": time_row.get("hospital_death_time", ""),
            "hospital_discharge_time": time_row.get("hospital_discharge_time", ""),
            "time_review_flags": time_row.get("time_review_flags", ""),
            "corrected_working_landmark_status": time_row.get("landmark_presence_status", ""),
            "l1_landmark_status": candidate.get("landmark_presence_status", ""),
            "l1_candidate_riskset_flag": int(current_broad_riskset),
            "rule_supported_working_flag": int(rule_supported),
            **derived,
            "strict_t12_eligible_flag": int(strict_eligible),
            "broad_t12_eligible_flag": int(inferred_eligible),
            "strict_rule_supported_riskset_flag": int(rule_supported and strict_eligible),
            "broad_rule_supported_riskset_flag": int(rule_supported and inferred_eligible),
            "calendar_2024_incomplete_flag": int(time_row.get("t0_time", "").startswith("2024-")),
            "interpretation": "chronology layer only; DHF phenotype and outcomes remain unfrozen",
        })

    if set(candidate_by_visit) != {row["visit_id"] for row in time_rows}:
        missing = set(candidate_by_visit) - {row["visit_id"] for row in time_rows}
        raise ValueError(f"L1 candidate visits missing from corrected time audit: {len(missing)}")
    return output


def write_outputs(rows, input_paths):
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    write_csv(OUT / "episode_chronology_reconciled.csv", rows, fields)

    summary = []
    for field in [
        "t0_source_quality",
        "corrected_working_landmark_status",
        "strict_t12_state",
        "broad_t12_state",
        "strict_riskset_status",
        "chronology_conflict",
    ]:
        counts = Counter(row[field] or "none" for row in rows)
        for value, count in sorted(counts.items()):
            summary.append({"domain": field, "value": value, "n": count})
    write_csv(OUT / "chronology_summary.csv", summary, ["domain", "value", "n"])

    t0_summary = []
    counts = Counter((row["t0_source"], row["t0_source_quality"]) for row in rows)
    for (source, quality), count in sorted(counts.items()):
        t0_summary.append({"t0_source": source, "t0_source_quality": quality, "n": count})
    write_csv(OUT / "t0_source_quality.csv", t0_summary, ["t0_source", "t0_source_quality", "n"])

    transitions = []
    counts = Counter((row["corrected_working_landmark_status"], row["strict_t12_state"]) for row in rows)
    for (working, strict), count in sorted(counts.items()):
        transitions.append({"corrected_working_landmark_status": working, "strict_t12_state": strict, "n": count})
    write_csv(
        OUT / "t12_state_transition_matrix.csv",
        transitions,
        ["corrected_working_landmark_status", "strict_t12_state", "n"],
    )

    riskset_rows = [
        {
            "riskset_layer": "historical_L1_working",
            "rule_supported_n": sum(row["l1_candidate_riskset_flag"] for row in rows),
            "definition": "corrected working document timeline; historical 626 layer",
            "status": "broad_working_not_final",
        },
        {
            "riskset_layer": "G2_broad_sensitivity",
            "rule_supported_n": sum(row["broad_rule_supported_riskset_flag"] for row in rows),
            "definition": "direct presence plus existing/inferred document timeline",
            "status": "sensitivity_layer",
        },
        {
            "riskset_layer": "G2_strict_direct",
            "rule_supported_n": sum(row["strict_rule_supported_riskset_flag"] for row in rows),
            "definition": "direct ICU exit after T12 proves presence; fail-closed otherwise",
            "status": "recommended_chronology_main_layer_pending_G3_phenotype",
        },
    ]
    write_csv(
        OUT / "strict_vs_broad_riskset_counts.csv",
        riskset_rows,
        ["riskset_layer", "rule_supported_n", "definition", "status"],
    )

    snapshot = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": [
            {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in input_paths
        ],
    }
    (OUT / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    qc = {
        "run_id": RUN_ID,
        "status": "PASS_CHRONOLOGY_STRICT_LAYER_WITH_INFERRED_SENSITIVITY",
        "rows": len(rows),
        "unique_patient_ids": len({row["patient_id"] for row in rows}),
        "unique_visit_ids": len({row["visit_id"] for row in rows}),
        "all_t0_nonmissing": all(row["t0_time"] for row in rows),
        "l1_matches_corrected_working_landmark": all(
            row["l1_landmark_status"] == row["corrected_working_landmark_status"] for row in rows
        ),
        "multiple_entry_cluster_rows": sum(int(row["entry_clusters"] or 0) > 1 for row in rows),
        "readmission_with_exit_rows": sum(is_true(row["readmission_with_exit_flag"]) for row in rows),
        "missing_index_icu_outtime_rows": sum(not row["index_icu_outtime"] for row in rows),
        "historical_rule_supported_riskset_n": sum(row["l1_candidate_riskset_flag"] for row in rows),
        "broad_rule_supported_riskset_n": sum(row["broad_rule_supported_riskset_flag"] for row in rows),
        "strict_direct_rule_supported_riskset_n": sum(row["strict_rule_supported_riskset_flag"] for row in rows),
        "inferred_later_death_rule_supported_n": sum(
            row["rule_supported_working_flag"]
            and row["t12_evidence_tier"] == "later_death_without_documented_icu_exit"
            for row in rows
        ),
        "formal_dhf_phenotype_generated": False,
        "formal_outcome_generated": False,
        "model_run": False,
        "raw_data_modified": False,
        "next_gate": "G3_A_B_C_evidence_ledger_and_review_package",
    }
    (OUT / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    return qc


def main():
    time_rows = read_csv(TIME_AUDIT)
    candidate_rows = read_csv(L1_CANDIDATES)
    rows = build_rows(time_rows, candidate_rows)
    qc = write_outputs(rows, [TIME_AUDIT, EPISODES, TIME_QC, L1_CANDIDATES, G1_SCOPE, DESIGN, SAP])
    print(json.dumps({
        "run_id": RUN_ID,
        "status": qc["status"],
        "rows": qc["rows"],
        "historical_rule_supported_riskset_n": qc["historical_rule_supported_riskset_n"],
        "broad_rule_supported_riskset_n": qc["broad_rule_supported_riskset_n"],
        "strict_direct_rule_supported_riskset_n": qc["strict_direct_rule_supported_riskset_n"],
        "inferred_later_death_rule_supported_n": qc["inferred_later_death_rule_supported_n"],
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
