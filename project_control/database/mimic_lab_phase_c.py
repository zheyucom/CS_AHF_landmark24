#!/usr/bin/env python3
"""Execute the patient-local MIMIC laboratory Phase-C PostgreSQL plan.

The runner records reproducibility metadata only.  It never accepts a database
password and exports only the two explicitly registered aggregate audit tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


PHASE_C_PLAN = [
    "sql_v3_3/executable/060_create_raw_lab_contract_layer_v1.sql",
    "sql_v3_3/audits/116_audit_raw_lab_contract_phase_c.sql",
    "sql_v3_3/executable/061A_create_ahf_evidence_table_12h_v2.sql",
    "sql_v3_3/executable/061C_create_pre12_overt_cs_flags_v2.sql",
    "sql_v3_3/executable/061E_create_post12_overt_cs_future48h_v2.sql",
    "sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql",
    "sql_v3_3/modeling/090B_create_compact_predictors_v34.sql",
    "sql_v3_3/audits/117_audit_raw_vs_derived_phase_c.sql",
]

AGGREGATE_EXPORTS = {
    "lab_contract_qc.csv": "study_ahf_v3_3.audit_116_lab_contract_phase_c_v1",
    "raw_vs_derived_qc.csv": "study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1",
}

REQUIRED_RELATIONS = (
    "mimiciv_hosp.labevents",
    "mimiciv_hosp.d_labitems",
    "study_ahf_v3_2.model_090a_modeling_base_v33_v1",
    "study_ahf_v3_2.model_090b_compact_predictors_v33_v1",
)


def utc_now() -> str:
    """Return a stable UTC timestamp for run metadata."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_inside(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"SQL path escapes project root: {relative}") from exc
    return candidate


def hash_sql_plan(project_root: Path, plan: Sequence[str]) -> dict[str, str]:
    """Hash every planned SQL file after enforcing project-root containment."""

    hashes: dict[str, str] = {}
    for relative in plan:
        sql_path = _resolve_inside(project_root, relative)
        if not sql_path.is_file():
            raise FileNotFoundError(f"Planned SQL file does not exist: {relative}")
        hashes[relative] = hashlib.sha256(sql_path.read_bytes()).hexdigest()
    return hashes


def build_psql_file_command(
    psql: Path,
    sql_file: Path,
    *,
    host: str,
    user: str,
    database: str,
) -> list[str]:
    """Build the fail-closed, noninteractive command for one SQL file."""

    return [
        str(psql),
        "-X",
        "-w",
        "-v",
        "ON_ERROR_STOP=1",
        "--single-transaction",
        "-h",
        host,
        "-U",
        user,
        "-d",
        database,
        "-f",
        str(sql_file),
    ]


