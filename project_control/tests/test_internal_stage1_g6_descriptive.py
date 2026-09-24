#!/usr/bin/env python3
"""Tests for Study-1 G6 descriptive and T0 factor-availability audit."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "build_internal_stage1_g6_descriptive.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g6_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G6 script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InternalStage1G6DescriptiveTests(unittest.TestCase):
    def test_numeric_summary_reports_median_and_quartiles_without_imputation(self) -> None:
        g6 = load_module()
        result = g6.numeric_summary([40, 50, "", 70, 80])
        self.assertEqual(4, result["available_n"])
        self.assertEqual(60.0, result["median"])
        self.assertEqual(47.5, result["q1"])
        self.assertEqual(72.5, result["q3"])

    def test_factor_availability_does_not_promote_post_t0_or_phenotype_fields(self) -> None:
        g6 = load_module()
        rows = [{"age": "70", "sex": "男"}, {"age": "80", "sex": "女"}]
        manifest = {row["factor"]: row for row in g6.build_t0_factor_manifest(rows)}
        self.assertEqual("eligible_for_pre_effect_freeze", manifest["age"]["gate_status"])
        self.assertEqual("eligible_for_pre_effect_freeze", manifest["sex"]["gate_status"])
        self.assertEqual("not_yet_mapped", manifest["chronic_comorbidity_set"]["gate_status"])
        self.assertEqual("not_yet_mapped", manifest["admission_route"]["gate_status"])
        self.assertEqual("excluded_post_T0", manifest["early_laboratory_or_vital_values"]["gate_status"])
        self.assertNotIn("a_hf_anchor_flag", manifest)
        self.assertNotIn("b_decompensation_flag", manifest)

    def test_main_summary_preserves_outcome_unknown_instead_of_counting_as_alive(self) -> None:
        g6 = load_module()
        rows = [
            {"age": "60", "sex": "男", "hospital_outcome_status": "hospital_death"},
            {"age": "70", "sex": "女", "hospital_outcome_status": "alive_hospital_discharge"},
            {"age": "80", "sex": "女", "hospital_outcome_status": "outcome_unknown"},
        ]
        summary = g6.summarize_main_cohort(rows)
        self.assertEqual(3, summary["n"])
        self.assertEqual(1, summary["hospital_death_n"])
        self.assertEqual(1, summary["alive_hospital_discharge_n"])
        self.assertEqual(1, summary["outcome_unknown_n"])

    def test_admission_route_normalization_preserves_emergency_outpatient_and_transfer(self) -> None:
        g6 = load_module()
        self.assertEqual("emergency", g6.normalize_admission_route("入院途径 : 急诊"))
        self.assertEqual("outpatient", g6.normalize_admission_route("入院途径 : 门诊"))
        self.assertEqual("transfer", g6.normalize_admission_route("入院途径 : 转诊"))
        self.assertEqual("unknown", g6.normalize_admission_route(""))

    def test_comorbidity_source_audit_keeps_missing_pre_t0_diagnosis_unknown(self) -> None:
        g6 = load_module()
        main = {
            "1": {"t0_time": "2025-01-01 12:00:00"},
            "2": {"t0_time": "2025-01-01 12:00:00"},
            "3": {"t0_time": "2025-01-01 12:00:00"},
        }
        diagnoses = [
            {"就诊号": "1", "诊断时间": "2025-01-01 10:00:00", "诊断名称": "高血压"},
            {"就诊号": "2", "诊断时间": "2025-01-01 13:00:00", "诊断名称": "糖尿病"},
        ]
        admissions = [
            {"就诊号": "1", "创建日期": "2025-01-01 11:00:00"},
            {"就诊号": "2", "创建日期": "2025-01-01 14:00:00"},
            {"就诊号": "3", "创建日期": "2025-01-01 11:30:00"},
        ]
        result = g6.audit_comorbidity_sources(main, diagnoses, admissions)
        self.assertEqual(1, result["pre_T0_diagnosis_visit_n"])
        self.assertEqual(2, result["no_pre_T0_diagnosis_record_n"])
        self.assertEqual(3, result["admission_history_visit_n"])
        self.assertEqual(2, result["admission_history_created_by_T0_n"])
        self.assertFalse(result["absence_can_be_interpreted_as_no_comorbidity"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
