#!/usr/bin/env python3
"""Prepare a 50-stay clinical review sheet from the internal echo QC sample.

The sheet contains prefilled source fields and blank reviewer fields. It does
not alter raw exports or assign final DHF/outcome labels automatically.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
SOURCE = BASE / "internal_echo_sample_qc_20260912.csv"
OUTPUT = BASE / "internal_gate3_manual_review_50_20260913.csv"


REVIEW_FIELDS = [
    "reviewer_id",
    "t0_time_final",
    "t0_source_final",
    "t0_discrepancy_reason",
    "echo_completed_final",
    "echo_result_available_final",
    "echo_abnormal_support_final",
    "echo_abnormal_domains",
    "echo_report_time_semantics",
    "echo_report_validity",
    "hf_anchor_support_final",
    "decompensation_domain_final",
    "management_evidence_final",
    "dhf_tier_final",
    "icu_out_time_final",
    "icu_out_source_final",
    "outcome_status_final",
    "event_time_final",
    "event_component_final",
    "competing_time_final",
    "censor_time_final",
    "review_comments",
]


def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    if len(source_rows) != 50:
        raise ValueError(f"Expected 50 source rows, found {len(source_rows)}")

    rows = []
    for i, row in enumerate(source_rows, start=1):
        out = {
            "review_id": f"G3-{i:03d}",
            "patient_id": row.get("patient_id", ""),
            "sex": row.get("sex", ""),
            "visit_id": row.get("visit_id", ""),
            "t0_candidate": row.get("t0_candidate", ""),
            "t0_source_candidate": row.get("t0_source", ""),
            "t12_candidate": row.get("t12_candidate", ""),
            "report_time": row.get("report_time", ""),
            "audit_time": row.get("audit_time", ""),
            "report_in_window": row.get("report_in_window", ""),
            "project_name": row.get("project_name", ""),
            "check_type": row.get("check_type", ""),
            "finding": row.get("finding", ""),
            "conclusion": row.get("conclusion", ""),
            "database_abnormal_field": row.get("database_abnormal_field", ""),
            "result_available_draft": row.get("result_available", ""),
            "audit_window_abnormal_support_draft": row.get(
                "audit_window_abnormal_support_draft_flag", ""
            ),
        }
        out.update({field: "" for field in REVIEW_FIELDS})
        rows.append(out)

    fields = [
        "review_id",
        "patient_id",
        "sex",
        "visit_id",
        "t0_candidate",
        "t0_source_candidate",
        "t12_candidate",
        "report_time",
        "audit_time",
        "report_in_window",
        "project_name",
        "check_type",
        "finding",
        "conclusion",
        "database_abnormal_field",
        "result_available_draft",
        "audit_window_abnormal_support_draft",
        *REVIEW_FIELDS,
    ]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
