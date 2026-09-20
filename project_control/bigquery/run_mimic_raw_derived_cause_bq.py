#!/usr/bin/env python3
"""Run the aggregate-only raw-vs-derived cause audit for MIMIC-IV."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = PROJECT_ROOT / "sql_v3_3/bigquery/audits/119_audit_raw_vs_derived_cause_phase_c_bq.sql"
BASE_RUNNER_PATH = PROJECT_ROOT / "project_control/bigquery/run_mimic_lab_phase_c_bq.py"
EXPECTED_FIELDS = [
    "check_group",
    "concept",
    "metric",
    "cause_code",
    "stay_count",
    "event_count",
    "mean_abs_diff",
    "max_abs_diff",
]
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


def load_base_runner():
    spec = importlib.util.spec_from_file_location("mimic_lab_phase_c_bq", BASE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the shared BigQuery runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base_runner()


def classify_cause_csv(text: str) -> str:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != EXPECTED_FIELDS:
        raise ValueError("cause audit output has an unexpected schema")
    hard_gates: set[tuple[str, str]] = set()
    row_seen = False
    positive_gate = False
    for row in reader:
        row_seen = True
        for field in ("stay_count", "event_count"):
            try:
                count = int(row[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field} must be an integer") from exc
            if count < 0:
                raise ValueError(f"{field} cannot be negative")
        if row["check_group"] == "hard_gate":
            gate = (row["concept"], row["cause_code"])
            if gate in hard_gates:
                raise ValueError(f"duplicate hard gate: {gate}")
            hard_gates.add(gate)
            positive_gate = positive_gate or int(row["stay_count"]) > 0 or int(row["event_count"]) > 0
    if not row_seen or hard_gates != EXPECTED_HARD_GATES:
        raise ValueError("cause audit output has missing or unexpected hard gates")
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

        (run_dir / "aggregate_qc.csv").write_text(live.stdout, encoding="utf-8")
        record["status"] = classify_cause_csv(live.stdout)
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
