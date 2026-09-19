#!/usr/bin/env python3
"""Initialize an isolated, traceable analysis run without copying patient data."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = Path(__file__).resolve().parent / "runs"
QUALITY_GATE_PATH = (
    Path(__file__).resolve().parent / "quality_gates" / "mimic_lab" / "quality_gate.py"
)
AUTHORITY_MANIFEST_PATH = Path(__file__).resolve().parent / "PIPELINE_AUTHORITY_MANIFEST.csv"
LAB_CONTRACT_PATH = (
    Path(__file__).resolve().parent
    / "quality_gates"
    / "mimic_lab"
    / "lab_contract_v1.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_files() -> list[Path]:
    patterns = (
        "sql/**/*.sql",
        "study_definition/*.md",
        "CS_AHF_hemodynamic_deterioration_ml_project/config/*.yaml",
        "CS_AHF_hemodynamic_deterioration_ml_project/scripts/*.py",
        "CS_AHF_hemodynamic_deterioration_ml_project/src/**/*.py",
    )
    files = {path for pattern in patterns for path in PROJECT_ROOT.glob(pattern)}
    return sorted(path for path in files if path.is_file())


def hash_execution_plan(project_root: Path, execution_plan: list[str]) -> dict[str, str]:
    """Hash only manifest-approved SQL paths and reject path traversal/missing files."""
    root = project_root.resolve()
    hashes: dict[str, str] = {}
    for relative_path in execution_plan:
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise SystemExit(f"execution-plan path escapes project root: {relative_path}") from exc
        if not candidate.is_file():
            raise SystemExit(f"execution-plan SQL is missing: {relative_path}")
        hashes[relative_path] = sha256(candidate)
    return hashes


def git_head() -> str:
    completed = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise SystemExit(f"cannot resolve Git HEAD: {completed.stderr.strip()}")
    return completed.stdout.strip()


def load_quality_gate() -> ModuleType:
    if not QUALITY_GATE_PATH.exists():
        raise SystemExit(f"quality gate is missing: {QUALITY_GATE_PATH}")
    spec = importlib.util.spec_from_file_location("mimic_lab_quality_gate", QUALITY_GATE_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"quality gate cannot be loaded: {QUALITY_GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight_final_run() -> dict[str, object]:
    """Fail before run-directory creation unless authority and repository gates pass."""
    gate = load_quality_gate()
    rows = gate.read_manifest(AUTHORITY_MANIFEST_PATH)
    contract = json.loads(LAB_CONTRACT_PATH.read_text(encoding="utf-8"))
    tracked_sql = gate.git_tracked_sql(PROJECT_ROOT)
    findings = gate.audit_repository(PROJECT_ROOT, rows, contract, tracked_sql)
    blockers = [item for item in findings if item["blocks_final_run"]]
    if blockers:
        preview = "; ".join(
            f"{item['code']}:{item['path']}" for item in blockers[:5]
        )
        raise SystemExit(
            f"quality gate blocked final run ({len(blockers)} findings): {preview}"
        )

    execution_plan = sorted(
        str(row["path"])
        for row in rows
        if row.get("authority_status") == "ACTIVE"
        and str(row.get("allow_final_run", "")).lower() == "true"
    )
    if not execution_plan:
        raise SystemExit("no ACTIVE SQL is approved for final run")

    status = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "status", "--porcelain"],
        check=False,
        text=True,
        capture_output=True,
    )
    if status.returncode != 0:
        raise SystemExit(f"cannot inspect Git worktree: {status.stderr.strip()}")
    if status.stdout.strip():
        raise SystemExit("final run requires a clean Git worktree")

    return {
        "git_head": git_head(),
        "sql_execution_plan": execution_plan,
        "sql_sha256": hash_execution_plan(PROJECT_ROOT, execution_plan),
        "tracked_sql_count": len(tracked_sql),
        "authority_manifest_sha256": sha256(AUTHORITY_MANIFEST_PATH),
        "lab_contract_sha256": sha256(LAB_CONTRACT_PATH),
        "quality_gate_findings": len(findings),
        "quality_gate_blockers": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S_v3"))
    parser.add_argument("--status", default="initialized")
    parser.add_argument("--run-class", choices=("working", "final"), default="working")
    args = parser.parse_args()

    final_preflight = preflight_final_run() if args.run_class == "final" else None

    run_dir = RUNS_ROOT / args.run_id
    if run_dir.exists():
        raise SystemExit(f"Run already exists: {run_dir}")

    for name in ("data", "logs", "qc", "models", "tables", "figures", "reports"):
        (run_dir / name).mkdir(parents=True, exist_ok=False)

    hashes = {
        str(path.relative_to(PROJECT_ROOT)): sha256(path)
        for path in tracked_files()
    }
    manifest = {
        "run_id": args.run_id,
        "run_class": args.run_class,
        "status": args.status,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "git_head": git_head(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "patient_data_copied": False,
        "tracked_file_sha256": hashes,
    }
    if final_preflight is not None:
        manifest["final_preflight"] = final_preflight
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(run_dir)


if __name__ == "__main__":
    main()
