"""Aggregate audit for the internal DHF C-domain and BNP mapping gap.

This audit is deliberately outcome-blind. It does not change cohort labels,
phenotype thresholds, or model predictors. Only aggregate counts are written.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "project_control"
RUN_ID = "20260924_dhf_phenotype_portability_audit_v1"
OUT = CONTROL / "runs" / RUN_ID
LEDGER = (
    CONTROL
    / "runs"
    / "20260924_internal_stage1_g3_phenotype"
    / "dhf_abc_evidence_ledger_v1.csv"
)
TIMELINE = (
    CONTROL
    / "internal_validation"
    / "20260916_semantic_corrected"
    / "encounter_icu_time_audit.csv"
)
BNP_EVIDENCE = (
    CONTROL
    / "internal_validation"
    / "20260916_semantic_corrected"
    / "bnp_general_lab_evidence.csv"
)
TARGETED_LAB_FOLDERS = {
    "DHF--女_检验记录20260911201403540",
    "DHF--男_检验记录20260911204412869",
}
BNP_NAME = re.compile(r"BNP|脑钠|钠尿肽|利钠肽|N末端|N-末端", re.I)


def read_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def parse_time(value: str):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def flag(row, name):
    return row.get(name) == "1"


def c_key(row):
    return "".join(
        (
            "N" if flag(row, "c_ntprobnp_rule_in_flag") else "-",
            "E" if flag(row, "c_echo_abnormal_flag") else "-",
            "L" if flag(row, "c_iv_loop_order_proxy_flag") else "-",
        )
    )


def exact_number(value):
    value = (value or "").strip()
    if not re.fullmatch(r"[+]?(?:\d+(?:\.\d*)?|\.\d+)", value):
        return None
    return float(value)


def composition(rows):
    counts = Counter(c_key(row) for row in rows)
    n = len(rows)
    return {
        "n": n,
        "combinations": {
            key: {"n": counts[key], "percent": round(100 * counts[key] / n, 1) if n else 0}
            for key in sorted(counts)
        },
        "ntprobnp_rule_in": sum(flag(row, "c_ntprobnp_rule_in_flag") for row in rows),
        "ntprobnp_measured": sum(flag(row, "c_ntprobnp_pre12_measured_flag") for row in rows),
        "echo_abnormal": sum(flag(row, "c_echo_abnormal_flag") for row in rows),
        "echo_result_available": sum(flag(row, "c_echo_result_available_flag") for row in rows),
        "iv_loop_order_proxy": sum(flag(row, "c_iv_loop_order_proxy_flag") for row in rows),
    }


def main():
    ledger = list(read_rows(LEDGER))
    main_rows = [row for row in ledger if flag(row, "main_rule_supported_flag")]
    strict_rows = [row for row in ledger if flag(row, "strict_objective_rule_supported_flag")]
    ab_rows = [
        row
        for row in ledger
        if flag(row, "a_hf_anchor_flag") and flag(row, "b_decompensation_flag")
    ]
    main_t12_rows = [row for row in ledger if flag(row, "main_strict_t12_riskset_flag")]

    assert len(ledger) == 8385
    assert len(main_rows) == 773
    assert len(strict_rows) == 594
    assert len(ab_rows) == 1113
    assert len(main_t12_rows) == 558

    current_bnp_rows = list(read_rows(BNP_EVIDENCE))
    current_analytes = Counter(row.get("analyte", "") for row in current_bnp_rows)

    timeline = list(read_rows(TIMELINE))
    by_visit = {row["visit_id"]: parse_time(row.get("t0_time", "")) for row in timeline}
    by_patient = defaultdict(list)
    for row in timeline:
        by_patient[row["patient_id"]].append(
            (row["visit_id"], parse_time(row.get("t0_time", "")))
        )

    raw_targeted_analytes = Counter()
    exact_visit_windows = Counter()
    patient_link_windows = Counter()
    patient_link_episodes = defaultdict(set)
    brain_bnp_pre_t0_by_episode = {}

    for path in sorted((ROOT / "DHF_SRR").glob("*/02_rdr_lab_test_data.csv")):
        if path.parent.name not in TARGETED_LAB_FOLDERS:
            continue
        for row in read_rows(path):
            analyte = row.get("检验指标", "")
            if not BNP_NAME.search(analyte):
                continue
            raw_targeted_analytes[analyte] += 1
            report_time = parse_time(row.get("检验[报告]日期", ""))
            source_visit = row.get("就诊号", "")
            source_t0 = by_visit.get(source_visit)
            if report_time and source_t0:
                hours = (report_time - source_t0).total_seconds() / 3600
                window = "preT0_24h" if -24 <= hours < 0 else "preT12" if 0 <= hours < 12 else "other"
                exact_visit_windows[(analyte, window)] += 1

            if not report_time:
                continue
            for index_visit, index_t0 in by_patient.get(row.get("患者ID", ""), []):
                if not index_t0:
                    continue
                hours = (report_time - index_t0).total_seconds() / 3600
                if not -24 <= hours < 12:
                    continue
                if source_visit == index_visit:
                    link = "same_visit_preT0" if hours < 0 else "same_visit_preT12"
                elif hours < 0:
                    link = "cross_visit_preT0_candidate"
                else:
                    link = "cross_visit_postT0_excluded"
                patient_link_windows[(analyte, link)] += 1
                patient_link_episodes[(analyte, link)].add(index_visit)
                if analyte == "脑钠肽BNP" and link == "cross_visit_preT0_candidate":
                    brain_bnp_pre_t0_by_episode[index_visit] = exact_number(
                        row.get("检验结果值", "") or row.get("检验结果数值", "")
                    )

    ledger_by_visit = {row["visit_id"]: row for row in ledger}
    bnp_link_strata = Counter()
    ab_without_c_values = []
    for visit_id, value in brain_bnp_pre_t0_by_episode.items():
        row = ledger_by_visit[visit_id]
        if flag(row, "main_rule_supported_flag"):
            stratum = "current_main"
        elif flag(row, "a_hf_anchor_flag") and flag(row, "b_decompensation_flag"):
            stratum = "A_plus_B_without_C"
            if value is not None:
                ab_without_c_values.append(value)
        elif flag(row, "a_hf_anchor_flag"):
            stratum = "A_without_B"
        elif flag(row, "b_decompensation_flag"):
            stratum = "B_without_A"
        else:
            stratum = "neither_A_nor_B"
        bnp_link_strata[stratum] += 1

    result = {
        "run_id": RUN_ID,
        "governance": {
            "outcome_blind": True,
            "changes_cohort_labels": False,
            "changes_thresholds": False,
            "interpretation": "portability audit; not a phenotype refit or clinical gold standard",
        },
        "cohorts": {
            "candidate_frame": composition(ledger),
            "A_plus_B": composition(ab_rows),
            "main_A_plus_B_plus_C": composition(main_rows),
            "strict_objective": composition(strict_rows),
            "main_strict_T12": composition(main_t12_rows),
        },
        "current_quantitative_natriuretic_peptide_extract": {
            "rows": len(current_bnp_rows),
            "analytes": dict(sorted(current_analytes.items())),
            "finding": "the current numeric C-domain extract contains NT-proBNP only",
        },
        "targeted_longitudinal_lab_discovery": {
            "raw_analytes": dict(sorted(raw_targeted_analytes.items())),
            "exact_visit_windows": {
                "|".join(key): value for key, value in sorted(exact_visit_windows.items())
            },
            "patient_link_rows": {
                "|".join(key): value for key, value in sorted(patient_link_windows.items())
            },
            "patient_link_unique_index_episodes": {
                "|".join(key): len(value)
                for key, value in sorted(patient_link_episodes.items())
            },
            "brain_BNP_cross_visit_preT0_potential_membership_impact": {
                "linked_index_episodes": len(brain_bnp_pre_t0_by_episode),
                "current_phenotype_strata": dict(sorted(bnp_link_strata.items())),
                "A_plus_B_without_C_numeric_n": len(ab_without_c_values),
                "A_plus_B_without_C_ge_100_n_descriptive_only": sum(
                    value >= 100 for value in ab_without_c_values
                ),
                "A_plus_B_without_C_ge_400_n_descriptive_only": sum(
                    value >= 400 for value in ab_without_c_values
                ),
                "warning": (
                    "100 and 400 pg/mL are descriptive audit cut points only; "
                    "no BNP threshold is authorized until item identity and units are validated"
                ),
            },
            "interpretation": (
                "brain-natriuretic-peptide rows exist in the longitudinal export, but "
                "their item identity, units, and cross-visit linkage require validation "
                "before they can alter the phenotype"
            ),
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "DHF_PHENOTYPE_PORTABILITY_AUDIT_V1.json"
    with output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(output)


if __name__ == "__main__":
    main()
