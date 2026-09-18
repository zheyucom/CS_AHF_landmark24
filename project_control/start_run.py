#!/usr/bin/env python3
"""Initialize an isolated, traceable analysis run without copying patient data."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = Path(__file__).resolve().parent / "runs"


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S_v3"))
    parser.add_argument("--status", default="initialized")
    args = parser.parse_args()

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
        "status": args.status,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "patient_data_copied": False,
        "tracked_file_sha256": hashes,
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(run_dir)


if __name__ == "__main__":
    main()

