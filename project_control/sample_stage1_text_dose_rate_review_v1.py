#!/usr/bin/env python3
"""Create a small, deterministic review pack for text dose/rate mentions."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "project_control/runs/20260925_internal_stage1_text_dose_extract"
OUT = RUN / "text_dose_rate_review_sample_v1.csv"


def as_bool(value: str) -> bool:
    """Parse CSV boolean fields without treating the word False as true."""
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def read_rows():
    with (RUN / "target_drug_text_dose_rate_mentions_v1.csv").open(encoding="utf-8-sig", newline="", errors="replace") as fh:
        yield from csv.DictReader(fh)


def main() -> None:
    strata = defaultdict(list)
    for row in read_rows():
        # Stratify on context and ambiguity as well as polarity and the
        # presence of dose/rate text. This keeps the review set useful for
        # checking template/reference text and multi-drug dose borrowing.
        key = (
            row.get("drug_class", ""),
            row.get("mention_polarity", ""),
            as_bool(row.get("dose_mentions")),
            as_bool(row.get("rate_mentions")),
            row.get("mention_context", ""),
            row.get("dose_rate_ambiguity", ""),
        )
        strata[key].append(row)
    sample = []
    for key in sorted(strata):
        candidates = sorted(strata[key], key=lambda x: (x.get("patient_id", ""), x.get("document_id", ""), x.get("source_ref", "")))
        sample.extend(candidates[:2])
    fields = list(sample[0]) + [
        "review_status",
        "reviewer",
        "confirmed_drug",
        "confirmed_dose",
        "confirmed_rate",
        "review_notes",
    ]
    with OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in sample:
            row = dict(row)
            row.update({k: "" for k in fields if k not in row})
            writer.writerow(row)
    print(f"strata={len(strata)} sample_n={len(sample)}")


if __name__ == "__main__":
    main()
