#!/usr/bin/env python3
"""Build the current internal three-tier DHF/echo audit.

The output distinguishes computable echo states from final clinical DHF and
outcome labels that still require data not present in the current export.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
MASTER = BASE / "icu_stay_master_20260912.csv"
ECHO = BASE / "internal_echo_three_state_audit_20260912.csv"
REVIEWED = BASE / "internal_gate3_manual_review_50_20260913_reviewed.csv"
OUT = BASE / "internal_dhf_three_tier_audit_20260913.csv"
SUMMARY = BASE / "internal_dhf_three_tier_audit_qc_20260913.json"


def main() -> None:
    with MASTER.open(encoding="utf-8-sig", newline="") as handle:
        master = {
            (r["sex"], r["visit_id"]): r
            for r in csv.DictReader(handle)
            if r["adult_flag"] == "1" and r["index_adult_icu_flag"] == "1"
        }
    with ECHO.open(encoding="utf-8-sig", newline="") as handle:
        echo = {(r["sex"], r["visit_id"]): r for r in csv.DictReader(handle)}
    reviewed = {}
    if REVIEWED.exists():
        with REVIEWED.open(encoding="utf-8-sig", newline="") as handle:
            reviewed = {(r["sex"], r["visit_id"]): r for r in csv.DictReader(handle)}

    rows = []
    for key, m in sorted(master.items()):
        e = echo.get(key, {})
        window_performed = int(e.get("window_bedside_echo_report_count", 0) or 0) > 0
        window_result = e.get("window_bedside_echo_result_available_flag", "0") == "1"
        window_abnormal_draft = e.get("window_bedside_echo_abnormal_support_draft_flag", "0") == "1"
        rv = reviewed.get(key)
        rows.append(
            {
                "patient_id": m["patient_id"],
                "sex": m["sex"],
                "visit_id": m["visit_id"],
                "adult_index_flag": 1,
                "t0_candidate": m["t0_candidate"],
                "t0_source_candidate": m["t0_candidate_source"],
                "window_bedside_echo_performed_flag": int(window_performed),
                "window_bedside_echo_result_available_flag": int(window_result),
                "window_bedside_echo_abnormal_support_draft_flag": int(window_abnormal_draft),
                "echo_supported_dhf_draft_flag": int(window_performed and window_result and window_abnormal_draft),
                "final_dhf_tier": rv.get("dhf_tier_final", "pending_human_review") if rv else "pending_human_review",
                "hf_anchor_final": rv.get("hf_anchor_support_final", "pending_data_mapping") if rv else "pending_data_mapping",
                "decompensation_domain_final": rv.get("decompensation_domain_final", "pending_data_mapping") if rv else "pending_data_mapping",
                "management_evidence_final": rv.get("management_evidence_final", "pending_data_mapping") if rv else "pending_data_mapping",
                "event_flag": "not_available_in_current_export",
                "competing_flag": "not_available_in_current_export",
                "censor_flag": "not_available_in_current_export",
                "manual_reviewed_flag": int(rv is not None),
                "outcome_status_reviewed": rv.get("outcome_status_final", "") if rv else "",
            }
        )

    def count(field: str) -> int:
        return sum(int(r[field]) for r in rows)

    summary = {
        "generated_at": "2026-09-13",
        "scope": "adult first eligible ICU candidate stay; merged female/male data",
        "raw_data_modified": False,
        "counts": {
            "adult_index_stays": len(rows),
            "window_bedside_echo_performed": count("window_bedside_echo_performed_flag"),
            "window_result_available": count("window_bedside_echo_result_available_flag"),
            "window_abnormal_support_draft": count("window_bedside_echo_abnormal_support_draft_flag"),
            "echo_supported_dhf_draft": count("echo_supported_dhf_draft_flag"),
            "manual_reviewed_cases": count("manual_reviewed_flag"),
            "manual_reviewed_tier_counts": {
                tier: sum(r["manual_reviewed_flag"] and r["final_dhf_tier"] == tier for r in rows)
                for tier in ("multidomain_draft", "echo_supported_draft", "unknown", "not_supported")
            },
            "current_full_table_tier_counts": {
                tier: sum(r["final_dhf_tier"] == tier for r in rows)
                for tier in ("multidomain_draft", "echo_supported_draft", "unknown", "not_supported", "pending_human_review")
            },
            "event": None,
            "competing_alive_icu_discharge": None,
            "administrative_censor": None,
        },
        "by_sex": {
            sex: {
                "adult_index_stays": sum(r["sex"] == sex for r in rows),
                "window_bedside_echo_performed": sum(int(r["window_bedside_echo_performed_flag"]) for r in rows if r["sex"] == sex),
                "window_result_available": sum(int(r["window_bedside_echo_result_available_flag"]) for r in rows if r["sex"] == sex),
                "window_abnormal_support_draft": sum(int(r["window_bedside_echo_abnormal_support_draft_flag"]) for r in rows if r["sex"] == sex),
                "echo_supported_dhf_draft": sum(int(r["echo_supported_dhf_draft_flag"]) for r in rows if r["sex"] == sex),
            }
            for sex in ("女", "男")
        },
        "definitions": {
            "window": "report-time proxy in [T0-24 h, T0+12 h); report time is not confirmed completion time",
            "result_available": "检查所见 or 检查结论 non-empty",
            "abnormal_support_draft": "regex draft only; requires human adjudication",
            "echo_supported_dhf_draft": "window bedside echo performed + result available + abnormal-support draft; not final DHF",
            "manual_overlay": "50 Gate-3 cases were user-adjudicated and overlaid by sex + visit_id; all remaining cases remain pending_human_review",
            "outcomes": "full-cohort event/competing/censor counts are not computable from current exports; reviewed-case ICU disposition is retained in outcome_status_reviewed and is not the prediction event label",
        },
    }
    fields = list(rows[0])
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"audit": str(OUT), "summary": str(SUMMARY), **summary["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
