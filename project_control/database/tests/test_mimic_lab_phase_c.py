#!/usr/bin/env python3
"""Patient-free regressions for the Phase-C PostgreSQL runner."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "project_control/database/mimic_lab_phase_c.py"


def load_runner():
    if not RUNNER_PATH.exists():
        raise AssertionError("mimic_lab_phase_c.py has not been implemented")
    spec = importlib.util.spec_from_file_location("mimic_lab_phase_c", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("mimic_lab_phase_c.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PhaseCPlanTests(unittest.TestCase):
    def test_plan_order_places_contract_gate_before_all_consumers(self) -> None:
        runner = load_runner()
        self.assertEqual(
            [
                "sql_v3_3/executable/060_create_raw_lab_contract_layer_v1.sql",
                "sql_v3_3/audits/116_audit_raw_lab_contract_phase_c.sql",
                "sql_v3_3/executable/061A_create_ahf_evidence_table_12h_v2.sql",
                "sql_v3_3/executable/061C_create_pre12_overt_cs_flags_v2.sql",
                "sql_v3_3/executable/061E_create_post12_overt_cs_future48h_v2.sql",
                "sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql",
                "sql_v3_3/modeling/090B_create_compact_predictors_v34.sql",
                "sql_v3_3/audits/117_audit_raw_vs_derived_phase_c.sql",
            ],
            runner.PHASE_C_PLAN,
        )

    def test_every_planned_sql_is_inside_project_and_hashable(self) -> None:
        runner = load_runner()
        hashes = runner.hash_sql_plan(ROOT, runner.PHASE_C_PLAN)
        self.assertEqual(set(runner.PHASE_C_PLAN), set(hashes))
        for relative, digest in hashes.items():
            expected = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(expected, digest, relative)


class PsqlCommandTests(unittest.TestCase):
    def test_psql_command_is_noninteractive_transactional_and_password_free(self) -> None:
        runner = load_runner()
        command = runner.build_psql_file_command(
            Path("/opt/postgres/bin/psql"),
            Path("/repo/sql/current.sql"),
            host="localhost",
            user="postgres",
            database="mimiciv31",
        )
        joined = " ".join(command)
        self.assertIn("-X", command)
        self.assertIn("-w", command)
        self.assertIn("ON_ERROR_STOP=1", command)
        self.assertIn("--single-transaction", command)
        self.assertNotIn("password", joined.lower())
        self.assertNotIn("PGPASSWORD", joined)

    def test_failure_stops_before_later_sql_and_records_actual_exit_code(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sql_dir = root / "sql"
            sql_dir.mkdir()
            for name in ("01.sql", "02_fail.sql", "03.sql"):
                (sql_dir / name).write_text("select 1;\n", encoding="utf-8")
            fake_psql = root / "fake_psql.py"
            fake_psql.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "target = pathlib.Path(sys.argv[sys.argv.index('-f') + 1]).name\n"
                "print(target)\n"
                "raise SystemExit(7 if 'fail' in target else 0)\n",
                encoding="utf-8",
            )
            fake_psql.chmod(0o700)
            run_dir = root / "run"
            record = runner.execute_sql_plan(
                project_root=root,
                psql=fake_psql,
                plan=["sql/01.sql", "sql/02_fail.sql", "sql/03.sql"],
                run_dir=run_dir,
                host="localhost",
                user="postgres",
                database="mimiciv31",
            )
        self.assertEqual("failed", record["status"])
        self.assertEqual(["passed", "failed", "not_run"], [s["status"] for s in record["steps"]])
        self.assertEqual(7, record["steps"][1]["exit_code"])

    def test_preflight_rejects_a_wrong_database_before_sql_execution(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            fake_psql = Path(tmp) / "fake_psql.py"
            fake_psql.write_text(
                "#!/usr/bin/env python3\n"
                "print('database\\twrong_database')\n"
                "print('server_version\\t12.18')\n"
                "print('transaction_read_only\\toff')\n"
                "print('database_create_privilege\\tt')\n"
                "print('relation:mimiciv_hosp.labevents\\tmimiciv_hosp.labevents')\n"
                "print('relation:mimiciv_hosp.d_labitems\\tmimiciv_hosp.d_labitems')\n"
                "print('relation:study_ahf_v3_2.model_090a_modeling_base_v33_v1\\tstudy_ahf_v3_2.model_090a_modeling_base_v33_v1')\n"
                "print('relation:study_ahf_v3_2.model_090b_compact_predictors_v33_v1\\tstudy_ahf_v3_2.model_090b_compact_predictors_v33_v1')\n",
                encoding="utf-8",
            )
            fake_psql.chmod(0o700)
            with self.assertRaisesRegex(RuntimeError, "wrong_database"):
                runner.preflight_database(
                    psql=fake_psql,
                    host="localhost",
                    user="postgres",
                    database="mimiciv31",
                )

    def test_preflight_records_database_version_and_required_relations(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            fake_psql = Path(tmp) / "fake_psql.py"
            fake_psql.write_text(
                "#!/usr/bin/env python3\n"
                "print('database\\tmimiciv31')\n"
                "print('server_version\\t12.18')\n"
                "print('transaction_read_only\\toff')\n"
                "print('database_create_privilege\\tt')\n"
                "print('relation:mimiciv_hosp.labevents\\tmimiciv_hosp.labevents')\n"
                "print('relation:mimiciv_hosp.d_labitems\\tmimiciv_hosp.d_labitems')\n"
                "print('relation:study_ahf_v3_2.model_090a_modeling_base_v33_v1\\tstudy_ahf_v3_2.model_090a_modeling_base_v33_v1')\n"
                "print('relation:study_ahf_v3_2.model_090b_compact_predictors_v33_v1\\tstudy_ahf_v3_2.model_090b_compact_predictors_v33_v1')\n",
                encoding="utf-8",
            )
            fake_psql.chmod(0o700)
            observed = runner.preflight_database(
                psql=fake_psql,
                host="localhost",
                user="postgres",
                database="mimiciv31",
            )
        self.assertEqual("mimiciv31", observed["database"])
        self.assertEqual("12.18", observed["server_version"])
        self.assertEqual("off", observed["transaction_read_only"])


class RunRecordTests(unittest.TestCase):
    def test_atomic_json_record_is_complete_and_has_no_secret_fields(self) -> None:
        runner = load_runner()
        payload = {
            "run_id": "synthetic",
            "status": "passed",
            "database": "mimiciv31",
            "steps": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run.json"
            runner.atomic_write_json(target, payload)
            self.assertEqual(payload, json.loads(target.read_text(encoding="utf-8")))
            self.assertFalse((target.parent / f".{target.name}.tmp").exists())
        serialized = json.dumps(payload).lower()
        for forbidden in ("password", "token", "secret"):
            self.assertNotIn(forbidden, serialized)

    def test_export_command_writes_only_registered_aggregate_tables(self) -> None:
        runner = load_runner()
        self.assertEqual(
            {
                "lab_contract_qc.csv": "study_ahf_v3_3.audit_116_lab_contract_phase_c_v1",
                "raw_vs_derived_qc.csv": "study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1",
            },
            runner.AGGREGATE_EXPORTS,
        )


class AuditSqlContractTests(unittest.TestCase):
    def test_116_is_a_fail_closed_contract_gate(self) -> None:
        sql = (
            ROOT / "sql_v3_3/audits/116_audit_raw_lab_contract_phase_c.sql"
        ).read_text(encoding="utf-8").lower()
        for required in (
            "audit_116_lab_contract_phase_c_v1",
            "eligible_wrong_fluid_n",
            "eligible_reversed_time_n",
            "eligible_missing_specimen_n",
            "eligible_duplicate_specimen_itemid_n",
            "eligible_non_inr_blank_unit_n",
            "contract_concept_n",
            "quarantine_item_n",
            "classified_row_balance_n",
            "raise exception",
        ):
            self.assertIn(required, sql)
        self.assertRegex(sql, r"contract_concept_n[\s\S]{0,500}\b14\b")
        self.assertRegex(sql, r"quarantine_item_n[\s\S]{0,500}\b8\b")

    def test_117_outputs_only_an_aggregate_schema(self) -> None:
        sql = (
            ROOT / "sql_v3_3/audits/117_audit_raw_vs_derived_phase_c.sql"
        ).read_text(encoding="utf-8").lower()
        for required in (
            "audit_117_raw_vs_derived_phase_c_v1",
            "model_090b_compact_predictors_v33_v1",
            "model_090b_compact_predictors_v34_v1",
            "availability_time",
            "late_result_events",
            "lactate",
            "creatinine",
            "bun",
            "mean_abs_diff",
        ):
            self.assertIn(required, sql)
        self.assertNotIn("m.r.", sql)
        self.assertNotIn("m.d.", sql)
        schema = re.search(
            r"create\s+table\s+study_ahf_v3_3\.audit_117_raw_vs_derived_phase_c_v1\s*\((.*?)\);",
            sql,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(schema)
        output_columns = schema.group(1)
        for patient_level_column in ("subject_id", "hadm_id", "stay_id", "labevent_id"):
            self.assertNotIn(patient_level_column, output_columns)

    def test_063a_namespaces_recomputed_fields_instead_of_shadowing_history(self) -> None:
        sql = (
            ROOT / "sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql"
        ).read_text(encoding="utf-8").lower()
        final_flags = re.search(
            r"final_flags\s+as\s*\((.*?)\n\s*from\s+base\s+b",
            sql,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(final_flags)
        projection = final_flags.group(1)
        for required_alias in (
            "pre12_lactate_contract_n",
            "pre12_lactate_contract_exact_n",
            "pre12_lactate_contract_max",
            "pre12_lactate_contract_min",
            "pre12_lactate_contract_last_time",
            "pre12_lactate_contract_last",
            "lactate_contract_ambiguous_episode_match_n",
            "lactate_contract_ambiguous_episode_match",
            "overlap_pre12_vaso_records_n",
            "overlap_post12_vaso_records_n",
            "overlap_post12_vaso_first_starttime",
        ):
            self.assertIn(required_alias, projection)
        self.assertIn("sum(lactate_contract_ambiguous_episode_match)", sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
