#!/usr/bin/env python3
"""Structural regressions for the MIMIC-IV laboratory semantic audit.

These tests inspect SQL text only and contain no patient-level data.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_CONTROL = Path(__file__).resolve().parents[1]
AUDIT_SQL = PROJECT_CONTROL / "MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql"
DISCOVERY_SQL = PROJECT_CONTROL / "MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql"
LEGACY_SQL = PROJECT_CONTROL / "MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql"


def required_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"required SQL is missing: {path.name}")
    return path.read_text(encoding="utf-8")


class SemanticAuditV2Tests(unittest.TestCase):
    def test_audit_uses_exact_project_lab_contracts(self):
        sql = required_text(AUDIT_SQL)
        for token in (
            "51006",  # BUN blood
            "50813",  # lactate
            "50912",  # creatinine blood chemistry
            "50820",  # blood pH
            "50963",  # NT-proBNP blood
            "51003",  # troponin T blood
            "Blood",
            "Chemistry",
            "Blood Gas",
        ):
            self.assertIn(token, sql)
        self.assertNotRegex(sql.lower(), r"regexp_contains\s*\([^;]*\blabel\b")

    def test_wrong_fluid_bun_itemids_are_quarantined(self):
        sql = required_text(AUDIT_SQL)
        for itemid in (51104, 51045, 50851, 51804, 51825, 51842, 51922, 51951):
            self.assertRegex(sql, rf"\b{itemid}\b")
        self.assertIn("wrong_fluid", sql)

    def test_result_availability_and_landmark_are_enforced(self):
        compact = re.sub(r"\s+", " ", required_text(AUDIT_SQL).lower())
        self.assertRegex(
            compact,
            r"greatest\s*\(\s*le\.charttime\s*,\s*coalesce\s*\(\s*le\.storetime\s*,\s*le\.charttime\s*\)\s*\)",
        )
        self.assertIn("available_after_landmark", compact)
        self.assertIn("storetime_before_charttime", compact)
        self.assertIn("datetime_add(cast(intime as datetime), interval 12 hour)", compact)

    def test_raw_values_censoring_units_and_duplicates_are_preserved(self):
        sql = required_text(AUDIT_SQL).lower()
        for token in (
            "labevent_id",
            "specimen_id",
            "value",
            "valuenum",
            "valueuom",
            "right_censored",
            "left_censored",
            "interval",
            "lower_bound",
            "upper_bound",
            "duplicate_specimen_itemid",
            "unknown_unit",
        ):
            self.assertIn(token, sql)
        self.assertNotRegex(sql, r"coalesce\s*\(\s*(?:\w+\.)?(?:value|valuenum)\s*,\s*0")

    def test_bun_and_lactate_reconcile_raw_and_derived_both_directions(self):
        sql = required_text(AUDIT_SQL).lower()
        self.assertRegex(sql, r"mimiciv_(?:3_1_)?derived\.chemistry")
        self.assertRegex(sql, r"mimiciv_(?:3_1_)?derived\.bg")
        self.assertIn("full outer join", sql)
        for status in ("raw_only", "derived_only", "both"):
            self.assertIn(status, sql)

    def test_final_output_is_aggregate_and_has_reason_codes(self):
        sql = required_text(AUDIT_SQL).lower()
        self.assertIn("quarantine_reason", sql)
        self.assertIn("count(distinct stay_id)", sql)
        self.assertIn("audit_section", sql)
        self.assertIn("rule_version", sql)

    def test_candidate_discovery_cannot_select_patient_rows(self):
        sql = required_text(DISCOVERY_SQL).lower()
        executable_sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
        self.assertIn("d_labitems", sql)
        self.assertIn("regexp_contains", sql)
        self.assertIn("proposed_candidate", sql)
        self.assertNotIn("labevents", executable_sql)
        self.assertNotIn("subject_id", executable_sql)
        self.assertNotIn("hadm_id", executable_sql)

    def test_superseded_v1_fails_closed_before_patient_query(self):
        sql = required_text(LEGACY_SQL)
        executable_sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE).strip().lower()
        self.assertTrue(executable_sql.startswith("assert false"), executable_sql[:200])
        self.assertIn("mimic_labevents_semantic_audit_v2.sql", sql.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
