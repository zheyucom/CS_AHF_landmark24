#!/usr/bin/env python3
"""Link the completed 300-report review to the verified landmark-12 export.

The 300-report package was sampled from the earlier pre-T0 export. This
script measures exact report-key overlap with the newer [T0-24 h, T12)
window; it does not reweight the old sample or claim landmark-window PPV.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


LINK_COLUMNS = [
    "annotation_id",
    "stay_id",
    "note_id",
    "original_screen_stratum",
    "congestion_label",
    "alternative_explanation_label",
    "report_available_pre_t0_label",
    "landmark12_charttime",
    "landmark12_storetime",
    "landmark12_report_available_by_t12_flag",
    "landmark12_report_modality",
    "landmark12_positive_congestion_evidence_flag",
    "landmark12_uncertainty_hit",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def source_stratum(row: dict[str, str]) -> str:
    if row.get("rule_positive_congestion") == "1":
        return "positive_rule_screen"
    if row.get("rule_uncertainty") == "1" or row.get("rule_negation") == "1":
        return "negated_or_uncertain_screen"
    return "no_hit_screen"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LINK_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation", type=Path, required=True)
    parser.add_argument("--landmark12", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()

    annotations = read_csv(args.annotation)
    landmark_rows = read_csv(args.landmark12)
    if len(annotations) != 300:
        raise SystemExit(f"Expected 300 completed annotations, got {len(annotations)}")
    if len(landmark_rows) != 7828:
        raise SystemExit(f"Expected 7,828 landmark reports, got {len(landmark_rows)}")

    landmark_by_key = {(row["stay_id"], row["note_id"]): row for row in landmark_rows}
    if len(landmark_by_key) != len(landmark_rows):
        raise SystemExit("Duplicate landmark (stay_id, note_id) keys")

    linked: list[dict[str, str]] = []
    for annotation in annotations:
        key = (annotation["stay_id"], annotation["note_id"])
        source = source_stratum(annotation)
        landmark = landmark_by_key.get(key)
        if landmark is None:
            continue
        linked.append({
            "annotation_id": annotation["annotation_id"],
            "stay_id": annotation["stay_id"],
            "note_id": annotation["note_id"],
            "original_screen_stratum": source,
            "congestion_label": annotation["congestion_label"],
            "alternative_explanation_label": annotation["alternative_explanation_label"],
            "report_available_pre_t0_label": annotation["report_available_pre_t0_label"],
            "landmark12_charttime": landmark["charttime"],
            "landmark12_storetime": landmark["storetime"],
            "landmark12_report_available_by_t12_flag": landmark["report_available_by_t12_flag"],
            "landmark12_report_modality": landmark.get("report_modality", ""),
            "landmark12_positive_congestion_evidence_flag": landmark["positive_congestion_evidence_flag"],
            "landmark12_uncertainty_hit": landmark["uncertainty_hit"],
        })

    write_csv(args.output_csv, linked)
    linked_labels = Counter(row["congestion_label"] for row in linked)
    linked_strata = Counter(row["original_screen_stratum"] for row in linked)
    missing = [
        row for row in annotations
        if (row["stay_id"], row["note_id"]) not in landmark_by_key
    ]
    missing_strata = Counter(source_stratum(row) for row in missing)

    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    with args.output_report.open("w", encoding="utf-8") as handle:
        handle.write("# 300条人工标注与 landmark-12 完整报告库链接审计\n\n")
        handle.write("日期：2026-09-04\n\n")
        handle.write("## 目的与边界\n\n")
        handle.write(
            "300条人工标注来自较早的 pre-T0 影像抽样框。本审计仅按 `(stay_id, note_id)` "
            "与已验证完整的 `[T0-24 h,T12)` 报告导出进行精确链接，不对旧抽样重新加权，"
            "也不把链接子集的标签比例写成 landmark-12 窗口的 PPV、敏感度或特异度。\n\n"
        )
        handle.write("## 完整性与重合\n\n")
        handle.write("| 项目 | 数量 |\n|---|---:|\n")
        handle.write(f"| 已完成人工标注 | {len(annotations)} |\n")
        handle.write(f"| landmark-12 完整报告 | {len(landmark_rows)} |\n")
        handle.write(f"| 精确链接成功 | {len(linked)} |\n")
        handle.write(f"| 未在 landmark-12 窗口出现 | {len(missing)} |\n")
        handle.write(f"| 链接率 | {len(linked) / len(annotations):.1%} |\n\n")
        handle.write("## 链接子集描述（不是主窗口性能估计）\n\n")
        handle.write("人工标签：" + ", ".join(f"{key}={value}" for key, value in sorted(linked_labels.items())) + "。\n\n")
        handle.write("原始筛查层：" + ", ".join(f"{key}={value}" for key, value in sorted(linked_strata.items())) + "。\n\n")
        handle.write("未链接记录按原始筛查层：" + ", ".join(f"{key}={value}" for key, value in sorted(missing_strata.items())) + "。\n\n")
        handle.write("## 解释\n\n")
        handle.write(
            "这145条记录可用于检查旧规则与主窗口字段是否能稳定对接，并可作为报告级语义示例；"
            "但155条记录不在新窗口，说明 pre-T0 证据窗与 `[T0-24 h,T12)` 证据窗不是同一抽样总体。"
            "因此，最终主窗口影像规则验证需要从7,828条完整报告中按主窗口规则分层重新抽样，"
            "并由临床人员进行盲法标注。现有300条标注保留为历史规则验证和可迁移性审计。\n\n"
        )
        handle.write("## 产物\n\n")
        handle.write(f"- 链接明细：`{args.output_csv}`\n")
        handle.write("- 主窗口完整文本来源：GCS 导出的 Parquet，经本地行数、键唯一性和 stay-level 对账验证。\n")

    print(f"linked={len(linked)} missing={len(missing)} output={args.output_csv}")


if __name__ == "__main__":
    main()
