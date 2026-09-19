#!/usr/bin/env python3
"""Synthetic, patient-free regressions for the MIMIC lab SQL quality gate."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


GATE_PATH = Path(__file__).resolve().parents[1] / "quality_gate.py"

CONTRACT = {
    "rules": [
        {
            "concept": "bun",
            "status": "active",
            "allow": [
                {
                    "itemid": 51006,
                    "fluid": "Blood",
                    "category": "Chemistry",
                    "units": ["mg/dL"],
                }
            ],
            "quarantine": [
                {"itemid": 51104, "reason_code": "wrong_fluid_urine"},
                {"itemid": 51045, "reason_code": "wrong_fluid_other_body_fluid"},
            ],
        },
        {
            "concept": "lactate",
            "status": "active",
            "allow": [
                {
                    "itemid": 50813,
                    "fluid": "Blood",
                    "category": "Blood Gas",
                    "units": ["mmol/L"],
                }
            ],
            "quarantine": [],
        },
    ]
}


def manifest_row(path: str, **overrides):
    row = {
        "path": path,
        "artifact_kind": "feature",
        "authority_status": "ACTIVE",
        "analysis_role": "main",
        "engine": "postgres",
        "replacement_path": "",
        "allow_final_run": "true",
        "rationale": "Synthetic test fixture.",
        "reviewed_on": "2026-09-19",
    }
    row.update(overrides)
    return row


def load_gate():
    if not GATE_PATH.exists():
        raise AssertionError("quality_gate.py has not been implemented")
    spec = importlib.util.spec_from_file_location("mimic_lab_quality_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("quality_gate.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ManifestValidationTests(unittest.TestCase):
    def test_unregistered_sql_is_a_hard_failure(self) -> None:
        gate = load_gate()
        findings = gate.validate_manifest_rows([], {"sql/current.sql"})
        self.assertTrue(
            any(
                finding["code"] == "MANIFEST_UNREGISTERED"
                and finding["severity"] == "error"
                and finding["path"] == "sql/current.sql"
                for finding in findings
            ),
            findings,
        )

    def test_duplicate_and_unknown_manifest_entries_fail(self) -> None:
        gate = load_gate()
        rows = [
            manifest_row("sql/a.sql"),
            manifest_row("sql/a.sql"),
            manifest_row("sql/not-tracked.sql", authority_status="UNKNOWN"),
        ]
        codes = {
            finding["code"]
            for finding in gate.validate_manifest_rows(rows, {"sql/a.sql"})
        }
        self.assertTrue(
            {"MANIFEST_DUPLICATE", "MANIFEST_NOT_TRACKED", "MANIFEST_BAD_STATUS"}.issubset(codes),
            codes,
        )

    def test_only_active_rows_may_enter_final_run(self) -> None:
        gate = load_gate()
        audit_row = manifest_row(
            "sql/audit.sql",
            authority_status="AUDIT_ONLY",
            analysis_role="audit",
            allow_final_run="true",
        )
        findings = gate.validate_manifest_rows([audit_row], {"sql/audit.sql"})
        self.assertIn("MANIFEST_FINAL_RUN_STATUS", {item["code"] for item in findings})

    def test_active_and_boolean_state_cannot_be_ambiguous(self) -> None:
        gate = load_gate()
        active_disabled = manifest_row("sql/active.sql", allow_final_run="false")
        invalid_boolean = manifest_row(
            "sql/audit.sql",
            authority_status="AUDIT_ONLY",
            analysis_role="audit",
            allow_final_run="yes",
        )
        findings = gate.validate_manifest_rows(
            [active_disabled, invalid_boolean], {"sql/active.sql", "sql/audit.sql"}
        )
        codes = {item["code"] for item in findings}
        self.assertIn("MANIFEST_ACTIVE_NOT_FINAL", codes)
        self.assertIn("MANIFEST_BAD_BOOLEAN", codes)

    def test_superseded_replacement_must_be_tracked(self) -> None:
        gate = load_gate()
        row = manifest_row(
            "sql/old.sql",
            authority_status="SUPERSEDED",
            analysis_role="historical",
            allow_final_run="false",
            replacement_path="sql/missing.sql",
        )
        findings = gate.validate_manifest_rows([row], {"sql/old.sql"})
        self.assertIn("MANIFEST_BAD_REPLACEMENT", {item["code"] for item in findings})

    def test_execution_plan_rejects_blocked_and_unregistered_paths(self) -> None:
        gate = load_gate()
        rows = [
            manifest_row("sql/active.sql"),
            manifest_row(
                "sql/legacy.sql",
                authority_status="LEGACY_BLOCKED",
                analysis_role="historical",
                allow_final_run="false",
            ),
        ]
        findings = gate.validate_execution_plan(
            ["sql/active.sql", "sql/legacy.sql", "sql/missing.sql"], rows
        )
        codes_by_path = {(item["code"], item["path"]) for item in findings}
        self.assertIn(("PLAN_BLOCKED_ARTIFACT", "sql/legacy.sql"), codes_by_path)
        self.assertIn(("PLAN_UNREGISTERED_ARTIFACT", "sql/missing.sql"), codes_by_path)


class SqlScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = load_gate()
        self.active = manifest_row("sql/current.sql")
        self.audit = manifest_row(
            "sql/audit.sql",
            artifact_kind="audit",
            authority_status="AUDIT_ONLY",
            analysis_role="audit",
            allow_final_run="false",
        )

    def codes(self, sql: str, row=None) -> set[str]:
        return {
            item["code"]
            for item in self.gate.scan_sql(
                (row or self.active)["path"], sql, row or self.active, CONTRACT
            )
        }

    def test_raw_lab_contract_gaps_fail_closed(self) -> None:
        codes = self.codes(
            "SELECT 51006, le.charttime FROM mimiciv_hosp.labevents le "
            "WHERE le.charttime < t12"
        )
        self.assertTrue(
            {
                "LAB_AVAILABILITY_MISSING",
                "LAB_UNIT_CONTRACT_MISSING",
                "LAB_FLUID_CONTRACT_MISSING",
                "LAB_CATEGORY_CONTRACT_MISSING",
                "LAB_SPECIMEN_CONTRACT_MISSING",
            }.issubset(codes),
            codes,
        )

    def test_derived_source_is_blocked_for_formal_feature(self) -> None:
        codes = self.codes("SELECT bun FROM mimiciv_derived.chemistry")
        self.assertIn("LAB_DERIVED_FORMAL_SOURCE", codes)

    def test_derived_lab_range_null_is_detected(self) -> None:
        codes = self.codes(
            "SELECT CASE WHEN ch.bun BETWEEN 1 AND 200 THEN ch.bun ELSE NULL END AS bun "
            "FROM mimiciv_derived.chemistry ch"
        )
        self.assertIn("LAB_SILENT_RANGE_NULL", codes)

    def test_non_lab_derived_table_is_outside_lab_gate_scope(self) -> None:
        codes = self.codes(
            "SELECT CASE WHEN v.sbp BETWEEN 40 AND 300 THEN v.sbp ELSE NULL END AS sbp "
            "FROM mimiciv_derived.vitalsign v"
        )
        self.assertNotIn("LAB_DERIVED_FORMAL_SOURCE", codes)
        self.assertNotIn("LAB_SILENT_RANGE_NULL", codes)

    def test_audit_only_may_reconcile_derived(self) -> None:
        codes = self.codes(
            "SELECT coverage_status FROM mimiciv_derived.chemistry "
            "FULL OUTER JOIN mimiciv_hosp.labevents USING (specimen_id)",
            self.audit,
        )
        self.assertNotIn("LAB_DERIVED_FORMAL_SOURCE", codes)

    def test_dangerous_lab_shortcuts_are_detected(self) -> None:
        sql = """
        SELECT
          COALESCE(le.valuenum, 0) AS bun,
          CASE WHEN le.valuenum BETWEEN 1 AND 300 THEN le.valuenum ELSE NULL END AS bun_clean
        FROM mimiciv_hosp.labevents le
        JOIN mimiciv_hosp.d_labitems di USING (itemid)
        WHERE LOWER(di.label) LIKE '%urea%' OR le.itemid = 51104
        """
        codes = self.codes(sql)
        self.assertTrue(
            {
                "LAB_MISSING_TO_ZERO",
                "LAB_SILENT_RANGE_NULL",
                "LAB_FUZZY_METADATA_SELECTION",
                "LAB_WRONG_FLUID_ITEMID",
            }.issubset(codes),
            codes,
        )

    def test_unregistered_lab_itemid_is_detected(self) -> None:
        self.assertIn(
            "LAB_UNREGISTERED_ITEMID",
            self.codes("SELECT * FROM mimiciv_hosp.labevents WHERE itemid = 59999"),
        )

    def test_numeric_threshold_is_not_misclassified_as_itemid(self) -> None:
        codes = self.codes(
            "SELECT * FROM mimiciv_hosp.labevents "
            "WHERE itemid = 51006 AND valuenum <= 10000"
        )
        self.assertNotIn("LAB_UNREGISTERED_ITEMID", codes)

    def test_availability_expression_without_landmark_comparison_still_fails(self) -> None:
        sql = """
        WITH lab_contract AS (SELECT 51006 AS itemid)
        SELECT le.specimen_id, le.valueuom, di.fluid, di.category,
               'unknown_unit' AS unit_status,
               'fluid_mismatch' AS fluid_status,
               'category_mismatch' AS category_status,
               'duplicate_specimen' AS duplicate_status,
               GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) AS availability_time
        FROM mimiciv_hosp.labevents le
        JOIN mimiciv_hosp.d_labitems di USING (itemid)
        """
        self.assertIn("LAB_LANDMARK_GATE_MISSING", self.codes(sql))

    def test_contract_cte_name_does_not_prove_fluid_or_category_validation(self) -> None:
        sql = """
        WITH lab_contract AS (SELECT 51006 AS itemid)
        SELECT le.specimen_id, le.valueuom, di.fluid, di.category,
               'unknown_unit' AS unit_status,
               'duplicate_specimen' AS duplicate_status,
               GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) AS availability_time
        FROM mimiciv_hosp.labevents le
        JOIN mimiciv_hosp.d_labitems di USING (itemid)
        WHERE availability_time < t12
        """
        codes = self.codes(sql)
        self.assertIn("LAB_FLUID_CONTRACT_MISSING", codes)
        self.assertIn("LAB_CATEGORY_CONTRACT_MISSING", codes)

    def test_compliant_raw_contract_passes(self) -> None:
        sql = """
        WITH lab_contract AS (
          SELECT 51006 AS itemid, 'Blood' AS fluid,
                 'Chemistry' AS category, 'mg/dL' AS allowed_unit
        ), classified AS (
          SELECT le.specimen_id, le.itemid, le.value, le.valuenum, le.valueuom,
                 di.fluid, di.category,
                 GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) AS availability_time,
                 COUNT(*) OVER (PARTITION BY le.specimen_id, le.itemid) AS specimen_itemid_count,
                 CASE WHEN le.valueuom != lc.allowed_unit THEN 'unknown_unit'
                      WHEN di.fluid != lc.fluid THEN 'fluid_mismatch'
                      WHEN di.category != lc.category THEN 'category_mismatch'
                      ELSE 'eligible' END AS quarantine_reason
          FROM mimiciv_hosp.labevents le
          JOIN mimiciv_hosp.d_labitems di USING (itemid)
          JOIN lab_contract lc ON le.itemid = lc.itemid
        )
        SELECT * FROM classified
        WHERE availability_time < t12 AND quarantine_reason = 'eligible'
        """
        errors = [
            item
            for item in self.gate.scan_sql("sql/current.sql", sql, self.active, CONTRACT)
            if item["severity"] == "error"
        ]
        self.assertEqual([], errors)


class DependencyTests(unittest.TestCase):
    def test_active_sql_cannot_read_table_produced_only_by_blocked_sql(self) -> None:
        gate = load_gate()
        sql_by_path = {
            "sql/legacy.sql": "CREATE TABLE analysis.legacy_labs AS SELECT 1;",
            "sql/current.sql": "SELECT * FROM analysis.legacy_labs;",
        }
        rows = [
            manifest_row(
                "sql/legacy.sql",
                authority_status="LEGACY_BLOCKED",
                analysis_role="historical",
                allow_final_run="false",
            ),
            manifest_row("sql/current.sql"),
        ]
        findings = gate.scan_blocked_dependencies(sql_by_path, rows)
        self.assertIn(
            ("DEPENDENCY_BLOCKED_TABLE", "sql/current.sql"),
            {(item["code"], item["path"]) for item in findings},
        )


class RepositoryAuditTests(unittest.TestCase):
    def test_initial_manifest_classification_is_conservative(self) -> None:
        gate = load_gate()
        v2_audit = gate.initial_manifest_row(
            "project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql"
        )
        v1_audit = gate.initial_manifest_row(
            "project_control/MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql"
        )
        main_candidate = gate.initial_manifest_row(
            "sql_v3_2/modeling/090B_create_compact_predictors_v33.sql"
        )
        self.assertEqual("AUDIT_ONLY", v2_audit["authority_status"])
        self.assertEqual("SUPERSEDED", v1_audit["authority_status"])
        self.assertEqual(
            "project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql",
            v1_audit["replacement_path"],
        )
        self.assertEqual("LEGACY_BLOCKED", main_candidate["authority_status"])
        self.assertEqual("false", main_candidate["allow_final_run"])

    def test_repository_audit_scans_history_without_blocking_on_history(self) -> None:
        gate = load_gate()
        dangerous = "SELECT COALESCE(valuenum, 0) FROM mimiciv_hosp.labevents"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sql").mkdir()
            (root / "sql/active.sql").write_text(dangerous, encoding="utf-8")
            (root / "sql/legacy.sql").write_text(dangerous, encoding="utf-8")
            rows = [
                manifest_row("sql/active.sql"),
                manifest_row(
                    "sql/legacy.sql",
                    authority_status="LEGACY_BLOCKED",
                    analysis_role="historical",
                    allow_final_run="false",
                ),
            ]
            findings = gate.audit_repository(
                root, rows, CONTRACT, {"sql/active.sql", "sql/legacy.sql"}
            )
        missing_to_zero = [
            item for item in findings if item["code"] == "LAB_MISSING_TO_ZERO"
        ]
        self.assertEqual(2, len(missing_to_zero), missing_to_zero)
        blocking_by_path = {
            item["path"]: item["blocks_final_run"] for item in missing_to_zero
        }
        self.assertTrue(blocking_by_path["sql/active.sql"])
        self.assertFalse(blocking_by_path["sql/legacy.sql"])

    def test_historical_derived_feature_is_recorded_but_nonblocking(self) -> None:
        gate = load_gate()
        legacy = manifest_row(
            "sql/legacy.sql",
            authority_status="LEGACY_BLOCKED",
            analysis_role="historical",
            allow_final_run="false",
        )
        findings = gate.scan_sql(
            "sql/legacy.sql",
            "SELECT bun FROM mimiciv_derived.chemistry",
            legacy,
            CONTRACT,
        )
        derived = [
            item for item in findings if item["code"] == "LAB_DERIVED_FORMAL_SOURCE"
        ]
        self.assertEqual(1, len(derived), findings)
        self.assertFalse(derived[0]["blocks_final_run"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
