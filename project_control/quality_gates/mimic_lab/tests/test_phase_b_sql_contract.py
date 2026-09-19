#!/usr/bin/env python3
"""Patient-free regressions for the Phase-B raw laboratory SQL contract."""

from __future__ import annotations

import csv
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = ROOT / "project_control/quality_gates/mimic_lab/lab_contract_v1.json"
MANIFEST_PATH = ROOT / "project_control/PIPELINE_AUTHORITY_MANIFEST.csv"
RAW_LAYER = ROOT / "sql_v3_3/executable/060_create_raw_lab_contract_layer_v1.sql"
DOWNSTREAM = {
    "061A": ROOT / "sql_v3_3/executable/061A_create_ahf_evidence_table_12h_v2.sql",
    "061C": ROOT / "sql_v3_3/executable/061C_create_pre12_overt_cs_flags_v2.sql",
    "061E": ROOT / "sql_v3_3/executable/061E_create_post12_overt_cs_future48h_v2.sql",
    "063A": ROOT / "sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql",
    "090B": ROOT / "sql_v3_3/modeling/090B_create_compact_predictors_v34.sql",
}


def sql_text(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())


class ContractDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.by_concept = {
            rule["concept"]: rule
            for rule in cls.contract["rules"]
            if rule.get("status") == "active"
        }

    def test_all_formal_predictor_and_outcome_labs_have_exact_contracts(self) -> None:
        expected = {
            "base_excess": 50802,
            "lactate": 50813,
            "ph": 50820,
            "bicarbonate": 50882,
            "creatinine": 50912,
            "ntprobnp": 50963,
            "potassium": 50971,
            "sodium": 50983,
            "bun": 51006,
            "hemoglobin": 51222,
            "inr": 51237,
            "platelet": 51265,
            "wbc": 51301,
        }
        observed = {
            concept: rule["allow"][0]["itemid"]
            for concept, rule in self.by_concept.items()
            if concept in expected
        }
        self.assertEqual(expected, observed)
        for concept in expected:
            allow = self.by_concept[concept]["allow"]
            self.assertEqual(1, len(allow), concept)
            self.assertEqual("Blood", allow[0]["fluid"], concept)
            self.assertTrue(allow[0]["category"], concept)

    def test_inr_null_unit_is_explicitly_dimensionless_not_unknown(self) -> None:
        inr = self.by_concept["inr"]["allow"][0]
        self.assertEqual("dimensionless_null", inr["unit_policy"])
        self.assertEqual([], inr["units"])

    def test_official_ranges_are_flags_not_claimed_physiologic_limits(self) -> None:
        self.assertEqual(
            {"lower": 0, "lower_inclusive": False, "upper": 300, "upper_inclusive": True},
            self.by_concept["bun"]["official_analysis_range"],
        )
        for concept in ("ph", "base_excess", "inr"):
            self.assertIsNone(self.by_concept[concept]["official_analysis_range"])


class RawLayerSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = sql_text(RAW_LAYER)

    def test_raw_layer_builds_four_versioned_relations(self) -> None:
        for relation in (
            "lab_contract_v1",
            "lab_quarantine_item_v1",
            "lab_event_classified_v1",
            "lab_eligible_v1",
        ):
            self.assertIn(f"study_ahf_v3_3.{relation}", self.sql)

    def test_provenance_and_original_values_are_preserved(self) -> None:
        required = {
            "labevent_id", "specimen_id", "subject_id", "hadm_id", "itemid",
            "label", "fluid", "category", "charttime", "storetime",
            "availability_time", "value", "valuenum", "valueuom",
            "ref_range_lower", "ref_range_upper", "flag", "priority", "comments",
            "result_class", "censor_type", "lower_bound", "upper_bound",
            "official_range_outlier_flag", "analysis_exclusion_reason",
            "quarantine_reason",
        }
        self.assertFalse(required - set(re.findall(r"\b[a-z_][a-z0-9_]*\b", self.sql)))

    def test_availability_duplicate_and_wrong_fluid_fail_closed(self) -> None:
        self.assertRegex(
            self.sql,
            r"greatest\s*\(\s*le\.charttime\s*,\s*coalesce\s*\(\s*le\.storetime\s*,\s*le\.charttime",
        )
        self.assertIn("le.storetime < le.charttime", self.sql)
        self.assertRegex(
            self.sql,
            r"partition by\s+le\.specimen_id\s*,\s*le\.itemid",
        )
        for itemid in (51104, 51045, 50851, 51804, 51825, 51842, 51922, 51951):
            self.assertRegex(self.sql, rf"\b{itemid}\b")
        self.assertIn("wrong_fluid", self.sql)

    def test_censoring_is_retained_but_not_fabricated_as_exact_numeric(self) -> None:
        for token in ("right_censored", "left_censored", "interval_censored"):
            self.assertIn(token, self.sql)
        self.assertIn("censor_type", self.sql)
        self.assertIn("lower_bound", self.sql)
        self.assertIn("upper_bound", self.sql)
        self.assertRegex(
            self.sql,
            r"case\s+when\s+[^;]*result_class\s*=\s*'exact_numeric'[^;]*analysis_value",
        )

    def test_inr_dimensionless_null_is_the_only_null_unit_exception(self) -> None:
        self.assertIn("dimensionless_null", self.sql)
        self.assertRegex(
            self.sql,
            r"unit_policy\s*=\s*'dimensionless_null'[^;]{0,240}valueuom\s+is\s+null",
        )


