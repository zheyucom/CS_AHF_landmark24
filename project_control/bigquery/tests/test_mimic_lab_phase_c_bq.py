#!/usr/bin/env python3
"""Patient-free regressions for the BigQuery Phase-C aggregate lab audit."""

from __future__ import annotations

import importlib.util
import csv
import hashlib
import io
import json
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQL_PATH = PROJECT_ROOT / "sql_v3_3/bigquery/audits/118_audit_raw_lab_contract_phase_c_bq.sql"
RUNNER_PATH = PROJECT_ROOT / "project_control/bigquery/run_mimic_lab_phase_c_bq.py"
CAUSE_SQL_PATH = PROJECT_ROOT / "sql_v3_3/bigquery/audits/119_audit_raw_vs_derived_cause_phase_c_bq.sql"
CAUSE_RUNNER_PATH = PROJECT_ROOT / "project_control/bigquery/run_mimic_raw_derived_cause_bq.py"
RULE_PACK_PATH = PROJECT_ROOT / (
    "phase2_edit/bq_connectivity_update/skill_implementation/"
    "mimic-iv-data-cleaning/references/mimic-iv-lab-rules.json"
)
AUDIT_DIR = PROJECT_ROOT / "project_control/audits/bigquery_phase_c_20260920"
AUDIT_RUN_PATH = AUDIT_DIR / "run.json"
AUDIT_AGGREGATE_PATH = AUDIT_DIR / "aggregate_qc.csv"
CAUSE_AUDIT_DIR = PROJECT_ROOT / "project_control/audits/bigquery_raw_derived_cause_20260920"
CAUSE_RUN_PATH = CAUSE_AUDIT_DIR / "run.json"
CAUSE_AGGREGATE_PATH = CAUSE_AUDIT_DIR / "aggregate_qc.csv"
EXPECTED_HARD_GATE_CSV = """check_group,concept,reason_code,row_count
hard_gate,all,active_dictionary_mismatch,0
hard_gate,all,cohort_duplicate_stay_rows,0
hard_gate,all,cohort_invalid_boundary,0
hard_gate,all,cohort_missing_key,0
hard_gate,all,eligible_specimen_violation,0
hard_gate,all,eligible_time_violation,0
hard_gate,all,eligible_wrong_contract,0
hard_gate,all,quarantine_dictionary_mismatch,0
hard_gate,bun,bun_eligible_nonblood_or_wrong_item,0
"""


def required_text(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"required implementation is missing: {path.relative_to(PROJECT_ROOT)}")
    return path.read_text(encoding="utf-8")


