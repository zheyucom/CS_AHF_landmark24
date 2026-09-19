#!/usr/bin/env python3
"""Integration regression for the final-run authority preflight."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "start_run.py"
RUN_ID = "__quality_gate_final_run_must_fail_without_active_sql__"


def load_start_run():
    spec = importlib.util.spec_from_file_location("start_run_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("start_run.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StartRunQualityGateTests(unittest.TestCase):
    def test_final_execution_plan_records_each_sql_hash(self) -> None:
        start_run = load_start_run()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sql = root / "sql/current.sql"
            sql.parent.mkdir()
            sql.write_text("SELECT 1;\n", encoding="utf-8")
            hashes = start_run.hash_execution_plan(root, ["sql/current.sql"])
        self.assertEqual(
            hashlib.sha256(b"SELECT 1;\n").hexdigest(),
            hashes["sql/current.sql"],
        )

    def test_final_run_fails_before_creating_directory_when_no_sql_is_active(self) -> None:
        run_dir = ROOT / "project_control" / "runs" / RUN_ID
        self.assertFalse(run_dir.exists(), f"stale test directory exists: {run_dir}")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--run-id",
                RUN_ID,
                "--run-class",
                "final",
            ],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("no ACTIVE SQL", completed.stdout + completed.stderr)
        self.assertFalse(run_dir.exists(), "preflight failure must not leave a run directory")


if __name__ == "__main__":
    unittest.main(verbosity=2)
