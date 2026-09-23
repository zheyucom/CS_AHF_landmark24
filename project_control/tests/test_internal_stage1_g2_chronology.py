#!/usr/bin/env python3
"""Tests for G2 index-ICU chronology reconciliation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "project_control" / "reconcile_internal_stage1_g2_chronology.py"


def load_module():
    spec = importlib.util.spec_from_file_location("g2_chronology_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("G2 chronology script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_row(**updates):
    row = {
        "patient_id": "p1",
        "sex": "女",
        "visit_id": "v1",
        "episode_id": "v1_index",
        "t0_time": "2025-01-01 00:00:00",
        "t0_source": "explicit_document_event",
        "t12_time": "2025-01-01 12:00:00",
        "t60_time": "2025-01-03 12:00:00",
        "index_icu_outtime": "",
        "icu_out_source": "",
        "hospital_death_time": "",
        "hospital_discharge_time": "",
        "landmark_presence_status": "unknown",
        "entry_clusters": "1",
        "readmission_with_exit_flag": "0",
        "time_review_flags": "",
    }
    row.update(updates)
    return row


class InternalStage1G2ChronologyTests(unittest.TestCase):
    def test_direct_outtime_after_t12_proves_presence(self) -> None:
        g2 = load_module()
        result = g2.derive_t12_state(base_row(
            index_icu_outtime="2025-01-02 00:00:00",
            landmark_presence_status="present_at_T12_by_document_timeline",
        ))
        self.assertEqual("present_at_T12_direct", result["strict_t12_state"])
        self.assertEqual("eligible", result["strict_riskset_status"])

    def test_later_death_without_icu_exit_is_inferred_not_direct(self) -> None:
        g2 = load_module()
        result = g2.derive_t12_state(base_row(
            hospital_death_time="2025-01-02 00:00:00",
            landmark_presence_status="present_at_T12_by_document_timeline",
        ))
        self.assertEqual("unknown_no_direct_icu_presence", result["strict_t12_state"])
        self.assertEqual("present_at_T12_inferred_from_later_death", result["broad_t12_state"])
        self.assertEqual("exclude_strict_include_broad_sensitivity", result["strict_riskset_status"])

    def test_death_before_t12_is_not_eligible(self) -> None:
        g2 = load_module()
        result = g2.derive_t12_state(base_row(
            hospital_death_time="2025-01-01 06:00:00",
            landmark_presence_status="died_by_T12",
        ))
        self.assertEqual("died_by_T12", result["strict_t12_state"])
        self.assertEqual("not_eligible_pre_t12_death", result["strict_riskset_status"])

    def test_discharge_before_t12_conflicting_with_later_icu_out_is_unknown(self) -> None:
        g2 = load_module()
        result = g2.derive_t12_state(base_row(
            hospital_discharge_time="2025-01-01 08:00:00",
            index_icu_outtime="2025-01-02 00:00:00",
            landmark_presence_status="present_at_T12_by_document_timeline",
            time_review_flags="discharge_note_admission_field_disagrees",
        ))
        self.assertEqual("unknown_conflicting_exit_evidence", result["strict_t12_state"])
        self.assertEqual("not_eligible_time_conflict", result["strict_riskset_status"])

    def test_no_exit_with_later_live_discharge_remains_unknown(self) -> None:
        g2 = load_module()
        result = g2.derive_t12_state(base_row(
            hospital_discharge_time="2025-01-03 00:00:00",
            landmark_presence_status="unknown",
        ))
        self.assertEqual("unknown_no_direct_icu_presence", result["strict_t12_state"])
        self.assertEqual("unknown", result["broad_t12_state"])

    def test_t0_source_quality_is_explicit(self) -> None:
        g2 = load_module()
        self.assertEqual("direct", g2.classify_t0_source("explicit_document_event"))
        self.assertEqual("retrospective_explicit", g2.classify_t0_source("icu_discharge_note_admission_field"))
        self.assertEqual("proxy", g2.classify_t0_source("structured_proxy"))
        self.assertEqual("contextual", g2.classify_t0_source("AI_review_contextual_admission"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