def load_runner():
    if not RUNNER_PATH.is_file():
        raise AssertionError(f"required implementation is missing: {RUNNER_PATH.relative_to(PROJECT_ROOT)}")
    spec = importlib.util.spec_from_file_location("mimic_lab_phase_c_bq", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load BigQuery Phase-C runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module(path: Path, name: str):
    if not path.is_file():
        raise AssertionError(f"required implementation is missing: {path.relative_to(PROJECT_ROOT)}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load module: {path.relative_to(PROJECT_ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BigQuerySqlContractTests(unittest.TestCase):
    def test_sql_uses_bigquery_and_all_phase_c_itemids(self):
        sql = required_text(SQL_PATH)
        self.assertIn("YOUR_BILLING_PROJECT.ahf_work.dhf_lab_audit_cohort_snapshot_20260918", sql)
        self.assertIn("physionet-data.mimiciv_3_1_hosp.labevents", sql)
        self.assertIn("physionet-data.mimiciv_3_1_hosp.d_labitems", sql)
        for itemid in (
            50802, 50813, 50820, 50882, 50912, 50963, 50971,
            50983, 51003, 51006, 51222, 51237, 51265, 51301,
            51104, 51045, 50851, 51804, 51825, 51842, 51922, 51951,
        ):
            self.assertRegex(sql, rf"\b{itemid}\b")
        self.assertNotRegex(sql.lower(), r"\bcreate\s+(?:temp\s+)?table\b")
        self.assertNotRegex(sql.lower(), r"\bdrop\s+table\b")
        self.assertNotIn("::", sql)

    def test_sql_enforces_contract_time_specimen_and_result_rules(self):
        compact = re.sub(r"\s+", " ", required_text(SQL_PATH).lower())
        for token in (
            "greatest(le.charttime, coalesce(le.storetime, le.charttime))",
            "available_after_landmark",
            "storetime_before_charttime",
            "missing_specimen_id",
            "duplicate_specimen_itemid",
            "unknown_unit",
            "fluid_mismatch",
            "category_mismatch",
            "right_censored",
            "left_censored",
            "interval_censored",
        ):
            self.assertIn(token, compact)
        self.assertNotRegex(compact, r"coalesce\s*\(\s*(?:le\.)?(?:value|valuenum)\s*,\s*0")

    def test_final_output_is_aggregate_only(self):
        sql = required_text(SQL_PATH)
        marker = "-- FINAL_AGGREGATE_OUTPUT"
        self.assertIn(marker, sql)
        final = sql.split(marker, 1)[1].lower()
        for identifier in ("subject_id", "hadm_id", "stay_id", "labevent_id", "specimen_id"):
            self.assertNotRegex(final, rf"\b{identifier}\b")
        for output in ("check_group", "concept", "reason_code", "row_count"):
            self.assertRegex(final, rf"\b{output}\b")

    def test_dictionary_aggregates_group_the_source_status(self):
        compact = re.sub(r"\s+", " ", required_text(SQL_PATH).lower())
        self.assertGreaterEqual(
            len(re.findall(r"group by concept, dictionary_status", compact)),
            2,
            "BigQuery cannot group these expressions only by the reason_code output alias",
        )

    def test_cause_sql_is_aggregate_only_and_uses_registered_derived_keys(self):
        sql = required_text(CAUSE_SQL_PATH)
        compact = re.sub(r"\s+", " ", sql.lower())
        for token in (
            "physionet-data.mimiciv_3_1_derived.chemistry",
            "physionet-data.mimiciv_3_1_derived.bg",
            "specimen_id",
            "charttime",
            "late_result",
            "censored_or_non_numeric",
            "out_of_analysis_range",
            "wrong_contract",
            "duplicate_specimen_itemid",
            "raw_only",
            "derived_only",
            "both_unequal",
            "-- final_aggregate_output",
        ):
            self.assertIn(token, compact)
        for itemid in (50813, 50912, 51006):
            self.assertRegex(sql, rf"\b{itemid}\b")
        self.assertNotRegex(compact, r"\bcreate\s+(?:temp\s+)?table\b")
        self.assertNotRegex(compact, r"\bdrop\s+table\b")
        final = compact.split("-- final_aggregate_output", 1)[1]
        for identifier in ("subject_id", "hadm_id", "stay_id", "labevent_id", "specimen_id"):
            self.assertNotRegex(final, rf"\b{identifier}\b")
        for output in (
            "check_group",
            "concept",
            "metric",
            "cause_code",
            "stay_count",
            "event_count",
            "mean_abs_diff",
            "max_abs_diff",
        ):
            self.assertRegex(final, rf"\b{output}\b")


class RunnerContractTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_runner()

    def test_render_sql_replaces_only_valid_project_placeholder(self):
        template = "SELECT * FROM `YOUR_BILLING_PROJECT.ahf_work.cohort`"
        rendered = self.runner.render_sql(template, "project-abc-123")
        self.assertEqual("SELECT * FROM `project-abc-123.ahf_work.cohort`", rendered)
        with self.assertRaises(ValueError):
            self.runner.render_sql(template, "bad project; DROP TABLE x")
        with self.assertRaises(ValueError):
            self.runner.render_sql("SELECT 1", "project-abc-123")

    def test_commands_pin_job_project_location_and_billing_limit(self):
        dry = self.runner.build_bq_command(
            Path("/opt/google/bin/bq"), "project-abc-123", 20_000_000_000, dry_run=True
        )
        live = self.runner.build_bq_command(
            Path("/opt/google/bin/bq"), "project-abc-123", 20_000_000_000, dry_run=False
        )
        for command in (dry, live):
            joined = " ".join(command)
            self.assertIn("--project_id=project-abc-123", joined)
            self.assertIn("--location=US", joined)
            self.assertIn("--use_legacy_sql=false", joined)
            self.assertIn("--maximum_bytes_billed=20000000000", joined)
        self.assertIn("--dry_run", dry)
        self.assertIn("--format=json", dry)
        self.assertNotIn("--dry_run", live)
        self.assertIn("--format=csv", live)

    def test_dry_run_metadata_is_sanitized(self):
        raw = {
            "user_email": "must-not-be-saved@example.org",
            "principal_subject": "user:must-not-be-saved@example.org",
            "statistics": {
                "totalBytesProcessed": "12345",
                "query": {
                    "referencedTables": [
                        {
                            "projectId": "physionet-data",
                            "datasetId": "mimiciv_3_1_hosp",
                            "tableId": "labevents",
                        }
                    ]
                },
            },
        }
        sanitized = self.runner.sanitize_dry_run(raw)
        self.assertEqual(12345, sanitized["total_bytes_processed"])
        self.assertEqual(
            ["physionet-data.mimiciv_3_1_hosp.labevents"], sanitized["referenced_tables"]
        )
        self.assertNotIn("must-not-be-saved", json.dumps(sanitized))

    def test_aggregate_parser_fails_closed_on_positive_hard_gate(self):
        failed = EXPECTED_HARD_GATE_CSV.replace(
            "hard_gate,all,eligible_wrong_contract,0",
            "hard_gate,all,eligible_wrong_contract,2",
        )
        self.assertEqual(
            "passed_aggregate_qc",
            self.runner.classify_aggregate_csv(EXPECTED_HARD_GATE_CSV),
        )
        self.assertEqual("failed_qc", self.runner.classify_aggregate_csv(failed))
        with self.assertRaises(ValueError):
            self.runner.classify_aggregate_csv("concept,row_count\nbun,2\n")

    def test_aggregate_parser_requires_all_unique_gates_and_exact_schema(self):
        missing_gate = EXPECTED_HARD_GATE_CSV.replace(
            "hard_gate,all,cohort_missing_key,0\n", ""
        )
        duplicate_gate = EXPECTED_HARD_GATE_CSV + (
            "hard_gate,all,cohort_missing_key,0\n"
        )
        extra_identifier = EXPECTED_HARD_GATE_CSV.replace(
            "check_group,concept,reason_code,row_count",
            "check_group,concept,reason_code,row_count,stay_id",
        )
        for invalid in (missing_gate, duplicate_gate, extra_identifier):
            with self.assertRaises(ValueError):
                self.runner.classify_aggregate_csv(invalid)

    def test_default_cli_paths_do_not_hardcode_a_personal_home(self):
        source = required_text(RUNNER_PATH)
        self.assertNotIn(str(Path.home()), source)
        self.assertEqual(Path.home() / "google-cloud-sdk/bin/bq", self.runner.DEFAULT_BQ)
        self.assertEqual(Path.home() / "google-cloud-sdk/bin/gcloud", self.runner.DEFAULT_GCLOUD)

    def test_run_record_rejects_secret_fields(self):
        record = self.runner.build_run_record(
            run_id="bq_phase_c_test",
            status="not_run",
            sql_sha256="a" * 64,
            rule_pack_sha256="b" * 64,
            dry_run={"total_bytes_processed": 1, "referenced_tables": []},
        )
        serialized = json.dumps(record).lower()
        for forbidden in ("token", "password", "secret", "user_email", "account"):
            self.assertNotIn(forbidden, serialized)

    def test_cause_runner_fails_closed_on_missing_or_positive_gate(self):
        cause = load_module(CAUSE_RUNNER_PATH, "mimic_raw_derived_cause_bq")
        header = "check_group,concept,metric,cause_code,stay_count,event_count,mean_abs_diff,max_abs_diff\n"
        gates = [
            "hard_gate,all,contract,active_dictionary_mismatch,0,0,,",
            "hard_gate,all,contract,cohort_duplicate_stay_rows,0,0,,",
            "hard_gate,all,contract,cohort_invalid_boundary,0,0,,",
            "hard_gate,all,contract,cohort_missing_key,0,0,,",
            "hard_gate,all,contract,eligible_specimen_violation,0,0,,",
            "hard_gate,all,contract,eligible_time_violation,0,0,,",
            "hard_gate,all,contract,eligible_wrong_contract,0,0,,",
            "hard_gate,all,contract,quarantine_dictionary_mismatch,0,0,,",
            "hard_gate,bun,contract,bun_eligible_nonblood_or_wrong_item,0,0,,",
        ]
        passed = header + "\n".join(gates) + "\n"
        self.assertEqual("passed_aggregate_qc", cause.classify_cause_csv(passed))
        failed = passed.replace("eligible_time_violation,0,0", "eligible_time_violation,2,2")
        self.assertEqual("failed_qc", cause.classify_cause_csv(failed))
        with self.assertRaises(ValueError):
            cause.classify_cause_csv(header + "\n".join(gates[:-1]) + "\n")

    def test_cause_runner_has_no_personal_home_path(self):
        source = required_text(CAUSE_RUNNER_PATH)
        self.assertNotIn(str(Path.home()), source)

    def test_cause_evidence_is_aggregate_only_and_sanitized(self):
        record = json.loads(required_text(CAUSE_RUN_PATH))
        aggregate_text = required_text(CAUSE_AGGREGATE_PATH)
        reader = csv.DictReader(io.StringIO(aggregate_text))
        self.assertEqual(
            ["check_group", "concept", "metric", "cause_code", "stay_count", "event_count", "mean_abs_diff", "max_abs_diff"],
            reader.fieldnames,
        )
        rows = list(reader)
        self.assertEqual("passed_aggregate_qc", record["status"])
        self.assertEqual(len(rows), record["aggregate_row_count"])
        self.assertGreater(len(rows), 9)
        hard_gates = [row for row in rows if row["check_group"] == "hard_gate"]
        self.assertEqual(9, len(hard_gates))
        self.assertTrue(all(int(row["stay_count"]) == 0 for row in hard_gates))
        serialized = json.dumps(record).lower()
        for forbidden in ("subject_id", "hadm_id", "stay_id", "labevent_id", "specimen_id", "user_email", "principal_subject"):
            self.assertNotIn(forbidden, serialized)
        # `duplicate_specimen_itemid` is a reason code, not an exported identifier column.
        self.assertNotIn("subject_id", aggregate_text.lower())
        self.assertNotIn("hadm_id", aggregate_text.lower())
        self.assertNotIn("labevent_id", aggregate_text.lower())


class EvidenceArtifactTests(unittest.TestCase):
    def test_committed_evidence_is_aggregate_only_sanitized_and_reproducible(self):
        record = json.loads(required_text(AUDIT_RUN_PATH))
        aggregate_text = required_text(AUDIT_AGGREGATE_PATH)
        rows = list(csv.DictReader(io.StringIO(aggregate_text)))

        self.assertEqual(
            ["check_group", "concept", "reason_code", "row_count"],
            list(rows[0]),
        )
        self.assertEqual("passed_aggregate_qc", record["status"])
        self.assertEqual("aggregate_only_no_patient_export", record["scope"])
        self.assertEqual(len(rows), record["aggregate_row_count"])
        self.assertEqual(81, len(rows))
        self.assertEqual(
            hashlib.sha256(RULE_PACK_PATH.read_bytes()).hexdigest(),
            record["rule_pack_sha256"],
        )

        hard_gates = [row for row in rows if row["check_group"] == "hard_gate"]
        self.assertEqual(9, len(hard_gates))
        self.assertTrue(all(int(row["row_count"]) == 0 for row in hard_gates))

        serialized = json.dumps(record).lower()
        for forbidden in (
            "subject_id",
            "hadm_id",
            "stay_id",
            "labevent_id",
            "specimen_id",
            "user_email",
            "principal_subject",
        ):
            self.assertNotIn(forbidden, serialized + aggregate_text.lower())
        private_tables = [
            table
            for table in record["dry_run"]["referenced_tables"]
            if not table.startswith("physionet-data.")
        ]
        self.assertEqual(
            ["BILLING_PROJECT_REDACTED.ahf_work.dhf_lab_audit_cohort_snapshot_20260918"],
            private_tables,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
