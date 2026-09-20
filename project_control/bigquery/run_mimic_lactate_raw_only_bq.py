#!/usr/bin/env python3
"""Run the aggregate-only lactate raw-only decomposition audit."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import math
import sys
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = PROJECT_ROOT / "sql_v3_3/bigquery/audits/121_audit_lactate_raw_only_phase_c_bq.sql"
BASE_RUNNER_PATH = PROJECT_ROOT / "project_control/bigquery/run_mimic_lab_phase_c_bq.py"
EXPECTED_FIELDS = [
    "check_group",
    "concept",
    "cause_code",
    "stay_count",
    "mean_raw_max",
    "max_raw_max",
]
EXPECTED_REFERENCE_TOTAL = 549
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
        ("lactate", "raw_only_public_bg_in_window_match"),
    }
)
EXPECTED_CAUSES = frozenset(
    {
        "no_lactate_specimen_has_po2",
        "po2_present_all_lactate_values_outside_official_range",
        "official_candidate_in_window_absent_from_public_bg",
        "official_candidates_all_after_t12",
        "raw_only_unresolved",
    }
)
EXPECTED_MEMBERSHIPS = frozenset(
    {
        "raw_max_specimen_has_po2",
        "any_lactate_specimen_has_po2",
        "any_official_bg_candidate",
        "official_candidate_charttime_in_window",
        "official_candidate_charttime_after_t12",
        "official_candidate_matches_public_bg_any_time",
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


def _validate_summary_fields(row: dict[str, str], count: int) -> None:
    values: list[float | None] = []
    for field in ("mean_raw_max", "max_raw_max"):
        raw = row[field]
        if raw in {None, ""}:
            values.append(None)
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be numeric or empty") from exc
        if not math.isfinite(value):
            raise ValueError(f"{field} must be finite")
        values.append(value)
    mean_value, max_value = values
    if (mean_value is None) != (max_value is None):
        raise ValueError("raw max summaries must be both populated or both empty")
    if count > 0 and row["check_group"] != "hard_gate" and mean_value is None:
        raise ValueError("positive aggregate rows require raw max summaries")
    if mean_value is not None and max_value is not None and mean_value > max_value:
        raise ValueError("mean_raw_max cannot exceed max_raw_max")


def classify_raw_only_csv(text: str) -> str:
    """Fail closed on schema, gates, fixed reference, catalogs, or conservation."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != EXPECTED_FIELDS:
        raise ValueError("lactate raw-only output has an unexpected schema")

    row_keys: set[tuple[str, str, str]] = set()
    hard_gates: set[tuple[str, str]] = set()
    positive_gate = False
    reference_total: int | None = None
    cause_counts: dict[str, int] = {}
    membership_counts: dict[str, int] = {}
    row_seen = False

    for row in reader:
        row_seen = True
        key = (row["check_group"], row["concept"], row["cause_code"])
        if key in row_keys:
            raise ValueError(f"duplicate aggregate row: {key}")
        row_keys.add(key)
        count = _parse_count(row)
        _validate_summary_fields(row, count)

        if row["check_group"] == "hard_gate":
            gate = (row["concept"], row["cause_code"])
            hard_gates.add(gate)
            positive_gate = positive_gate or count > 0
        elif row["check_group"] == "reference_total":
            if row["concept"] != "lactate" or row["cause_code"] != "raw_only":
                raise ValueError("unexpected raw-only reference row")
            reference_total = count
        elif row["check_group"] == "exclusive_cause":
            if row["concept"] != "lactate" or row["cause_code"] not in EXPECTED_CAUSES:
                raise ValueError("unexpected raw-only exclusive cause row")
            cause_counts[row["cause_code"]] = count
        elif row["check_group"] == "membership":
            if row["concept"] != "lactate" or row["cause_code"] not in EXPECTED_MEMBERSHIPS:
                raise ValueError("unexpected raw-only membership row")
            membership_counts[row["cause_code"]] = count
        else:
            raise ValueError(f"unexpected check_group: {row['check_group']}")

    if not row_seen or hard_gates != EXPECTED_HARD_GATES:
        raise ValueError("lactate raw-only output has missing or unexpected hard gates")
    if reference_total != EXPECTED_REFERENCE_TOTAL:
        raise ValueError("raw-only reference total differs from the fixed 119 audit")
    if set(cause_counts) != EXPECTED_CAUSES:
        raise ValueError("raw-only output has missing or unexpected exclusive causes")
    if set(membership_counts) != EXPECTED_MEMBERSHIPS:
        raise ValueError("raw-only output has missing or unexpected memberships")
    if sum(cause_counts.values()) != reference_total:
        raise ValueError("raw-only exclusive cause conservation failed")
    if any(count > reference_total for count in membership_counts.values()):
        raise ValueError("raw-only membership exceeds the reference total")
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
            record["status"] = classify_raw_only_csv(live.stdout)
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