class DownstreamSqlTests(unittest.TestCase):
    def test_all_revised_paths_use_the_raw_contract_layer(self) -> None:
        forbidden = (
            "mimiciv_derived.bg",
            "mimiciv_derived.chemistry",
            "mimiciv_derived.complete_blood_count",
            "mimiciv_derived.coagulation",
        )
        for name, path in DOWNSTREAM.items():
            sql = sql_text(path)
            self.assertIn("study_ahf_v3_3.lab_eligible_v1", sql, name)
            for table in forbidden:
                self.assertNotIn(table, sql, name)

    def test_every_revised_path_gates_on_availability_time(self) -> None:
        for name, path in DOWNSTREAM.items():
            sql = sql_text(path)
            self.assertIn("availability_time", sql, name)
            self.assertRegex(sql, r"availability_time\s*[<>]=?", name)
            self.assertRegex(sql, r"le\.charttime\s*>=", name)
            self.assertRegex(sql, r"le\.charttime\s*<", name)

    def test_ntprobnp_threshold_is_three_state(self) -> None:
        sql = sql_text(DOWNSTREAM["061A"])
        for token in (
            "definitely_above",
            "definitely_below",
            "indeterminate_censored",
        ):
            self.assertIn(token, sql)
        for threshold in (300, 900, 1800):
            self.assertIn(f"ntprobnp_{threshold}_state", sql)

    def test_threshold_paths_ignore_missing_or_unparsed_results(self) -> None:
        for name in ("061A", "061C", "061E", "063A"):
            sql = sql_text(DOWNSTREAM[name])
            self.assertRegex(
                sql,
                r"result_class\s+in\s*\(\s*'exact_numeric'\s*,\s*'right_censored'\s*,\s*'left_censored'\s*,\s*'interval_censored'",
                name,
            )

    def test_continuous_rollups_use_analysis_value_only(self) -> None:
        sql = sql_text(DOWNSTREAM["090B"])
        self.assertNotRegex(sql, r"\b(?:value|valuenum)\s*\)")
        self.assertIn("analysis_value", sql)

    def test_episode_join_audit_detects_multi_match(self) -> None:
        for name in ("061A", "061C", "061E", "063A", "090B"):
            sql = sql_text(DOWNSTREAM[name])
            self.assertIn("episode_match_count", sql, name)
            self.assertIn("ambiguous_episode_match", sql, name)

    def test_support_windows_count_infusions_that_overlap_each_window(self) -> None:
        sql = sql_text(DOWNSTREAM["063A"])
        self.assertRegex(
            sql,
            r"pre_agent as \([^;]*va\.starttime\s*<\s*b\.landmark12_time[^;]*endtime[^;]*>\s*b\.intime",
        )
        self.assertRegex(
            sql,
            r"post_agent as \([^;]*va\.starttime\s*<\s*b\.observed_until_time[^;]*endtime[^;]*>\s*b\.landmark12_time",
        )

    def test_new_sql_is_registered_but_not_promoted_without_database_qc(self) -> None:
        with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
            rows = {row["path"]: row for row in csv.DictReader(handle)}
        for path in (RAW_LAYER, *DOWNSTREAM.values()):
            relative = path.relative_to(ROOT).as_posix()
            self.assertIn(relative, rows)
            self.assertNotEqual("ACTIVE", rows[relative]["authority_status"])
            self.assertEqual("false", rows[relative]["allow_final_run"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
