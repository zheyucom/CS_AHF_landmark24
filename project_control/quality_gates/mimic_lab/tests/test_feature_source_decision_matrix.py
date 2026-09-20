#!/usr/bin/env python3
"""Contracts for the versioned MIMIC laboratory feature-source decision."""

from __future__ import annotations

import csv
import hashlib
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MATRIX_PATH = PROJECT_ROOT / "project_control/MIMIC_LAB_FEATURE_SOURCE_DECISION_MATRIX_V1.csv"
MANIFEST_PATH = PROJECT_ROOT / "project_control/PIPELINE_AUTHORITY_MANIFEST.csv"
V2_PATH = PROJECT_ROOT / "sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql"
V3_RELATIVE = "sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v3.sql"
V3_PATH = PROJECT_ROOT / V3_RELATIVE
AUDIT_RELATIVE = "sql_v3_3/audits/122_audit_lactate_window_contract_v3.sql"
AUDIT_PATH = PROJECT_ROOT / AUDIT_RELATIVE
PREDICTOR_RELATIVE = "sql_v3_3/modeling/090B_create_compact_predictors_v34.sql"
PREDICTOR_PATH = PROJECT_ROOT / PREDICTOR_RELATIVE

EXPECTED_FIELDS = [
    "feature_key",
    "feature_name",
    "concept",
    "research_role",
    "source_sql",
    "source_relation",
    "source_policy",
    "sample_window",
    "availability_window",
    "aggregation",
    "sequence_order",
    "value_policy",
    "missingness_policy",
    "derived_policy",
    "evidence_refs",
    "freeze_status",
]


def required_text(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"required file is missing: {path.relative_to(PROJECT_ROOT)}")
    return path.read_text(encoding="utf-8")


def required_feature_keys() -> set[str]:
    predictor_features = {
        "lactate_max",
        "lactate_first",
        "lactate_last",
        "lactate_delta",
        "ph_min",
        "baseexcess_min",
        "creatinine_max",
        "creatinine_first",
        "creatinine_last",
        "creatinine_delta",
        "bun_max",
        "sodium_min",
        "sodium_max",
        "potassium_min",
        "potassium_max",
        "chem_bicarbonate_min",
        "wbc_max",
        "hemoglobin_min",
        "platelet_min",
        "inr_max",
    }
    keys = {f"{PREDICTOR_RELATIVE}::{feature}" for feature in predictor_features}
    keys.update(
        {
            "sql_v3_3/executable/061A_create_ahf_evidence_table_12h_v2.sql::ntprobnp_max_early12",
            "sql_v3_3/executable/061A_create_ahf_evidence_table_12h_v2.sql::ntprobnp_min_early12",
            "sql_v3_3/executable/061C_create_pre12_overt_cs_flags_v2.sql::pre12_lactate_max",
            "sql_v3_3/executable/061E_create_post12_overt_cs_future48h_v2.sql::post12_lactate_max",
            f"{V3_RELATIVE}::pre12_lactate_contract_max",
            f"{V3_RELATIVE}::pre12_lactate_contract_min",
            f"{V3_RELATIVE}::pre12_lactate_contract_last",
            f"{V3_RELATIVE}::post12_lactate_contract_max",
            f"{V3_RELATIVE}::lactate_delta_ge2_from_last_flag",
        }
    )
    return keys


class FeatureSourceMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        text = required_text(MATRIX_PATH)
        reader = csv.DictReader(text.splitlines())
        self.assertEqual(EXPECTED_FIELDS, reader.fieldnames)
        self.rows = list(reader)

    def test_matrix_has_unique_complete_feature_catalog(self):
        keys = [row["feature_key"] for row in self.rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(required_feature_keys().issubset(set(keys)))
        for row in self.rows:
            self.assertEqual(
                f"{row['source_sql']}::{row['feature_name']}",
                row["feature_key"],
            )
            self.assertTrue((PROJECT_ROOT / row["source_sql"]).is_file())

    def test_all_features_use_raw_contract_without_silent_fill(self):
        for row in self.rows:
            self.assertEqual("study_ahf_v3_3.lab_eligible_v1", row["source_relation"])
            self.assertEqual("raw_contract_primary", row["source_policy"])
            self.assertEqual("preserve_null_no_derived_fill", row["missingness_policy"])
            self.assertEqual("reconciliation_only", row["derived_policy"])
            self.assertEqual("candidate_not_frozen", row["freeze_status"])
            for evidence in row["evidence_refs"].split(";"):
                self.assertTrue((PROJECT_ROOT / evidence).is_file(), evidence)

    def test_first_last_and_delta_have_deterministic_sequence_contracts(self):
        ordered = [
            row
            for row in self.rows
            if row["aggregation"] in {"first", "last", "delta_last_minus_first", "threshold_postmax_minus_last_ge2"}
        ]
        self.assertGreaterEqual(len(ordered), 7)
        for row in ordered:
            self.assertEqual("charttime_then_labevent_id", row["sequence_order"])
        delta_rows = [row for row in ordered if "delta" in row["aggregation"] or "minus" in row["aggregation"]]
        self.assertGreaterEqual(len(delta_rows), 3)


class VersionedSqlContractTests(unittest.TestCase):
    def test_historical_v2_is_unchanged(self):
        digest = hashlib.sha256(V2_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            "99e5bd01e752c77c0d81b1f710967c542ffa752f9320fb259998b24d15969966",
            digest,
        )

    def test_v3_separates_pre_and_post_sample_and_availability_windows(self):
        compact = re.sub(r"\s+", " ", required_text(V3_PATH).lower())
        self.assertIn("outcome_063a_candidate_hd_outcomes_overall_v3", compact)
        pre_contract = (
            "le.charttime >= b.intime and le.charttime < b.landmark12_time "
            "and le.availability_time >= b.intime "
            "and le.availability_time < b.landmark12_time"
        )
        post_contract = (
            "le.charttime >= b.landmark12_time "
            "and le.charttime < b.observed_until_time "
            "and le.availability_time >= b.landmark12_time "
            "and le.availability_time < b.observed_until_time"
        )
        self.assertIn(pre_contract, compact)
        self.assertIn(post_contract, compact)
        self.assertIn("then 'pre12' else 'post12' end as lab_window", compact)
        self.assertIn("order by charttime desc, labevent_id desc", compact)

    def test_v3_is_registered_but_cannot_enter_a_final_run(self):
        manifest = required_text(MANIFEST_PATH)
        expected = f"{V3_RELATIVE},outcome,LEGACY_BLOCKED,historical,postgres,,false,"
        self.assertIn(expected, manifest)

    def test_non_audit_v33_sql_does_not_use_derived_laboratory_tables(self):
        offenders: list[str] = []
        for path in (PROJECT_ROOT / "sql_v3_3").rglob("*.sql"):
            if "audits" in path.parts:
                continue
            compact = re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())
            if "mimiciv_derived.bg" in compact or "mimiciv_derived.chemistry" in compact:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
        self.assertEqual([], offenders)

    def test_time_contract_audit_is_registered_and_aggregate_only(self):
        compact = re.sub(r"\s+", " ", required_text(AUDIT_PATH).lower())
        for token in (
            "excluded_late_event_n",
            "affected_stay_n",
            "pre12_max_changed_n",
            "pre12_min_changed_n",
            "pre12_last_changed_n",
            "post12_max_changed_n",
            "new_ge2_changed_n",
            "worsen_ge4_changed_n",
            "delta_ge2_changed_n",
            "composite_changed_n",
            "-- final_aggregate_output",
        ):
            self.assertIn(token, compact)
        final = compact.split("-- final_aggregate_output", 1)[1]
        for identifier in ("subject_id", "hadm_id", "stay_id", "labevent_id"):
            self.assertNotRegex(final, rf"\b{identifier}\b")
        manifest = required_text(MANIFEST_PATH)
        expected = f"{AUDIT_RELATIVE},audit,AUDIT_ONLY,audit,postgres,,false,"
        self.assertIn(expected, manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
