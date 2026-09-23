#!/usr/bin/env python3
"""G1 scope and calendar-completeness audit for internal DHF Study 1.

This gate locks the inferential denominator and known incomplete calendar
periods. It emits aggregate metadata only and does not derive a phenotype,
outcome, predictor effect, or model.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260923_internal_stage1_g1_scope"
OUT = CONTROL / "runs" / RUN_ID

L1_CANDIDATES = CONTROL / "runs/20260923_internal_stage1_l1/internal_stage1_cohort_candidate.csv"
L0_YEARS = CONTROL / "runs/20260923_internal_stage1_l0/calendar_year_counts.csv"
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


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_true(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def classify_calendar_year(year: str, first_year: str, last_year: str):
    if year == "2024":
        return {
            "completeness_status": "incomplete_calendar_period",
            "annual_trend_eligible": False,
            "interpretation": "known data discontinuity; do not interpret low count as true clinical decline",
        }
    if year and year in {first_year, last_year}:
        return {
            "completeness_status": "partial_observation_boundary",
            "annual_trend_eligible": False,
            "interpretation": "boundary year in observed T0 span; not comparable with a complete natural year",
        }
    return {
        "completeness_status": "completeness_not_independently_proven",
        "annual_trend_eligible": False,
        "interpretation": "candidate count observed, but independent source-completeness proof is unavailable",
    }


def build_scope_contract(candidate_rows, year_counts, first_year: str, last_year: str):
    candidate_n = len(candidate_rows)
    rule_supported = [row for row in candidate_rows if is_true(row.get("candidate_rule_support_flag"))]
    riskset = [row for row in candidate_rows if is_true(row.get("candidate_riskset_flag"))]
    echo_available = [row for row in candidate_rows if is_true(row.get("bedside_echo_report_available"))]
    rule_echo = [row for row in rule_supported if is_true(row.get("bedside_echo_report_available"))]
    risk_echo = [row for row in riskset if is_true(row.get("bedside_echo_report_available"))]

    calendar_status = []
    for year in sorted(year_counts):
        status = classify_calendar_year(str(year), str(first_year), str(last_year))
        calendar_status.append({
            "calendar_year": str(year),
            "candidate_episode_n": int(year_counts[year]),
            **status,
        })

    return {
        "run_id": RUN_ID,
        "scope_denominator": "echo_assessed_adult_icu_candidate_frame",
        "scope_statement": "adult ICU patients present in the bedside-echo-selected source frame",
        "institutional_workflow_assumption": "ICU acute decompensated heart failure patients routinely receive bedside echocardiography",
        "assumption_is_independently_verifiable_in_current_frame": False,
        "independent_all_icu_denominator_available": False,
        "can_estimate_all_icu_dhf_prevalence": False,
        "candidate_n": candidate_n,
        "rule_supported_n": len(rule_supported),
        "t12_working_riskset_n": len(riskset),
        "structured_echo_report_available_n": len(echo_available),
        "structured_echo_report_missing_n": candidate_n - len(echo_available),
        "rule_supported_structured_echo_available_n": len(rule_echo),
        "rule_supported_structured_echo_missing_n": len(rule_supported) - len(rule_echo),
        "t12_riskset_structured_echo_available_n": len(risk_echo),
        "t12_riskset_structured_echo_missing_n": len(riskset) - len(risk_echo),
        "echo_interpretation": "structured report observability is not the same as whether an echocardiogram was clinically performed",
        "calendar_status": calendar_status,
        "calendar_trend_allowed": False,
        "include_2024_patient_level_if_observable": True,
        "mandatory_sensitivity_analysis_excluding_2024": True,
        "prohibited_claims": [
            "本研究覆盖全院全部成人ICU患者",
            "当前数据是连续完整五年数据库",
            "2024年病例真实下降",
            "结构化心超报告缺失等同于未实施床旁心超",
            "当前抽样框可用于估计全ICU人群DHF患病率或检出率",
        ],
        "permitted_scope_claim": "本院接受床旁心超的成人ICU候选人群中的算法操作性DHF研究",
        "formal_phenotype_generated": False,
        "formal_outcome_generated": False,
        "model_run": False,
        "raw_data_modified": False,
    }


def rate(numerator: int, denominator: int):
    if denominator == 0:
        return ""
    return round(numerator / denominator, 6)


def write_outputs(out: Path, contract, input_paths):
    out.mkdir(parents=True, exist_ok=True)
    (out / "scope_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_csv(
        out / "calendar_completeness.csv",
        contract["calendar_status"],
        ["calendar_year", "candidate_episode_n", "completeness_status", "annual_trend_eligible", "interpretation"],
    )

    echo_rows = [
        {
            "analysis_layer": "all_candidates",
            "denominator_n": contract["candidate_n"],
            "structured_echo_report_available_n": contract["structured_echo_report_available_n"],
            "structured_echo_report_missing_n": contract["structured_echo_report_missing_n"],
            "structured_echo_report_observed_fraction": rate(contract["structured_echo_report_available_n"], contract["candidate_n"]),
            "interpretation": contract["echo_interpretation"],
        },
        {
            "analysis_layer": "automated_rule_supported_working_layer",
            "denominator_n": contract["rule_supported_n"],
            "structured_echo_report_available_n": contract["rule_supported_structured_echo_available_n"],
            "structured_echo_report_missing_n": contract["rule_supported_structured_echo_missing_n"],
            "structured_echo_report_observed_fraction": rate(contract["rule_supported_structured_echo_available_n"], contract["rule_supported_n"]),
            "interpretation": contract["echo_interpretation"],
        },
        {
            "analysis_layer": "t12_working_riskset",
            "denominator_n": contract["t12_working_riskset_n"],
            "structured_echo_report_available_n": contract["t12_riskset_structured_echo_available_n"],
            "structured_echo_report_missing_n": contract["t12_riskset_structured_echo_missing_n"],
            "structured_echo_report_observed_fraction": rate(contract["t12_riskset_structured_echo_available_n"], contract["t12_working_riskset_n"]),
            "interpretation": contract["echo_interpretation"],
        },
    ]
    write_csv(
        out / "echo_observability.csv",
        echo_rows,
        [
            "analysis_layer",
            "denominator_n",
            "structured_echo_report_available_n",
            "structured_echo_report_missing_n",
            "structured_echo_report_observed_fraction",
            "interpretation",
        ],
    )

    prohibited = [{"prohibited_claim": claim, "status": "not_allowed"} for claim in contract["prohibited_claims"]]
    write_csv(out / "prohibited_interpretations.csv", prohibited, ["prohibited_claim", "status"])

    inputs = []
    for path in input_paths:
        path = Path(path)
        inputs.append({"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    snapshot = {
        "run_id": contract["run_id"],
        "generated_at": datetime.now().astimezone().isoformat(),
        "inputs": inputs,
    }
    (out / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    qc = {
        "run_id": contract["run_id"],
        "status": "PASS_SCOPE_LOCKED_WITH_KNOWN_LIMITATIONS",
        "scope_locked": contract["scope_denominator"] == "echo_assessed_adult_icu_candidate_frame",
        "all_icu_prevalence_claim_allowed": contract["can_estimate_all_icu_dhf_prevalence"],
        "calendar_trend_allowed": contract["calendar_trend_allowed"],
        "year_2024_marked_incomplete": any(
            row["calendar_year"] == "2024" and row["completeness_status"] == "incomplete_calendar_period"
            for row in contract["calendar_status"]
        ),
        "structured_echo_missing_not_treated_as_not_performed": True,
        "formal_phenotype_generated": contract["formal_phenotype_generated"],
        "formal_outcome_generated": contract["formal_outcome_generated"],
        "model_run": contract["model_run"],
        "raw_data_modified": contract["raw_data_modified"],
        "next_gate": "G2_index_ICU_episode_chronology",
    }
    (out / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    candidate_rows = read_csv(L1_CANDIDATES)
    year_rows = read_csv(L0_YEARS)
    year_counts = {row["calendar_year"]: int(row["candidate_episode_rows"]) for row in year_rows}
    years = sorted(year_counts)
    contract = build_scope_contract(
        candidate_rows,
        year_counts,
        years[0] if years else "",
        years[-1] if years else "",
    )
    write_outputs(OUT, contract, [L1_CANDIDATES, L0_YEARS, DESIGN, SAP])
    print(json.dumps({
        "run_id": RUN_ID,
        "status": "PASS_SCOPE_LOCKED_WITH_KNOWN_LIMITATIONS",
        "candidate_n": contract["candidate_n"],
        "rule_supported_n": contract["rule_supported_n"],
        "t12_working_riskset_n": contract["t12_working_riskset_n"],
        "structured_echo_report_available_n": contract["structured_echo_report_available_n"],
        "out": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
