#!/usr/bin/env python3
"""Audit a complete landmark radiology export and prepare blinded DHF annotation sheets.

The script deliberately uses only the Python standard library.  It is run only
after the landmark batch export has been downloaded locally; radiology text stays in the supplied
controlled output directory and never enters the prediction dataset.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_RAW_COLUMNS = {
    "stay_id",
    "subject_id",
    "hadm_id",
    "note_id",
    "charttime",
    "storetime",
    "admittime",
    "intime",
    "window_start",
    "landmark12_time",
    "text",
    "pulmonary_edema_hit",
    "vascular_congestion_hit",
    "pulmonary_edema_negation_hit",
    "vascular_congestion_negation_hit",
    "uncertainty_hit",
    "report_available_by_t12_flag",
    "storetime_missing_flag",
    "positive_congestion_evidence_flag",
    "rule_version",
}

REQUIRED_COHORT_COLUMNS = {"stay_id", "admittime", "intime"}

ANNOTATION_COLUMNS = [
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
    "congestion_label",
    "alternative_explanation_label",
    "report_available_pre_t0_label",
    "report_available_by_t12_label",
    "comments",
    "adjudication_label",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require_columns(rows: list[dict[str, str]], required: set[str], path: Path) -> None:
    if not rows:
        raise ValueError(f"No data rows found in {path}")
    columns = set(rows[0])
    missing = sorted(required - columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {', '.join(missing)}")


def parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Unparseable timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def as_flag(row: dict[str, str], column: str) -> bool:
    return row.get(column, "").strip() == "1"


def report_stratum(row: dict[str, str]) -> str:
    if as_flag(row, "positive_congestion_evidence_flag") and not as_flag(row, "uncertainty_hit"):
        return "definite_positive_rule_screen"
    if (
        as_flag(row, "uncertainty_hit")
        or as_flag(row, "pulmonary_edema_negation_hit")
        or as_flag(row, "vascular_congestion_negation_hit")
    ):
        return "negated_or_uncertain_screen"
    return "no_hit_screen"


def sample_rows(rows: list[dict[str, str]], requested: int, rng: random.Random) -> list[dict[str, str]]:
    if len(rows) <= requested:
        return list(rows)
    return rng.sample(rows, requested)


def annotation_row(row: dict[str, str], annotation_id: str) -> dict[str, str]:
    return {
        "annotation_id": annotation_id,
        "stay_id": row["stay_id"],
        "note_id": row["note_id"],
        "charttime": row["charttime"],
        "storetime": row["storetime"],
        "report_text": row["text"],
        "rule_positive_congestion": row["positive_congestion_evidence_flag"],
        "rule_uncertainty": row["uncertainty_hit"],
        "rule_negation": str(
            int(
                as_flag(row, "pulmonary_edema_negation_hit")
                or as_flag(row, "vascular_congestion_negation_hit")
            )
        ),
        "reviewer_id": "",
        "congestion_label": "",
        "alternative_explanation_label": "",
        # The batch export exposes report_available_by_t12_flag.  The
        # annotation label is independently recomputed from storetime below.
        "report_available_pre_t0_label": row.get("report_available_pre_t0_label", "unknown"),
        "report_available_by_t12_label": row.get("report_available_by_t12_label", "unknown"),
        "comments": "",
        "adjudication_label": "",
    }


def embedded_landmark_times(
    raw_rows: list[dict[str, str]],
) -> dict[str, tuple[datetime, datetime, datetime, datetime]]:
    """Use the audited T0/T12 boundaries carried by the complete export."""
    times: dict[str, tuple[datetime, datetime, datetime, datetime]] = {}
    for row in raw_rows:
        stay_id = row["stay_id"].strip()
        parsed = tuple(
            parse_timestamp(row[column])
            for column in ("admittime", "intime", "window_start", "landmark12_time")
        )
        if any(value is None for value in parsed):
            raise ValueError(f"Invalid embedded landmark boundary for stay_id {stay_id}")
        typed = parsed  # all values are non-None after the check above
        if stay_id in times and times[stay_id] != typed:
            raise ValueError(f"Inconsistent embedded landmark boundary for stay_id {stay_id}")
        times[stay_id] = typed  # type: ignore[assignment]
    return times


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-csv", type=Path, required=True, help="Complete CSV exported from BigQuery query 112 batches")
    parser.add_argument(
        "--cohort-csv",
        type=Path,
        default=Path(__file__).with_name("dhf_radiology_candidates.csv"),
        help="Legacy candidate CSV retained for provenance; landmark boundaries come from the complete export",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="New controlled local annotation directory")
    parser.add_argument("--per-stratum", type=int, default=100, help="Requested reports from each screen stratum")
    parser.add_argument("--double-review-fraction", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument(
        "--exclude-invalid-boundaries",
        action="store_true",
        help="Retain embedded admittime/intime anomalies in QC while using audited window bounds.",
    )
    args = parser.parse_args()

    if args.output_dir.exists():
        raise SystemExit(f"Output directory already exists: {args.output_dir}")
    if args.per_stratum <= 0 or not 0 < args.double_review_fraction <= 1:
        raise SystemExit("per-stratum must be positive and double-review-fraction must be in (0, 1].")

    raw_rows = read_csv(args.raw_csv)
    require_columns(raw_rows, REQUIRED_RAW_COLUMNS, args.raw_csv)

    embedded_times = embedded_landmark_times(raw_rows)
    cohort_times = {stay_id: (values[0], values[1]) for stay_id, values in embedded_times.items()}
    invalid_boundary_stays = sum(admittime > intime for admittime, intime, _, _ in embedded_times.values())
    if invalid_boundary_stays and not args.exclude_invalid_boundaries:
        raise SystemExit(
            "Embedded export contains admission/ICU boundary anomalies; "
            "rerun with --exclude-invalid-boundaries to retain them in QC and use the audited window bounds."
        )

    qc = Counter()
    strata: dict[str, list[dict[str, str]]] = {
        "definite_positive_rule_screen": [],
        "negated_or_uncertain_screen": [],
        "no_hit_screen": [],
    }
    seen_note_ids: set[tuple[str, str]] = set()
    for row in raw_rows:
        stay_id, note_id = row["stay_id"].strip(), row["note_id"].strip()
        if stay_id not in cohort_times:
            qc["unknown_stay_id"] += 1
            continue
        if not note_id:
            qc["missing_note_id"] += 1
        elif (stay_id, note_id) in seen_note_ids:
            qc["duplicate_stay_note_id"] += 1
        else:
            seen_note_ids.add((stay_id, note_id))

        charttime = parse_timestamp(row["charttime"])
        admittime, intime, window_start, landmark12_time = embedded_times[stay_id]
        if charttime is None or not window_start <= charttime < landmark12_time:
            qc["charttime_outside_pre_t0_window"] += 1
        else:
            qc["charttime_pre_t0_valid"] += 1
        storetime = parse_timestamp(row["storetime"])
        if storetime is None:
            qc["storetime_missing"] += 1
            row["report_available_pre_t0_label"] = "unknown"
            row["report_available_by_t12_label"] = "unknown"
        elif storetime < intime:
            qc["storetime_pre_t0"] += 1
            row["report_available_pre_t0_label"] = "yes"
            row["report_available_by_t12_label"] = "yes"
            qc["report_available_by_t12"] += 1
        else:
            qc["storetime_at_or_after_t0"] += 1
            row["report_available_pre_t0_label"] = "no"
            row["report_available_by_t12_label"] = "yes" if storetime < landmark12_time else "no"
            if storetime < landmark12_time:
                qc["report_available_by_t12"] += 1
        strata[report_stratum(row)].append(row)

    invalid = sum(
        qc[key]
        for key in ("unknown_stay_id", "missing_note_id", "duplicate_stay_note_id", "charttime_outside_pre_t0_window")
    )
    if invalid:
        raise SystemExit(
            "Raw result failed integrity QC: "
            + ", ".join(f"{key}={qc[key]}" for key in sorted(qc) if qc[key])
        )

    rng = random.Random(args.seed)
    sampled: list[tuple[str, dict[str, str]]] = []
    for stratum, rows in strata.items():
        sampled.extend((stratum, row) for row in sample_rows(rows, args.per_stratum, rng))

    annotation_rows = [
        annotation_row(row, f"DHF-RAD-{index:04d}")
        for index, (_, row) in enumerate(sampled, start=1)
    ]
    recheck_count = round(len(annotation_rows) * args.double_review_fraction)
    recheck_indexes = set(rng.sample(range(len(annotation_rows)), recheck_count))
    recheck_rows = []
    for index in sorted(recheck_indexes):
        row = dict(annotation_rows[index])
        row["annotation_id"] = f"DHF-RAD-R2-{index + 1:04d}"
        recheck_rows.append(row)

    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "dhf_radiology_annotation_round1.csv", annotation_rows, ANNOTATION_COLUMNS)
    write_csv(args.output_dir / "dhf_radiology_annotation_round2_blinded.csv", recheck_rows, ANNOTATION_COLUMNS)
    sampling_rows = [
        {
            "annotation_id": annotation["annotation_id"],
            "sampling_stratum": stratum,
            "stay_id": annotation["stay_id"],
            "note_id": annotation["note_id"],
        }
        for (stratum, _), annotation in zip(sampled, annotation_rows, strict=True)
    ]
    write_csv(
        args.output_dir / "dhf_radiology_sampling_key_restricted.csv",
        sampling_rows,
        ["annotation_id", "sampling_stratum", "stay_id", "note_id"],
    )

    total_cohort = len(cohort_times)
    stays_with_reports = len({row["stay_id"].strip() for row in raw_rows})
    report_counts = {name: len(rows) for name, rows in strata.items()}
    report = [
        "# DHF Radiology Import QC and Annotation Package",
        "",
        "This package contains protected clinical text for blinded phenotype validation only. ",
        "Do not merge it with outcome, T0-T12 predictor, or model-prediction data.",
        "",
        "## Inputs",
        "",
        f"- Complete landmark batch CSV: `{args.raw_csv}`",
        f"- Candidate-time-boundary CSV: `{args.cohort_csv}`",
        f"- Random seed: `{args.seed}`",
        "",
        "## Integrity QC",
        "",
        f"- Stays represented in the complete export with valid landmark boundaries: {total_cohort}",
        f"- Candidate stays excluded for invalid boundary (`admittime > intime`): {invalid_boundary_stays}",
        f"- Raw report rows: {len(raw_rows)}", 
        f"- Stays with at least one pre-T0 report: {stays_with_reports}",
        f"- `charttime` within `admittime <= charttime < intime`: {qc['charttime_pre_t0_valid']}",
        f"- `storetime < intime`: {qc['storetime_pre_t0']}",
        f"- Missing `storetime`: {qc['storetime_missing']}",
        f"- `storetime >= intime`: {qc['storetime_at_or_after_t0']}",
        f"- `storetime < landmark12_time`: {qc['report_available_by_t12']}",
        "",
        "## Screen and Sampling",
        "",
        *[
            f"- {name}: {report_counts[name]} eligible reports; {min(report_counts[name], args.per_stratum)} sampled"
            for name in strata
        ],
        f"- Round 1 blinded reviews: {len(annotation_rows)} reports",
        f"- Independent round 2 blinded reviews: {len(recheck_rows)} reports ({args.double_review_fraction:.0%})",
        "",
        "## Interpretation Boundary",
        "",
        "The screen strata are weak labels.  `definite_positive_rule_screen` is not a final DHF diagnosis;",
        "the clinical annotation guide defines the report-level label and the later patient-level multidomain phenotype.",
    ]
    (args.output_dir / "README.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Prepared annotation package: {args.output_dir}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
