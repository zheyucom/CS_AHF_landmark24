#!/usr/bin/env python3
"""Build the compact landmark-12 radiology audit from the complete text export.

This mirrors the modality preamble rule in BigQuery query 111 locally after the
complete Parquet export has been verified. The report text is not copied to the
compact output.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


COMPACT_COLUMNS = [
    "stay_id", "subject_id", "hadm_id", "note_id", "note_type", "note_seq",
    "charttime", "storetime", "report_available_by_t12_flag",
    "storetime_missing_flag", "pulmonary_edema_hit", "vascular_congestion_hit",
    "pleural_effusion_hit", "cardiomegaly_hit", "pulmonary_edema_negation_hit",
    "vascular_congestion_negation_hit", "uncertainty_hit",
    "positive_congestion_evidence_flag", "report_modality", "rule_version",
]


def has(row: dict[str, str], key: str) -> bool:
    return row.get(key, "").strip() in {"1", "1.0", "true", "True"}


def modality(text: str) -> str:
    preamble = (text or "")[:1500].lower()
    ct = [
        r"(?:^|\n)\s*(?:examination|exam|study|procedure|technique)\s*:\s*[^\n]{0,120}\b(?:ct|cta)\b[^\n]{0,120}\b(?:chest|thorax)\b",
        r"(?:^|\n)\s*(?:examination|exam|study|procedure|technique)\s*:\s*[^\n]{0,120}\b(?:chest|thorax)\b[^\n]{0,120}\b(?:ct|cta)\b",
        r"^\s*(?:ct|cta)\b[^\n]{0,100}\b(?:chest|thorax)\b|^\s*computed\s+tomograph(?:y|ic)\b[^\n]{0,100}\b(?:chest|thorax)\b",
    ]
    xray = [
        r"(?:^|\n)\s*(?:examination|exam|study|procedure|technique)\s*:\s*(?:[^\n]{0,80}\b(?:portable\s+)?(?:ap|pa)\s+(?:portable\s+)?chest\b|[^\n]{0,80}\bportable\s+chest\b|\s*chest\s*$|[^\n]{0,80}\bchest\s+(?:radiograph|x[- ]?ray)\b|[^\n]{0,80}\bchest\s+(?:pa\s+and\s+lat(?:eral)?|two\s+views|2\s+views|portable\s+ap)\b)",
        r"^\s*(?:ap|pa)\s+(?:portable\s+)?chest\b|^\s*portable\s+chest\b|^\s*two\s+views\s+of\s+the\s+chest\b|^\s*chest\s*\(\s*(?:portable\s+)?(?:ap|pa)",
    ]
    if any(re.search(pattern, preamble, flags=re.MULTILINE) for pattern in ct):
        return "chest_ct"
    if any(re.search(pattern, preamble, flags=re.MULTILINE) for pattern in xray):
        return "chest_xray"
    return "other_or_unclassified"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 7828:
        raise SystemExit(f"Expected 7,828 complete reports, got {len(rows)}")
    keys = [(row.get("stay_id", ""), row.get("note_id", "")) for row in rows]
    if len(set(keys)) != len(keys):
        raise SystemExit("Duplicate (stay_id, note_id) keys")
    compact = []
    for row in rows:
        compact.append({
            key: row.get(key, "") for key in COMPACT_COLUMNS
        } | {
            "report_modality": modality(row.get("text", "")),
            "rule_version": "111_landmark12_compact_report_audit_v1; local_from_verified_gcs_export; preamble_modality_rule; manual_validation_required",
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMPACT_COLUMNS)
        writer.writeheader()
        writer.writerows(compact)
    print(f"Wrote {len(compact)} complete compact reports to {args.output}")


if __name__ == "__main__":
    main()
