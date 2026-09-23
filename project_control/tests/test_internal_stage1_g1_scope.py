#!/usr/bin/env python3
"""Tests for the internal DHF Stage-1 G1 scope/calendar audit."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "audit_internal_stage1_g1_scope.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g1_scope_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G1 scope audit cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InternalStage1G1ScopeTests(unittest.TestCase):
    def test_contract_limits_inference_to_echo_assessed_frame(self) -> None:
        g1 = load_module()
        rows = [
            {"candidate_rule_support_flag": "1", "candidate_riskset_flag": "1", "bedside_echo_report_available": "1"},
            {"candidate_rule_support_flag": "1", "candidate_riskset_flag": "0", "bedside_echo_report_available": "0"},
            {"candidate_rule_support_flag": "0", "candidate_riskset_flag": "0", "bedside_echo_report_available": "0"},
        ]
        contract = g1.build_scope_contract(rows, {"2023": 2, "2024": 1}, "2023", "2024")
        self.assertEqual("echo_assessed_adult_icu_candidate_frame", contract["scope_denominator"])
        self.assertFalse(contract["independent_all_icu_denominator_available"])
        self.assertFalse(contract["can_estimate_all_icu_dhf_prevalence"])
        self.assertEqual(3, contract["candidate_n"])
        self.assertEqual(2, contract["rule_supported_n"])
        self.assertEqual(1, contract["structured_echo_report_available_n"])
        self.assertEqual(2, contract["structured_echo_report_missing_n"])

    def test_2024_is_incomplete_and_not_trend_eligible(self) -> None:
        g1 = load_module()
        contract = g1.build_scope_contract([], {"2021": 10, "2024": 2, "2025": 4}, "2021", "2025")
        by_year = {row["calendar_year"]: row for row in contract["calendar_status"]}
        self.assertEqual("incomplete_calendar_period", by_year["2024"]["completeness_status"])
        self.assertFalse(by_year["2024"]["annual_trend_eligible"])
        self.assertEqual("partial_observation_boundary", by_year["2025"]["completeness_status"])
        self.assertFalse(by_year["2025"]["annual_trend_eligible"])

    def test_non_boundary_years_are_not_claimed_complete_without_external_proof(self) -> None:
        g1 = load_module()
        contract = g1.build_scope_contract([], {"2021": 10, "2022": 11, "2023": 9}, "2021", "2023")
        by_year = {row["calendar_year"]: row for row in contract["calendar_status"]}
        self.assertEqual("completeness_not_independently_proven", by_year["2022"]["completeness_status"])
        self.assertFalse(by_year["2022"]["annual_trend_eligible"])

    def test_prohibited_claims_cover_known_overstatements(self) -> None:
        g1 = load_module()
        contract = g1.build_scope_contract([], {}, "", "")
        joined = "|".join(contract["prohibited_claims"])
        self.assertIn("全院全部成人ICU", joined)
        self.assertIn("连续完整五年", joined)
        self.assertIn("2024年病例真实下降", joined)

    def test_write_outputs_creates_machine_readable_g1_artifacts(self) -> None:
        g1 = load_module()
        contract = g1.build_scope_contract(
            [{"candidate_rule_support_flag": "1", "candidate_riskset_flag": "1", "bedside_echo_report_available": "0"}],
            {"2024": 1},
            "2024",
            "2024",
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            g1.write_outputs(out, contract, [])
            self.assertTrue((out / "scope_contract.json").exists())
            self.assertTrue((out / "calendar_completeness.csv").exists())
            self.assertTrue((out / "echo_observability.csv").exists())
            self.assertTrue((out / "prohibited_interpretations.csv").exists())
            qc = json.loads((out / "qc.json").read_text())
            self.assertEqual("PASS_SCOPE_LOCKED_WITH_KNOWN_LIMITATIONS", qc["status"])
            self.assertFalse(qc["all_icu_prevalence_claim_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
