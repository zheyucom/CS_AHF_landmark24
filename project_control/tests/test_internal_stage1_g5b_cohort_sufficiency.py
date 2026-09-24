#!/usr/bin/env python3
"""Tests for Study-1方案B cohort sufficiency and phenotype sensitivity audit."""

from __future__ import annotations

import importlib.util
import random
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "audit_internal_stage1_g5b_cohort_sufficiency.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g5b_cohort_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G5B cohort-sufficiency script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(visit_id: str, a: bool, b: bool, c: bool, *, unknown: bool = False):
    return {
        "patient_id": visit_id.split("_")[0],
        "visit_id": visit_id,
        "sex": "男",
        "age": "70",
        "t0_time": "2025-01-01 00:00:00",
        "a_hf_anchor_flag": str(int(a)),
        "b_decompensation_flag": str(int(b)),
        "c_ntprobnp_rule_in_flag": str(int(c)),
        "c_echo_abnormal_flag": "0",
        "c_iv_loop_order_proxy_flag": "0",
        "algorithmic_label_v1": "algorithmic_unknown" if unknown else "algorithmic_rule_not_supported",
        "old_pre_review_label": "unknown" if unknown else "not_supported",
        "a_source_refs": "a.csv#row=2",
        "a_evidence_excerpt": "心功能不全",
        "b_source_refs": "b.csv#row=2",
        "b_evidence_excerpt": "呼吸困难",
        "c_ntprobnp_rule_in_summary": "=2000@2025-01-01 01:00:00" if c else "",
        "c_ntprobnp_source_refs": "c.csv#row=2" if c else "",
        "echo_source_refs": "",
        "c_iv_loop_order_summary": "",
        "c_iv_loop_source_refs": "",
        "alternative_mentioned_flag": "0",
    }


class InternalStage1G5BCohortSufficiencyTests(unittest.TestCase):
    def test_abc_pattern_preserves_each_domain_instead_of_collapsing_missing_to_negative(self) -> None:
        g5b = load_module()
        self.assertEqual("ABC", g5b.abc_pattern(row("1_1", True, True, True)))
        self.assertEqual("AB_without_C", g5b.abc_pattern(row("2_1", True, True, False)))
        self.assertEqual("BC_without_A", g5b.abc_pattern(row("3_1", False, True, True)))
        self.assertEqual("AC_without_B", g5b.abc_pattern(row("4_1", True, False, True)))

    def test_sample_size_does_not_authorize_relaxing_phenotype(self) -> None:
        g5b = load_module()
        result = g5b.assess_cohort_sufficiency(n=773, events=62)
        self.assertEqual(4, result["effective_df_cap"])
        self.assertEqual("adequate_for_description_and_low_dimensional_association", result["assessment"])
        self.assertFalse(result["prediction_model_development_supported"])
        self.assertFalse(result["relax_phenotype_for_sample_size"])

    def test_wilson_interval_for_main_mortality_is_reasonably_precise(self) -> None:
        g5b = load_module()
        low, high = g5b.wilson_interval(62, 773)
        self.assertGreater(low, 0.05)
        self.assertLess(high, 0.11)
        self.assertLess(high - low, 0.04)

    def test_near_boundary_review_sampling_is_deterministic_and_outcome_blind(self) -> None:
        g5b = load_module()
        rows = [
            *(row(f"{i}_1", False, True, True) for i in range(1, 9)),
            *(row(f"{i}_1", True, False, True) for i in range(20, 28)),
            row("99_1", True, True, True),
        ]
        first = g5b.select_supplemental_review(rows, set(), {"BC_without_A": 3, "AC_without_B": 2})
        shuffled = list(rows)
        random.Random(20260924).shuffle(shuffled)
        second = g5b.select_supplemental_review(shuffled, set(), {"BC_without_A": 3, "AC_without_B": 2})
        self.assertEqual([r["visit_id"] for r in first], [r["visit_id"] for r in second])
        self.assertEqual(5, len(first))
        forbidden = {"hospital_outcome_status", "death", "mortality", "outcome"}
        for selected in first:
            self.assertTrue(forbidden.isdisjoint(selected))
            self.assertIn(selected["review_stratum"], {"BC_without_A", "AC_without_B"})

    def test_ab_without_c_profile_separates_unavailable_from_measured_not_supportive(self) -> None:
        g5b = load_module()
        unavailable = row("1_1", True, True, False)
        unavailable.update({
            "c_ntprobnp_pre12_measured_flag": "0",
            "c_echo_result_available_flag": "0",
            "alternative_mentioned_flag": "1",
        })
        measured_not_supportive = row("2_1", True, True, False)
        measured_not_supportive.update({
            "c_ntprobnp_pre12_measured_flag": "1",
            "c_echo_result_available_flag": "1",
            "alternative_mentioned_flag": "0",
        })

        profile = g5b.summarize_ab_without_c([unavailable, measured_not_supportive])

        self.assertEqual(2, profile["AB_without_C_n"])
        self.assertEqual(1, profile["ntprobnp_not_available_n"])
        self.assertEqual(1, profile["ntprobnp_measured_below_rule_in_n"])
        self.assertEqual(1, profile["echo_not_available_n"])
        self.assertEqual(1, profile["echo_available_not_abnormal_n"])
        self.assertEqual(1, profile["alternative_diagnosis_mentioned_n"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
