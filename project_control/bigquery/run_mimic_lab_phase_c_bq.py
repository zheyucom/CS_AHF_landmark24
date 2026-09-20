#!/usr/bin/env python3
"""Run the aggregate-only MIMIC-IV BigQuery Phase-C laboratory audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = PROJECT_ROOT / "sql_v3_3/bigquery/audits/118_audit_raw_lab_contract_phase_c_bq.sql"
RULE_PACK_PATH = PROJECT_ROOT / (
    "phase2_edit/bq_connectivity_update/skill_implementation/"
    "mimic-iv-data-cleaning/references/mimic-iv-lab-rules.json"
)
DEFAULT_BQ = Path.home() / "google-cloud-sdk/bin/bq"
DEFAULT_GCLOUD = Path.home() / "google-cloud-sdk/bin/gcloud"
DEFAULT_MAX_BYTES = 20_000_000_000
PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
FORBIDDEN_RECORD_KEYS = {"token", "password", "secret", "user_email", "account"}
EXPECTED_OUTPUT_FIELDS = ["check_group", "concept", "reason_code", "row_count"]
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_sql(template: str, project_id: str) -> str:
    """Replace the sole project placeholder after validating a GCP project ID."""
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("invalid GCP project ID")
    placeholder = "YOUR_BILLING_PROJECT"
    if placeholder not in template:
        raise ValueError("SQL template does not contain the billing-project placeholder")
    rendered = template.replace(placeholder, project_id)
    if placeholder in rendered:
        raise ValueError("unresolved billing-project placeholder")
    return rendered


def build_bq_command(
    bq: Path,
    project_id: str,
    max_bytes: int,
    *,
    dry_run: bool,
) -> list[str]:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    command = [
        str(bq),
        "query",
        f"--project_id={project_id}",
        "--location=US",
        "--use_legacy_sql=false",
        f"--maximum_bytes_billed={max_bytes}",
        "--quiet=true",
    ]
    if dry_run:
        command.extend(["--dry_run", "--format=json"])
    else:
        command.extend(["--format=csv", "--max_rows=10000"])
    return command


def sanitize_dry_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep billing evidence and table names; discard identity-bearing job metadata."""
    statistics = payload.get("statistics", {})
    query_statistics = statistics.get("query", {})
    raw_bytes = statistics.get("totalBytesProcessed", query_statistics.get("totalBytesProcessed", 0))
    tables = []
    for table in query_statistics.get("referencedTables", []):
        parts = [table.get("projectId"), table.get("datasetId"), table.get("tableId")]
        if all(isinstance(part, str) and part for part in parts):
            tables.append(".".join(parts))
    return {
        "total_bytes_processed": int(raw_bytes),
        "referenced_tables": sorted(set(tables)),
    }


