#!/usr/bin/env python3
"""Additional fail-closed edge-case regression checks for the MIMIC skill."""

from __future__ import annotations

import importlib.util
import json
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "audit_mimic_sql.py"
RULES = ROOT.parent / "references" / "mimic-iv-lab-rules.json"


def load_audit():
    spec = importlib.util.spec_from_file_location("audit_mimic_sql", AUDIT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EdgeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit()
        cls.rules = json.loads(RULES.read_text(encoding="utf-8"))

    def base_row(self):
        return {
            "specimen_id": 1,
            "itemid": 51006,
            "fluid": "Blood",
            "category": "Chemistry",
            "valueuom": "mg/dL",
            "charttime": "2026-01-01T10:00:00+00:00",
            "storetime": "2026-01-01T10:30:00+00:00",
            "value": "20",
        }

    def test_missing_specimen_storetime_inversion_interval_and_missing_value_fail_closed(self):
        rows = []
        missing_specimen = self.base_row()
        missing_specimen["specimen_id"] = None
        rows.append(missing_specimen)
        inversion = self.base_row()
        inversion["specimen_id"] = 2
        inversion["storetime"] = "2026-01-01T09:00:00+00:00"
        rows.append(inversion)
        interval = self.base_row()
        interval["specimen_id"] = 3
        interval["value"] = "10-20"
        rows.append(interval)
        missing_value = self.base_row()
        missing_value["specimen_id"] = 4
        missing_value["value"] = None
        rows.append(missing_value)
        result = self.audit.classify_lab_rows(rows, "bun", datetime.fromisoformat("2026-01-01T12:00:00"), self.rules)
        self.assertEqual([], result["accepted"])
        self.assertEqual(
            {"missing_specimen_id", "storetime_before_charttime", "interval_value", "missing_value"},
            {entry["reason_code"] for entry in result["quarantine"]},
        )

    def test_derived_only_source_is_hard_error(self):
        findings = self.audit.audit_sql(
            "SELECT subject_id, bun FROM mimiciv_derived.labs WHERE charttime < t12",
            self.rules,
        )
        self.assertIn("MIMIC009", {finding["code"] for finding in findings if finding["severity"] == "error"})

    def test_quarantine_contract_does_not_treat_isolation_ids_as_inclusion(self):
        sql = """
        WITH lab_quarantine_item_v1 AS (
          SELECT 51104 AS itemid, 'wrong_fluid_urine' AS quarantine_reason
        ), source_rows AS (
          SELECT le.itemid, qi.quarantine_reason AS known_quarantine_reason
          FROM mimiciv_hosp.labevents le
          LEFT JOIN lab_quarantine_item_v1 qi USING (itemid)
        )
        SELECT itemid, quarantine_reason FROM source_rows
        """
        findings = self.audit.audit_sql(sql, self.rules)
        self.assertNotIn("MIMIC002", {finding["code"] for finding in findings if finding["severity"] == "error"})

    def test_lab_contract_plus_derived_support_is_not_derived_only(self):
        sql = """
        SELECT le.stay_id, le.analysis_value, v.heart_rate
        FROM study_ahf_v3_3.lab_eligible_v1 le
        JOIN mimiciv_derived.vitalsign v USING (stay_id)
        """
        findings = self.audit.audit_sql(sql, self.rules)
        self.assertNotIn("MIMIC009", {finding["code"] for finding in findings if finding["severity"] == "error"})

    def test_raw_value_and_timezone_normalization_are_preserved(self):
        row = self.base_row()
        row["value"] = ">300"
        result = self.audit.classify_lab_rows(
            [row], "bun", datetime.fromisoformat("2026-01-01T12:00:00"), self.rules
        )
        accepted = result["accepted"][0]
        self.assertEqual(">300", accepted["raw_value"])
        self.assertEqual(">", accepted["censor_type"])
        self.assertEqual("300", accepted["raw_boundary"])
        self.assertEqual("2026-01-01T10:30:00", accepted["availability_time"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
