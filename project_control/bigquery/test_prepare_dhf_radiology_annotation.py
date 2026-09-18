#!/usr/bin/env python3
"""Minimal regression test for the local DHF radiology annotation preparer."""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control/bigquery/prepare_dhf_radiology_annotation.py"


class PrepareAnnotationTest(unittest.TestCase):
    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_prepares_three_strata_and_double_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            cohort = workdir / "cohort.csv"
            raw = workdir / "raw.csv"
            output = workdir / "annotation"
            self.write_csv(
                cohort,
                [
                    {"stay_id": "1", "admittime": "2100-01-01 00:00:00", "intime": "2100-01-01 12:00:00"},
                    {"stay_id": "2", "admittime": "2100-01-01 00:00:00", "intime": "2100-01-01 12:00:00"},
                    {"stay_id": "3", "admittime": "2100-01-01 00:00:00", "intime": "2100-01-01 12:00:00"},
                ],
            )
            base = {
                "subject_id": "10", "hadm_id": "20", "storetime": "2100-01-01 03:30:00",
                "admittime": "2100-01-01 00:00:00", "intime": "2100-01-01 12:00:00",
                "window_start": "2100-01-01 00:00:00", "landmark12_time": "2100-01-02 00:00:00",
                "text": "report", "pulmonary_edema_hit": "0", "vascular_congestion_hit": "0",
                "pulmonary_edema_negation_hit": "0", "vascular_congestion_negation_hit": "0",
                "uncertainty_hit": "0", "report_available_pre_t0_flag": "1",
                "report_available_by_t12_flag": "1",
                "storetime_missing_flag": "0", "positive_congestion_evidence_flag": "0",
                "rule_version": "test",
            }
            self.write_csv(
                raw,
                [
                    base | {"stay_id": "1", "note_id": "101", "charttime": "2100-01-01 03:00:00", "pulmonary_edema_hit": "1", "positive_congestion_evidence_flag": "1"},
                    base | {"stay_id": "2", "note_id": "102", "charttime": "2100-01-01 03:00:00", "uncertainty_hit": "1"},
                    base | {"stay_id": "3", "note_id": "103", "charttime": "2100-01-01 03:00:00"},
                ],
            )
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--raw-csv", str(raw), "--cohort-csv", str(cohort),
                 "--output-dir", str(output), "--per-stratum", "1", "--seed", "7"],
                check=False, text=True, capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with (output / "dhf_radiology_annotation_round1.csv").open(newline="", encoding="utf-8") as handle:
                prepared = list(csv.DictReader(handle))
                self.assertEqual(len(prepared), 3)
                self.assertIn("report_available_by_t12_label", prepared[0])
            with (output / "dhf_radiology_annotation_round2_blinded.csv").open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 1)
            self.assertIn("charttime` within", (output / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