def classify_aggregate_csv(text: str) -> str:
    """Fail closed unless the expected aggregate schema and hard gates are present."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != EXPECTED_OUTPUT_FIELDS:
        raise ValueError("aggregate output has an unexpected schema")
    hard_gates: set[tuple[str, str]] = set()
    positive_gate = False
    row_seen = False
    for row in reader:
        row_seen = True
        try:
            count = int(row["row_count"])
        except (TypeError, ValueError) as exc:
            raise ValueError("aggregate row_count must be an integer") from exc
        if count < 0:
            raise ValueError("aggregate row_count cannot be negative")
        if row["check_group"] == "hard_gate":
            gate = (row["concept"], row["reason_code"])
            if gate in hard_gates:
                raise ValueError(f"duplicate hard gate: {gate}")
            hard_gates.add(gate)
            positive_gate = positive_gate or count > 0
    if not row_seen or hard_gates != EXPECTED_HARD_GATES:
        raise ValueError("aggregate output has missing or unexpected hard gates")
    return "failed_qc" if positive_gate else "passed_aggregate_qc"


def build_run_record(
    *,
    run_id: str,
    status: str,
    sql_sha256: str,
    rule_pack_sha256: str,
    dry_run: dict[str, Any] | None,
) -> dict[str, Any]:
    record = {
        "run_id": run_id,
        "status": status,
        "mimic_release": "3.1",
        "scope": "aggregate_only_no_patient_export",
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "sql_sha256": sql_sha256,
        "rule_pack_sha256": rule_pack_sha256,
        "dry_run": dry_run,
        "query_exit_code": None,
        "aggregate_row_count": None,
    }
    serialized_keys = " ".join(record).lower()
    if any(key in serialized_keys for key in FORBIDDEN_RECORD_KEYS):
        raise ValueError("run record contains a forbidden identity or credential field")
    return record


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def configured_project(gcloud: Path) -> str:
    completed = subprocess.run(
        [str(gcloud), "config", "get-value", "project"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    project_id = completed.stdout.strip()
    if completed.returncode != 0 or not PROJECT_ID_RE.fullmatch(project_id):
        raise RuntimeError("no valid gcloud project is configured")
    return project_id


def bq_environment(bq: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = str(bq.parent) + os.pathsep + env.get("PATH", "")
    return env


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bq", type=Path, default=DEFAULT_BQ)
    parser.add_argument("--gcloud", type=Path, default=DEFAULT_GCLOUD)
    parser.add_argument("--project")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
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
    if not SQL_PATH.is_file() or not RULE_PACK_PATH.is_file():
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
        project_id = args.project or configured_project(args.gcloud)
        sql = render_sql(SQL_PATH.read_text(encoding="utf-8"), project_id)
        record = build_run_record(
            run_id=args.run_id,
            status="not_run",
            sql_sha256=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            rule_pack_sha256=sha256(RULE_PACK_PATH),
            dry_run=None,
        )
        atomic_write_json(record_path, record)

        dry = subprocess.run(
            build_bq_command(args.bq, project_id, args.max_bytes, dry_run=True),
            input=sql,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            env=bq_environment(args.bq),
        )
        if dry.returncode != 0:
            combined = (dry.stdout + "\n" + dry.stderr).strip()
            record["status"] = "not_run_access_denied" if "access denied" in combined.lower() else "not_run"
            record["finished_at_utc"] = utc_now()
            record["query_exit_code"] = dry.returncode
            log_path.write_text(combined + "\n", encoding="utf-8")
            atomic_write_json(record_path, record)
            return 1

        dry_metadata = sanitize_dry_run(json.loads(dry.stdout))
        record["dry_run"] = dry_metadata
        if dry_metadata["total_bytes_processed"] > args.max_bytes:
            record["status"] = "not_run"
            record["finished_at_utc"] = utc_now()
            log_path.write_text("dry-run estimate exceeds configured maximum bytes\n", encoding="utf-8")
            atomic_write_json(record_path, record)
            return 1
        if args.dry_run_only:
            record["status"] = "dry_run_passed"
            record["finished_at_utc"] = utc_now()
            atomic_write_json(record_path, record)
            print(run_dir)
            return 0

        live = subprocess.run(
            build_bq_command(args.bq, project_id, args.max_bytes, dry_run=False),
            input=sql,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
            env=bq_environment(args.bq),
        )
        record["query_exit_code"] = live.returncode
        log_path.write_text(live.stderr, encoding="utf-8")
        if live.returncode != 0:
            combined = (live.stdout + "\n" + live.stderr).strip()
            record["status"] = "not_run_access_denied" if "access denied" in combined.lower() else "failed_query"
            if live.stdout:
                log_path.write_text(combined + "\n", encoding="utf-8")
            record["finished_at_utc"] = utc_now()
            atomic_write_json(record_path, record)
            return 1

        aggregate_path = run_dir / "aggregate_qc.csv"
        aggregate_path.write_text(live.stdout, encoding="utf-8")
        record["status"] = classify_aggregate_csv(live.stdout)
        record["aggregate_row_count"] = max(0, len(live.stdout.splitlines()) - 1)
        record["finished_at_utc"] = utc_now()
        atomic_write_json(record_path, record)
        print(run_dir)
        return 0 if record["status"] == "passed_aggregate_qc" else 1
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
