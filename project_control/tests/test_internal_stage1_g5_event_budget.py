#!/usr/bin/env python3
"""Tests for the internal DHF Study-1 G5 event-budget gate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "audit_internal_stage1_g5_event_budget.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g5_event_budget_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G5 event-budget script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InternalStage1G5EventBudgetTests(unittest.TestCase):
    def test_effective_df_cap_uses_one_df_per_15_events_and_caps_at_10(self) -> None:
        g5 = load_module()
        self.assertEqual(0, g5.effective_df_cap(14))
        self.assertEqual(1, g5.effective_df_cap(15))
        self.assertEqual(2, g5.effective_df_cap(44))
        self.assertEqual(3, g5.effective_df_cap(45))
        self.assertEqual(10, g5.effective_df_cap(300))

    def test_16_deaths_block_adjusted_multivariable_association(self) -> None:
        g5 = load_module()
        result = g5.assess_endpoint(
            endpoint="strict_T12_hospital_death",
            events=16,
            endpoint_frozen=True,
            minimum_adjusted_df=3,
        )
        self.assertEqual(1, result["effective_df_cap"])
        self.assertFalse(result["adjusted_multivariable_allowed"])
        self.assertEqual("descriptive_and_pre_specified_crude_only", result["analysis_scope"])

    def test_62_events_would_allow_four_df_but_does_not_change_authorized_population(self) -> None:
        g5 = load_module()
        result = g5.assess_endpoint(
            endpoint="overall_phenotype_hospital_death_context_only",
            events=62,
            endpoint_frozen=True,
            minimum_adjusted_df=3,
        )
        self.assertEqual(4, result["effective_df_cap"])
        self.assertTrue(result["adjusted_multivariable_allowed"])
        self.assertEqual("adjusted_association_within_df_cap", result["analysis_scope"])

    def test_unfrozen_execution_level_endpoint_blocks_model_even_with_events(self) -> None:
        g5 = load_module()
        result = g5.assess_endpoint(
            endpoint="short_execution_level_composite",
            events=81,
            endpoint_frozen=False,
            minimum_adjusted_df=3,
        )
        self.assertEqual(5, result["effective_df_cap"])
        self.assertFalse(result["adjusted_multivariable_allowed"])
        self.assertEqual("endpoint_not_frozen_no_formal_model", result["analysis_scope"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
