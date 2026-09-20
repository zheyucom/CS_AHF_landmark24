#!/usr/bin/env python3
"""Run the aggregate-only second-layer raw-vs-derived unequal audit."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = PROJECT_ROOT / (
    "sql_v3_3/bigquery/audits/120_audit_raw_vs_derived_unequal_phase_c_bq.sql"
)
BASE_RUNNER_PATH = PROJECT_ROOT / "project_control/bigquery/run_mimic_lab_phase_c_bq.py"
EXPECTED_FIELDS = [
    "check_group",
    "concept",
    "direction",
    "cause_code",
    "stay_count",
    "mean_abs_diff",
    "max_abs_diff",
]
EXPECTED_CONCEPTS = frozenset({"bun", "creatinine", "lactate"})
EXPECTED_REFERENCE_TOTALS = {"bun": 222, "creatinine": 162, "lactate": 136}
EXPECTED_HARD_GATES = frozenset(
    {
        ("all", "active_dictionary_mismatch"),
        ("all", "cohort_duplicate_stay_rows"),
        ("all", "cohort_invalid_boundary"),
        ("all", "cohort_missing_key"),
        ("all", "eligible_specimen_violation"),
        ("all", "eligible_time_violation"),
        ("all", "eligible_wrong_contract"),
        ("all", "quarantine_dictionary_mismatch"),
        ("bun", "bun_eligible_nonblood_or_wrong_item"),
    }
)
EXPECTED_CAUSE_PAIRS = frozenset(
    {
        ("precision_only", "precision_only"),
        ("derived_higher", "derived_higher_matches_late_raw"),
        ("derived_higher", "derived_higher_matches_other_quarantine_raw"),
        ("derived_higher", "derived_higher_not_found_in_raw"),
        ("raw_higher", "raw_higher_lactate_specimen_missing_po2"),
        ("raw_higher", "raw_higher_specimen_absent_from_derived"),
        ("raw_higher", "raw_higher_derived_value_in_eligible_raw_set"),
        ("raw_higher", "raw_higher_unresolved"),
        ("derived_higher", "derived_higher_unresolved"),
    }
)
EXPECTED_MEMBERSHIPS = frozenset(
    {
        "derived_max_in_eligible_raw_set",
        "derived_max_in_late_raw_set",
        "derived_max_in_any_raw_set",
        "raw_max_in_derived_event_set",
    }
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location("mimic_lab_phase_c_bq", BASE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the shared BigQuery runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base_runner()


def _parse_count(row: dict[str, str]) -> int:
    try:
        count = int(row["stay_count"])
    except (TypeError, ValueError) as exc:
        raise ValueError("stay_count must be an integer") from exc
    if count < 0:
        raise ValueError("stay_count cannot be negative")
    return count


def _validate_diff_fields(row: dict[str, str], count: int) -> None:
    values: list[float | None] = []
    for field in ("mean_abs_diff", "max_abs_diff"):
        raw = row[field]
        if raw in {None, ""}:
            values.append(None)
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be numeric or empty") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{field} must be finite and nonnegative")
        values.append(value)
    mean_diff, max_diff = values
    if (mean_diff is None) != (max_diff is None):
        raise ValueError("difference summaries must be both populated or both empty")
    if count > 0 and row["check_group"] != "hard_gate" and mean_diff is None:
        raise ValueError("positive aggregate rows require difference summaries")
    if mean_diff is not None and max_diff is not None and mean_diff > max_diff:
        raise ValueError("mean_abs_diff cannot exceed max_abs_diff")


def classify_unequal_csv(text: str) -> str:
    """Fail closed on schema, hard gates, missing categories, or imbalance."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != EXPECTED_FIELDS:
        raise ValueError("unequal audit output has an unexpected schema")

    hard_gates: set[tuple[str, str]] = set()
    positive_gate = False
    reference_totals: dict[str, int] = {}
    exclusive_totals: dict[str, int] = defaultdict(int)
    exclusive_seen: set[tuple[str, str, str]] = set()
    membership_seen: set[tuple[str, str]] = set()
    membership_counts: dict[tuple[str, str], int] = {}
    precision_counts: dict[str, int] = {}
    row_keys: set[tuple[str, str, str, str]] = set()
    row_seen = False

    for row in reader:
        row_seen = True
        key = (row["check_group"], row["concept"], row["direction"], row["cause_code"])
        if key in row_keys:
            raise ValueError(f"duplicate aggregate row: {key}")
        row_keys.add(key)
        count = _parse_count(row)
        _validate_diff_fields(row, count)

        if row["check_group"] == "hard_gate":
            if row["direction"] != "not_applicable":
                raise ValueError("hard gates must use not_applicable direction")
            gate = (row["concept"], row["cause_code"])
            hard_gates.add(gate)
            positive_gate = positive_gate or count > 0
        elif row["check_group"] == "reference_total":
            if (
                row["concept"] not in EXPECTED_CONCEPTS
                or row["direction"] != "all"
                or row["cause_code"] != "both_unequal"
            ):
                raise ValueError("unexpected reference total row")
            reference_totals[row["concept"]] = count
        elif row["check_group"] == "exclusive_cause":
            concept = row["concept"]
            pair = (row["direction"], row["cause_code"])
            if concept not in EXPECTED_CONCEPTS or pair not in EXPECTED_CAUSE_PAIRS:
                raise ValueError("unexpected exclusive cause row")
            exclusive_seen.add((concept, *pair))
            exclusive_totals[concept] += count
            if row["cause_code"] == "precision_only":
                precision_counts[concept] = count
        elif row["check_group"] == "membership":
            if (
                row["concept"] not in EXPECTED_CONCEPTS
                or row["direction"] != "all"
                or row["cause_code"] not in EXPECTED_MEMBERSHIPS
            ):
                raise ValueError("unexpected membership row")
            membership_key = (row["concept"], row["cause_code"])
            membership_seen.add(membership_key)
            membership_counts[membership_key] = count
        else:
            raise ValueError(f"unexpected check_group: {row['check_group']}")

    expected_exclusive = {
        (concept, direction, cause_code)
        for concept in EXPECTED_CONCEPTS
        for direction, cause_code in EXPECTED_CAUSE_PAIRS
    }
    expected_membership = {
        (concept, cause_code)
        for concept in EXPECTED_CONCEPTS
        for cause_code in EXPECTED_MEMBERSHIPS
    }
    if not row_seen or hard_gates != EXPECTED_HARD_GATES:
        raise ValueError("unequal audit output has missing or unexpected hard gates")
    if reference_totals != EXPECTED_REFERENCE_TOTALS:
        raise ValueError("both-unequal reference totals differ from the fixed 119 audit")
    if exclusive_seen != expected_exclusive:
        raise ValueError("unequal audit output has missing or unexpected exclusive causes")
    if membership_seen != expected_membership:
        raise ValueError("unequal audit output has missing or unexpected memberships")
    for concept, reference_total in reference_totals.items():
        if exclusive_totals[concept] != reference_total:
            raise ValueError(f"exclusive cause conservation failed for {concept}")
        if precision_counts.get(concept) != 0:
            raise ValueError(f"precision-only sentinel is nonzero for {concept}")
        for cause_code in EXPECTED_MEMBERSHIPS:
            if membership_counts[(concept, cause_code)] > reference_total:
                raise ValueError(f"membership exceeds reference total for {concept}")
    return "failed_qc" if positive_gate else "passed_aggregate_qc"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bq", type=Path, default=BASE.DEFAULT_BQ)
    parser.add_argument("--gcloud", type=Path, default=BASE.DEFAULT_GCLOUD)
    parser.add_argument("--project")
    parser.add_argument("--max-bytes", type=int, default=BASE.DEFAULT_MAX_BYTES)
    parser.add_argument("--dry-run-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if Path(args.run_id).name != args.run_id or args.run_id in {"", ".", ".."}:
        print("--run-id must be one safe path component", file=sys.stderr)
        return 2
    if not args.bq.is_file() or not args.gcloud.is_file():
        print("bq or gcloud executable is missing", file=sys.stderr)
        return 2
    if not SQL_PATH.is_file() or not BASE.RULE_PACK_PATH.is_file():
        print("SQL template or rule pack is missing", file=sys.stderr)
        return 2

    run_dir = PROJECT_ROOT / "project_control/runs" / args.run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"run directory is not empty: {run_dir}", file=sys.stderr)
        return 2
    run_dir.mkdir(parents=True, exist_ok=True)
    record_path = run_dir / "run.json"
    log_path = run_dir / "execution.log"

    try:
        project_id = args.project or BASE.configured_project(args.gcloud)
        sql = BASE.render_sql(SQL_PATH.read_text(encoding="utf-8"), project_id)
        record = BASE.build_run_record(
            run_id=args.run_id,
            status="not_run",
            sql_sha256=__import__("hashlib").sha256(sql.encode("utf-8")).hexdigest(),
            rule_pack_sha256=BASE.sha256(BASE.RULE_PACK_PATH),
            dry_run=None,
        )
        BASE.atomic_write_json(record_path, record)

        dry = BASE.subprocess.run(
            BASE.build_bq_command(args.bq, project_id, args.max_bytes, dry_run=True),
            input=sql,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            env=BASE.bq_environment(args.bq),
        )
        if dry.returncode != 0:
            combined = (dry.stdout + "\n" + dry.stderr).strip()
            record["status"] = "not_run_access_denied" if "access denied" in combined.lower() else "not_run"
            record["finished_at_utc"] = BASE.utc_now()
            record["query_exit_code"] = dry.returncode
            log_path.write_text(combined + "\n", encoding="utf-8")
            BASE.atomic_write_json(record_path, record)
            return 1

        record["dry_run"] = BASE.sanitize_dry_run(json.loads(dry.stdout))
        if record["dry_run"]["total_bytes_processed"] > args.max_bytes:
            record["finished_at_utc"] = BASE.utc_now()
            log_path.write_text("dry-run estimate exceeds configured maximum bytes\n", encoding="utf-8")
            BASE.atomic_write_json(record_path, record)
            return 1
        if args.dry_run_only:
            record["status"] = "dry_run_passed"
            record["finished_at_utc"] = BASE.utc_now()
            BASE.atomic_write_json(record_path, record)
            print(run_dir)
            return 0

        live = BASE.subprocess.run(
            BASE.build_bq_command(args.bq, project_id, args.max_bytes, dry_run=False),
            input=sql,
            capture_output=True,
            text=True,
            check=False,
            timeout=900,
            env=BASE.bq_environment(args.bq),
        )
        record["query_exit_code"] = live.returncode
        if live.returncode != 0:
            combined = (live.stdout + "\n" + live.stderr).strip()
            record["status"] = "not_run_access_denied" if "access denied" in combined.lower() else "failed_query"
            record["finished_at_utc"] = BASE.utc_now()
            log_path.write_text(combined + "\n", encoding="utf-8")
            BASE.atomic_write_json(record_path, record)
            return 1

        aggregate_path = run_dir / "aggregate_qc.csv"
        aggregate_path.write_text(live.stdout, encoding="utf-8")
        try:
            record["status"] = classify_unequal_csv(live.stdout)
        except ValueError as exc:
            record["status"] = "failed_qc"
            record["aggregate_row_count"] = max(0, len(live.stdout.splitlines()) - 1)
            record["finished_at_utc"] = BASE.utc_now()
            log_path.write_text(str(exc) + "\n" + live.stderr, encoding="utf-8")
            BASE.atomic_write_json(record_path, record)
            return 1
        record["aggregate_row_count"] = max(0, len(live.stdout.splitlines()) - 1)
        record["finished_at_utc"] = BASE.utc_now()
        log_path.write_text(live.stderr, encoding="utf-8")
        BASE.atomic_write_json(record_path, record)
        print(run_dir)
        return 0 if record["status"] == "passed_aggregate_qc" else 1
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, BASE.subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
