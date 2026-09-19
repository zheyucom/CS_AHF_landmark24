#!/usr/bin/env python3
"""Run the project-local MIMIC cleaning skill against SQL without executing SQL."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = PROJECT_ROOT / "phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning"
AUDITOR_PATH = SKILL_ROOT / "scripts/audit_mimic_sql.py"
RULE_PACK_PATH = SKILL_ROOT / "references/mimic-iv-lab-rules.json"
OUTPUT_DIR = PROJECT_ROOT / "project_control/audits"


def load_auditor():
    spec = importlib.util.spec_from_file_location("mimic_skill_auditor", AUDITOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load auditor: {AUDITOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sql_paths() -> list[Path]:
    paths = set()
    for root in (PROJECT_ROOT / "sql_v3_3", PROJECT_ROOT / "project_control"):
        if root.exists():
            paths.update(path for path in root.rglob("*.sql") if path.is_file())
    return sorted(paths)


def main() -> int:
    auditor = load_auditor()
    rule_pack = json.loads(RULE_PACK_PATH.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for path in sql_paths():
        findings = auditor.audit_sql(path.read_text(encoding="utf-8"), rule_pack)
        errors = [finding for finding in findings if finding["severity"] == "error"]
        warnings = [finding for finding in findings if finding["severity"] == "warning"]
        status = "blocked" if errors else "warning" if warnings else "pass"
        records.append(
            {
                "path": str(path.relative_to(PROJECT_ROOT)),
                "sha256": sha256(path),
                "status": status,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "finding_codes": [finding["code"] for finding in findings],
                "findings": findings,
            }
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "read-only static SQL preflight; no database or patient-level query executed",
        "rule_pack": str(RULE_PACK_PATH.relative_to(PROJECT_ROOT)),
        "rule_pack_sha256": sha256(RULE_PACK_PATH),
        "sql_count": len(records),
        "pass_count": sum(record["status"] == "pass" for record in records),
        "warning_count": sum(record["status"] == "warning" for record in records),
        "blocked_count": sum(record["status"] == "blocked" for record in records),
        "records": records,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "mimic_skill_preflight_20260919.json"
    csv_path = OUTPUT_DIR / "mimic_skill_preflight_20260919.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "sha256", "status", "error_count", "warning_count", "finding_codes"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow({key: record[key] for key in writer.fieldnames})
    print(json.dumps({key: summary[key] for key in (
        "sql_count", "pass_count", "warning_count", "blocked_count"
    )}, ensure_ascii=False))
    print(json_path)
    print(csv_path)
    return 1 if summary["blocked_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
