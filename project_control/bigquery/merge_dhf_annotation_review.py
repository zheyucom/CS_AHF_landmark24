#!/usr/bin/env python3
"""Validate a reviewed draft and export the original annotation-table shape."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_DIR = ROOT / "project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2"
DEFAULT_INPUT = ANNOTATION_DIR / "dhf_radiology_annotation_round1_codex_draft.csv"
DEFAULT_OUTPUT = ANNOTATION_DIR / "dhf_radiology_annotation_round1_completed.csv"

CONGESTION = {"definite_congestion", "possible_congestion", "no_congestion", "indeterminate"}
ALTERNATIVES = {
    "none_apparent",
    "pneumonia_ards",
    "pulmonary_embolism_or_rv_strain",
    "postoperative_or_technical",
    "other",
    "unclear",
}
AVAILABILITY = {"yes", "no", "unknown"}
REPORT_SCOPES = {"chest_radiology", "non_chest_radiology", "mixed_or_unclear", "unknown"}
MODALITIES = {"cxr", "chest_ct", "other_chest", "non_chest", "mixed_or_unclear", "unknown"}
ORIGINAL_COLUMNS = [
    "annotation_id",
    "stay_id",
    "note_id",
    "charttime",
    "storetime",
    "report_text",
    "rule_positive_congestion",
    "rule_uncertainty",
    "rule_negation",
    "reviewer_id",
    "report_scope",
    "modality",
    "congestion_label",
    "alternative_explanation_label",
    "report_available_pre_t0_label",
    "report_available_by_t12_label",
    "comments",
    "adjudication_label",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("No rows found in input draft.")

    required = {
        "final_congestion_label",
        "final_alternative_explanation_label",
        "final_report_available_pre_t0_label",
        "reviewer_id",
        "final_comments",
    }
    missing_columns = required.difference(rows[0])
    if missing_columns:
        raise SystemExit(f"Missing draft columns: {sorted(missing_columns)}")

    errors: list[str] = []
    has_landmark_availability = "final_report_available_by_t12_label" in rows[0]
    has_scope = "final_report_scope" in rows[0]
    has_modality = "final_modality" in rows[0]
    if has_scope != has_modality:
        raise SystemExit("final_report_scope and final_modality must be supplied together")
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        annotation_id = row.get("annotation_id", "")
        if not annotation_id or annotation_id in seen:
            errors.append(f"row {row_number}: missing or duplicate annotation_id")
        seen.add(annotation_id)
        if not row.get("reviewer_id", "").strip():
            errors.append(f"row {row_number}: reviewer_id is blank")
        if has_scope:
            scope = row.get("final_report_scope", "")
            modality = row.get("final_modality", "")
            if scope not in REPORT_SCOPES:
                errors.append(f"row {row_number}: invalid final_report_scope")
            if modality not in MODALITIES:
                errors.append(f"row {row_number}: invalid final_modality")
            if scope == "non_chest_radiology" and row.get("final_congestion_label") != "indeterminate":
                errors.append(f"row {row_number}: non-chest report must have indeterminate congestion label")
            if scope == "chest_radiology" and modality in {"non_chest", "mixed_or_unclear", "unknown"}:
                errors.append(f"row {row_number}: chest report has incompatible final_modality")
            if scope == "non_chest_radiology" and modality != "non_chest":
                errors.append(f"row {row_number}: non-chest report must have non_chest modality")
        if row.get("final_congestion_label") not in CONGESTION:
            errors.append(f"row {row_number}: invalid final_congestion_label")
        if row.get("final_alternative_explanation_label") not in ALTERNATIVES:
            errors.append(f"row {row_number}: invalid final_alternative_explanation_label")
        if row.get("final_report_available_pre_t0_label") not in AVAILABILITY:
            errors.append(f"row {row_number}: invalid final_report_available_pre_t0_label")
        if has_landmark_availability and row.get("final_report_available_by_t12_label") not in AVAILABILITY:
            errors.append(f"row {row_number}: invalid final_report_available_by_t12_label")
        if not row.get("final_comments", "").strip():
            errors.append(f"row {row_number}: final_comments is blank")
        if row.get("review_status") != "human_reviewed":
            errors.append(f"row {row_number}: review_status must be human_reviewed")

    if errors:
        raise SystemExit("Review validation failed:\n" + "\n".join(errors[:30]))

    output_rows = []
    for row in rows:
        output_rows.append({
            "annotation_id": row["annotation_id"],
            "stay_id": row["stay_id"],
            "note_id": row["note_id"],
            "charttime": row["charttime"],
            "storetime": row["storetime"],
            "report_text": row["report_text"],
            "rule_positive_congestion": row["rule_positive_congestion"],
            "rule_uncertainty": row["rule_uncertainty"],
            "rule_negation": row["rule_negation"],
            "reviewer_id": row["reviewer_id"],
            "report_scope": row.get("final_report_scope", ""),
            "modality": row.get("final_modality", ""),
            "congestion_label": row["final_congestion_label"],
            "alternative_explanation_label": row["final_alternative_explanation_label"],
            "report_available_pre_t0_label": row["final_report_available_pre_t0_label"],
            "report_available_by_t12_label": row.get("final_report_available_by_t12_label", ""),
            "comments": row["final_comments"],
            "adjudication_label": row.get("adjudication_label", ""),
        })

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ORIGINAL_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"validated and wrote {len(output_rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