def preflight_database(
    *,
    psql: Path,
    host: str,
    user: str,
    database: str,
) -> dict[str, str]:
    """Verify database identity, write capability and required source relations."""

    relation_queries = "\nunion all\n".join(
        "select "
        f"'relation:{relation}'::text, "
        f"coalesce(to_regclass('{relation}')::text, '')"
        for relation in REQUIRED_RELATIONS
    )
    query = f"""
select 'database'::text, current_database()::text
union all
select 'server_version', current_setting('server_version')
union all
select 'transaction_read_only', current_setting('transaction_read_only')
union all
select 'database_create_privilege',
       has_database_privilege(current_user, current_database(), 'CREATE')::text
union all
{relation_queries};
"""
    command = [
        str(psql),
        "-X",
        "-w",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        host,
        "-U",
        user,
        "-d",
        database,
        "-At",
        "-F",
        "\t",
        "-c",
        query,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Database preflight command failed: {completed.stderr.strip()}")

    observed: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        observed[key] = value

    if observed.get("database") != database:
        raise RuntimeError(
            f"Database preflight selected {observed.get('database', '<missing>')}, expected {database}"
        )
    if observed.get("transaction_read_only") != "off":
        raise RuntimeError("Database preflight requires transaction_read_only=off")
    if observed.get("database_create_privilege") not in {"t", "true"}:
        raise RuntimeError("Database preflight requires CREATE privilege on the database")
    missing = [
        relation
        for relation in REQUIRED_RELATIONS
        if observed.get(f"relation:{relation}") != relation
    ]
    if missing:
        raise RuntimeError(f"Database preflight is missing required relations: {', '.join(missing)}")
    return observed


def atomic_write_json(target: Path, payload: dict[str, Any]) -> None:
    """Atomically replace a UTF-8 JSON run record in the target directory."""

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.tmp"
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def execute_sql_plan(
    *,
    project_root: Path,
    psql: Path,
    plan: Sequence[str],
    run_dir: Path,
    host: str,
    user: str,
    database: str,
    preflight: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute SQL files in order and stop immediately after the first failure."""

    project_root = project_root.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    sql_hashes = hash_sql_plan(project_root, plan)
    record: dict[str, Any] = {
        "run_id": run_dir.name,
        "status": "running",
        "database": database,
        "host": host,
        "user": user,
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "sql_sha256": sql_hashes,
        "preflight": preflight,
        "steps": [],
    }
    for relative in plan:
        record["steps"].append(
            {
                "sql": relative,
                "sha256": sql_hashes[relative],
                "status": "not_run",
                "started_at_utc": None,
                "finished_at_utc": None,
                "exit_code": None,
            }
        )
    atomic_write_json(run_dir / "run.json", record)

    log_path = run_dir / "execution.log"
    failed = False
    with log_path.open("a", encoding="utf-8") as log:
        for step in record["steps"]:
            if failed:
                break
            sql_path = _resolve_inside(project_root, step["sql"])
            command = build_psql_file_command(
                psql,
                sql_path,
                host=host,
                user=user,
                database=database,
            )
            step["status"] = "running"
            step["started_at_utc"] = utc_now()
            atomic_write_json(run_dir / "run.json", record)
            log.write(f"[{step['started_at_utc']}] START {step['sql']} sha256={step['sha256']}\n")
            log.flush()
            completed = subprocess.run(
                command,
                cwd=project_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            step["exit_code"] = completed.returncode
            step["finished_at_utc"] = utc_now()
            step["status"] = "passed" if completed.returncode == 0 else "failed"
            log.write(
                f"[{step['finished_at_utc']}] END {step['sql']} "
                f"status={step['status']} exit_code={completed.returncode}\n"
            )
            log.flush()
            atomic_write_json(run_dir / "run.json", record)
            failed = completed.returncode != 0

    record["status"] = "failed" if failed else "passed"
    record["finished_at_utc"] = utc_now()
    atomic_write_json(run_dir / "run.json", record)
    return record


def export_registered_aggregates(
    *,
    psql: Path,
    run_dir: Path,
    host: str,
    user: str,
    database: str,
) -> None:
    """Export only the allowlisted aggregate QC tables to CSV."""

    qc_dir = run_dir / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    for filename, qualified_table in AGGREGATE_EXPORTS.items():
        command = [
            str(psql),
            "-X",
            "-w",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            host,
            "-U",
            user,
            "-d",
            database,
            "-c",
            f"COPY (SELECT * FROM {qualified_table}) TO STDOUT WITH (FORMAT CSV, HEADER true)",
        ]
        target = qc_dir / filename
        with target.open("w", encoding="utf-8", newline="") as output:
            completed = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, text=True, check=False)
        if completed.returncode != 0:
            target.unlink(missing_ok=True)
            raise RuntimeError(
                f"Aggregate export failed for {qualified_table}: {completed.stderr.strip()}"
            )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--psql", type=Path, required=True)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--database", default="mimiciv31")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[2]
    if not args.psql.is_file():
        print(f"psql executable not found: {args.psql}", file=sys.stderr)
        return 2
    if Path(args.run_id).name != args.run_id or args.run_id in {"", ".", ".."}:
        print("--run-id must be one safe path component", file=sys.stderr)
        return 2

    run_dir = project_root / "project_control/database/runs" / args.run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        print(f"run directory is not empty: {run_dir}", file=sys.stderr)
        return 2

    try:
        preflight = preflight_database(
            psql=args.psql,
            host=args.host,
            user=args.user,
            database=args.database,
        )
        record = execute_sql_plan(
            project_root=project_root,
            psql=args.psql,
            plan=PHASE_C_PLAN,
            run_dir=run_dir,
            host=args.host,
            user=args.user,
            database=args.database,
            preflight=preflight,
        )
        if record["status"] != "passed":
            print(f"Phase-C SQL plan failed; see {run_dir / 'execution.log'}", file=sys.stderr)
            return 1
        export_registered_aggregates(
            psql=args.psql,
            run_dir=run_dir,
            host=args.host,
            user=args.user,
            database=args.database,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
