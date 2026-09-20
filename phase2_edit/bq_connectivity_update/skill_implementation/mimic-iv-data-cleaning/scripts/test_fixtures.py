#!/usr/bin/env python3
"""Synthetic regression tests for mimic-iv-data-cleaning.

The fixtures contain no patient-level data. Run directly with Python's standard
library; no third-party packages are required.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
RULE_PACK = SKILL_ROOT / "references" / "mimic-iv-lab-rules.json"
DERIVED_REFERENCE = SKILL_ROOT / "references" / "derived-reconciliation.md"


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    if not path.exists():
        raise AssertionError(f"Required implementation is missing: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load implementation: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RulePackTests(unittest.TestCase):
    def test_active_rule_pack_is_valid(self):
        validator = load_script("validate_rule_pack")
        self.assertTrue(RULE_PACK.exists(), "Rule pack has not been implemented")
        errors = validator.validate_rule_pack(json.loads(RULE_PACK.read_text()))
        self.assertEqual([], errors)

    def test_active_rule_requires_human_approval(self):
        validator = load_script("validate_rule_pack")
        pack = {
            "schema_version": "1.0.0",
            "dataset": {"name": "MIMIC-IV", "supported_versions": ["3.1"]},
            "rules": [
                {
                    "rule_id": "lab-test-v1",
                    "concept": "test",
                    "status": "active",
                    "mimic_versions": ["3.1"],
                    "source_table": "mimiciv_hosp.labevents",
                    "allow": [{"itemid": 1, "fluid": "Blood", "category": "Chemistry", "units": ["mg/dL"]}],
                    "quarantine": [],
                    "time_contract": {"availability_expression": "GREATEST(charttime, COALESCE(storetime, charttime))"},
                    "handling": {"unknown_unit": "quarantine"},
                    "evidence_sources": ["https://example.org/source"],
                    "test_ids": ["fixture-test"],
                }
            ],
        }
        errors = validator.validate_rule_pack(pack)
        self.assertTrue(any("approval" in error for error in errors), errors)

    def test_allow_and_quarantine_itemids_cannot_overlap(self):
        validator = load_script("validate_rule_pack")
        pack = json.loads(RULE_PACK.read_text())
        pack["rules"][0]["quarantine"].append({"itemid": 51006, "reason_code": "overlap"})
        errors = validator.validate_rule_pack(pack)
        self.assertTrue(any("overlap" in error.lower() for error in errors), errors)

    def test_bun_rule_quarantines_all_sourced_nonblood_itemids(self):
        pack = json.loads(RULE_PACK.read_text())
        bun_rule = next(rule for rule in pack["rules"] if rule["concept"] == "bun")
        quarantined = {entry["itemid"] for entry in bun_rule["quarantine"]}
        self.assertTrue(
            {51104, 51045, 50851, 51804, 51825, 51842, 51922, 51951}.issubset(quarantined),
            quarantined,
        )


class DerivedReconciliationReferenceTests(unittest.TestCase):
    def test_official_chemistry_and_bg_selection_is_pinned(self):
        self.assertTrue(DERIVED_REFERENCE.is_file(), "derived reconciliation reference is missing")
        text = DERIVED_REFERENCE.read_text(encoding="utf-8")
        for token in (
            "303d26c623dcc9c49cc0f204468d4acc2f063797",
            "51006",
            "0 < valuenum <= 300",
            "50912",
            "0 < valuenum <= 150",
            "50813",
            "valuenum <= 10000",
            "50821",
            "same `specimen_id`",
            "GREATEST(charttime, COALESCE(storetime, charttime))",
            "proposed",
        ):
            self.assertIn(token, text)

    def test_project_findings_do_not_self_promote_to_filtering_rules(self):
        text = DERIVED_REFERENCE.read_text(encoding="utf-8")
        for token in (
            "222/222",
            "162/162",
            "126/136",
            "549/549",
            "raw-only",
            "aggregate-only",
            "不得据此自动删除",
            "不得写成患者级事实",
        ):
            self.assertIn(token, text)


class SqlAuditTests(unittest.TestCase):
    def audit(self, sql: str):
        auditor = load_script("audit_mimic_sql")
        self.assertTrue(RULE_PACK.exists(), "Rule pack has not been implemented")
        return auditor.audit_sql(sql, json.loads(RULE_PACK.read_text()))

    def test_bun_fuzzy_label_and_wrong_fluids_are_blocked(self):
        findings = self.audit(
            """
            SELECT COALESCE(le.valuenum, 0) AS bun
            FROM mimiciv_hosp.labevents le
            JOIN mimiciv_hosp.d_labitems di USING (itemid)
            WHERE REGEXP_CONTAINS(LOWER(di.label), r'urea nitrogen')
              AND le.itemid IN (51006, 51104, 51045, 50851)
              AND le.charttime < t12
            """
        )
        codes = {finding["code"] for finding in findings if finding["severity"] == "error"}
        self.assertTrue({"MIMIC001", "MIMIC002", "MIMIC003", "MIMIC005"}.issubset(codes), codes)

    def test_known_wrong_fluid_itemids_are_allowed_only_in_explicit_quarantine_audit(self):
        findings = self.audit(
            """
            WITH known_quarantine AS (
              SELECT 51104 AS itemid, 'wrong_fluid_urine' AS reason_code
            ), approved_contract AS (
              SELECT 51006 AS itemid
            )
            SELECT le.specimen_id, le.value, le.valuenum, le.valueuom,
                   le.charttime, le.storetime,
                   q.reason_code AS quarantine_reason
            FROM mimiciv_hosp.labevents le
            JOIN known_quarantine q USING (itemid)
            WHERE GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) < t12
            """
        )
        codes = {finding["code"] for finding in findings if finding["severity"] == "error"}
        self.assertNotIn("MIMIC002", codes, findings)

    def test_compliant_bun_query_has_no_hard_failure(self):
        findings = self.audit(
            """
            SELECT le.specimen_id, le.value, le.valuenum, le.valueuom,
                   le.charttime, le.storetime
            FROM mimiciv_hosp.labevents le
            JOIN mimiciv_hosp.d_labitems di USING (itemid)
            WHERE le.itemid = 51006
              AND UPPER(di.fluid) = 'BLOOD'
              AND UPPER(di.category) = 'CHEMISTRY'
              AND le.valueuom IN ('mg/dL')
              AND GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) < t12
            """
        )
        self.assertEqual([], [f for f in findings if f["severity"] == "error"], findings)

    def test_non_lab_label_regex_is_outside_lab_audit_scope(self):
        findings = self.audit(
            """
            SELECT report_text
            FROM radiology_reports r
            JOIN mimiciv_icu.d_items di USING (itemid)
            WHERE REGEXP_CONTAINS(LOWER(di.label), r'echo|radiology')
            """
        )
        self.assertEqual([], [f for f in findings if f["severity"] == "error"], findings)

    def test_comment_mentioning_labevents_does_not_change_dictionary_only_scope(self):
        findings = self.audit(
            """
            -- Candidate discovery never reads labevents or patient identifiers.
            SELECT itemid, label, fluid, category
            FROM mimiciv_hosp.d_labitems
            WHERE REGEXP_CONTAINS(LOWER(label), r'urea nitrogen|lactate')
            """
        )
        self.assertEqual([], [f for f in findings if f["severity"] == "error"], findings)

    def test_dictionary_only_discovery_may_list_known_quarantine_itemids(self):
        findings = self.audit(
            """
            SELECT itemid, label, fluid, category
            FROM mimiciv_hosp.d_labitems
            WHERE itemid IN (51006, 51104, 51045, 50851)
            """
        )
        self.assertEqual([], [f for f in findings if f["severity"] == "error"], findings)

    def test_unknown_unit_and_post_landmark_availability_are_quarantined(self):
        cleaner = load_script("audit_mimic_sql")
        rules = json.loads(RULE_PACK.read_text())
        landmark = datetime.fromisoformat("2026-01-01T12:00:00")
        rows = [
            {
                "specimen_id": 1,
                "itemid": 51006,
                "fluid": "Blood",
                "category": "Chemistry",
                "valueuom": "mmol/L",
                "charttime": "2026-01-01T10:00:00",
                "storetime": "2026-01-01T11:00:00",
                "value": "20",
            },
            {
                "specimen_id": 2,
                "itemid": 51006,
                "fluid": "Blood",
                "category": "Chemistry",
                "valueuom": "mg/dL",
                "charttime": "2026-01-01T10:00:00",
                "storetime": "2026-01-01T12:01:00",
                "value": "22",
            },
        ]
        result = cleaner.classify_lab_rows(rows, "bun", landmark, rules)
        reasons = {entry["reason_code"] for entry in result["quarantine"]}
        self.assertEqual({"unknown_unit", "available_after_landmark"}, reasons)

    def test_censored_value_is_preserved_and_duplicate_specimen_is_quarantined(self):
        cleaner = load_script("audit_mimic_sql")
        rules = json.loads(RULE_PACK.read_text())
        landmark = datetime.fromisoformat("2026-01-01T12:00:00")
        base = {
            "specimen_id": 9,
            "itemid": 51006,
            "fluid": "Blood",
            "category": "Chemistry",
            "valueuom": "mg/dL",
            "charttime": "2026-01-01T10:00:00",
            "storetime": "2026-01-01T10:30:00",
            "value": ">300",
        }
        result = cleaner.classify_lab_rows([base, dict(base)], "bun", landmark, rules)
        self.assertEqual(">", result["accepted"][0]["censor_type"])
        self.assertEqual("300", result["accepted"][0]["raw_boundary"])
        self.assertEqual("duplicate_specimen_itemid", result["quarantine"][0]["reason_code"])

    def test_raw_derived_reconciliation_is_bidirectional(self):
        cleaner = load_script("audit_mimic_sql")
        result = cleaner.reconcile_keys({"raw-only", "both"}, {"derived-only", "both"})
        self.assertEqual(["raw-only"], result["raw_only"])
        self.assertEqual(["derived-only"], result["derived_only"])
        self.assertEqual(["both"], result["both"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
