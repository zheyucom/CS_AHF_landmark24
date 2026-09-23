#!/usr/bin/env python3
"""Tests for the internal DHF A/B/C phenotype contract and G3 ledger."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "build_internal_stage1_g3_phenotype.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g3_phenotype_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G3 phenotype script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InternalStage1G3PhenotypeTests(unittest.TestCase):
    def test_ntprobnp_uses_age_specific_rule_in_thresholds(self) -> None:
        g3 = load_module()
        self.assertEqual(450.0, g3.ntprobnp_rule_in(49, "450")["threshold_pg_ml"])
        self.assertEqual("rule_in", g3.ntprobnp_rule_in(49, "450")["status"])
        self.assertEqual(900.0, g3.ntprobnp_rule_in(50, "900")["threshold_pg_ml"])
        self.assertEqual(900.0, g3.ntprobnp_rule_in(75, "900")["threshold_pg_ml"])
        self.assertEqual(1800.0, g3.ntprobnp_rule_in(76, "1800")["threshold_pg_ml"])

    def test_ntprobnp_preserves_inequality_semantics(self) -> None:
        g3 = load_module()
        high = g3.ntprobnp_rule_in(80, ">25000")
        self.assertEqual(">", high["qualifier"])
        self.assertEqual("rule_in", high["status"])
        low = g3.ntprobnp_rule_in(40, "<300")
        self.assertEqual("<", low["qualifier"])
        self.assertEqual("below_rule_in", low["status"])

    def test_unparseable_ntprobnp_is_unknown_not_negative(self) -> None:
        g3 = load_module()
        result = g3.ntprobnp_rule_in(70, "无法测定")
        self.assertEqual("unknown_unparseable", result["status"])
        self.assertIsNone(result["numeric_bound_pg_ml"])

    def test_treatment_only_supports_main_but_not_strict_phenotype(self) -> None:
        g3 = load_module()
        result = g3.classify_phenotype({
            "a_hf_anchor": True,
            "b_decompensation": True,
            "c_ntprobnp_rule_in": False,
            "c_echo_abnormal": False,
            "c_iv_loop_order_proxy": True,
            "old_pre_review_label": "not_supported",
            "alternative_mentioned": False,
        })
        self.assertTrue(result["main_rule_supported"])
        self.assertFalse(result["strict_objective_rule_supported"])
        self.assertEqual("treatment_proxy_only_C", result["c_support_type"])

    def test_objective_c_supports_both_main_and_strict(self) -> None:
        g3 = load_module()
        result = g3.classify_phenotype({
            "a_hf_anchor": True,
            "b_decompensation": True,
            "c_ntprobnp_rule_in": True,
            "c_echo_abnormal": False,
            "c_iv_loop_order_proxy": False,
            "old_pre_review_label": "not_supported",
            "alternative_mentioned": False,
        })
        self.assertTrue(result["main_rule_supported"])
        self.assertTrue(result["strict_objective_rule_supported"])
        self.assertEqual("objective_C", result["c_support_type"])

    def test_missing_anchor_uncertainty_is_not_forced_negative(self) -> None:
        g3 = load_module()
        result = g3.classify_phenotype({
            "a_hf_anchor": False,
            "b_decompensation": True,
            "c_ntprobnp_rule_in": True,
            "c_echo_abnormal": False,
            "c_iv_loop_order_proxy": False,
            "old_pre_review_label": "unknown",
            "alternative_mentioned": False,
        })
        self.assertEqual("algorithmic_unknown", result["algorithmic_label"])

    def test_alternative_diagnosis_triggers_review_not_automatic_exclusion(self) -> None:
        g3 = load_module()
        result = g3.classify_phenotype({
            "a_hf_anchor": True,
            "b_decompensation": True,
            "c_ntprobnp_rule_in": True,
            "c_echo_abnormal": False,
            "c_iv_loop_order_proxy": False,
            "old_pre_review_label": "probable_dhf",
            "alternative_mentioned": True,
        })
        self.assertTrue(result["main_rule_supported"])
        self.assertTrue(result["clinical_review_priority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
