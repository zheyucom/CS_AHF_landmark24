#!/usr/bin/env python3
"""Read-only audit of BNP/NT-proBNP measurements for the 290-case review sample."""

from __future__ import annotations

import csv
import glob
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


SAMPLE = "project_control/runs/20260924_internal_stage1_g3_phenotype/clinical_review_sample_v1.csv"
OUTPUT_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")


def parse_number(value: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value or "")
    return float(match.group()) if match else None


def is_ntprobnp(name: str) -> bool:
    return bool(re.search(r"NT|氨基末端", name or "", re.I))


def is_np_name(name: str) -> bool:
    return bool(re.search(r"BNP|利钠|脑钠", name or "", re.I))


def is_strong_negative(name: str, value: float) -> bool:
    return value < (300.0 if is_ntprobnp(name) else 100.0)


def main() -> None:
    with open(SAMPLE, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    sample_by_visit = {row["visit_id"]: row for row in rows}
    observations: dict[str, list[tuple[str, str, str, str, str]]] = {
        visit_id: [] for visit_id in sample_by_visit
    }
    name_counts: Counter[str] = Counter()

    for path in glob.glob("DHF_SRR/*检验*/02_rdr_lab_test_data.csv"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
            for record in csv.DictReader(handle):
                visit_id = record.get("就诊号", "")
                if visit_id not in sample_by_visit:
                    continue
                name = record.get("检验指标", "")
                if not is_np_name(name):
                    continue
                name_counts[name] += 1
                observations[visit_id].append(
                    (
                        record.get("检验[报告]日期", ""),
                        name,
                        record.get("检验结果值", ""),
                        record.get("检验结果数值", ""),
                        record.get("异常标志", ""),
                    )
                )

    audit_rows: list[dict[str, str]] = []
    for visit_id, sample_row in sample_by_visit.items():
        t0 = datetime.fromisoformat(sample_row["t0_time"])
        in_window = []
        for date_text, name, display_value, numeric_value, abnormal_flag in observations[visit_id]:
            try:
                date_value = datetime.fromisoformat(date_text)
            except ValueError:
                continue
            if t0 - timedelta(hours=24) <= date_value < t0 + timedelta(hours=12):
                number = parse_number(numeric_value or display_value)
                in_window.append(
                    (date_value, name, display_value, number, abnormal_flag)
                )
        in_window.sort(key=lambda item: item[0])
        evaluable = [item for item in in_window if item[3] is not None]
        all_strong_negative = bool(evaluable) and all(
            is_strong_negative(item[1], item[3]) for item in evaluable
        )
        any_strong_negative = any(
            is_strong_negative(item[1], item[3]) for item in evaluable
        )
        audit_rows.append(
            {
                "visit_id": visit_id,
                "sample_stratum": sample_row["sample_stratum"],
                "algorithmic_label_v1": sample_row["algorithmic_label_v1"],
                "np_measured_t0m24_to_t12": "1" if evaluable else "0",
                "np_all_values_strong_negative": "1" if all_strong_negative else "0",
                "np_any_value_strong_negative": "1" if any_strong_negative else "0",
                "np_evidence": " || ".join(
                    f"{item[1]}={item[2]}@{item[0].isoformat(sep=' ')}"
                    for item in in_window
                ),
            }
        )

    output_path = OUTPUT_DIR / "clinical_review_290_np_window_audit_v1.csv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    summary_lines = ["NP_NAMES"]
    for name, count in name_counts.most_common():
        summary_lines.append(f"{count}\t{name}")
    summary_lines.append("COUNTS")
    for field in [
        "np_measured_t0m24_to_t12",
        "np_all_values_strong_negative",
        "np_any_value_strong_negative",
    ]:
        summary_lines.append(f"{field}\t{dict(Counter(row[field] for row in audit_rows))}")
    summary_lines.append("STRONG_NEGATIVE_CASES")
    for row in audit_rows:
        if row["np_all_values_strong_negative"] == "1":
            summary_lines.append(
                "\t".join(
                    [
                        row["visit_id"],
                        row["sample_stratum"],
                        row["algorithmic_label_v1"],
                        row["np_evidence"],
                    ]
                )
            )
    summary_path = OUTPUT_DIR / "clinical_review_290_np_window_audit_v1.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(output_path)
    print(summary_path)


if __name__ == "__main__":
    main()
