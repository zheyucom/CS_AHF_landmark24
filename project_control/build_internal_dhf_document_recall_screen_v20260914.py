#!/usr/bin/env python3
"""Build a visit-level document recall screen from local DHF_SRR exports.

This is a high-recall triage artifact. It intentionally does not assign DHF
labels, infer T0 from document creation time, or use post-T0 evidence as a
clinical gold standard.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "DHF_SRR"
OUT = ROOT / "project_control/internal_dhf_document_recall_screen_20260914.csv"
REPORT = ROOT / "project_control/task_reports/TASK_REPORT_2026-09-14_DOCUMENT_RECALL_SCREEN.md"
EXCLUDED_PATIENTS = {"9204020"}  # user-confirmed under-18 patient

PATTERNS = {
    "hf_anchor_hit_count": re.compile(r"急性心衰|急性心力衰竭|心力衰竭|心功能不全|心源性休克|心肌病|严重瓣膜", re.I),
    "congestion_hit_count": re.compile(r"肺水肿|肺充血|肺淤血|湿啰音|端坐呼吸|呼吸困难|颈静脉怒张|外周水肿|低氧恶化", re.I),
    "alternative_hit_count": re.compile(r"肺炎|ARDS|误吸|脓毒症|感染|肺出血|创伤|术后|肾功能不全", re.I),
}
DOC_NAMES = {
    "icu_entry_note_count": {"入ICU记录", "入住重症监护室（ICU）谈话记录"},
    "icu_exit_note_count": {"出ICU记录", "ICU转病房记录"},
    "soap_note_count": {"查房记录(SOAP)", "查房记录(简单)", "普通病程录", "首次病程录（新版）"},
}


def as_age(value: str) -> float | None:
    try:
        x = float(str(value).strip())
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    ages: dict[tuple[str, str], float] = {}
    homepage_files = sorted(DATA.glob("*/02_rdr_emr_inp_homepage.csv"))
    for path in homepage_files:
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            for row in csv.DictReader(handle):
                key = (row.get("患者ID", ""), row.get("就诊号", ""))
                if key[0] in EXCLUDED_PATIENTS:
                    continue
                age = as_age(row.get("年龄", ""))
                if key[0] and key[1] and age is not None:
                    ages[key] = age

    # Values are aggregate counts only; no text is retained.
    agg: dict[tuple[str, str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    doc_path = next(iter(sorted(DATA.glob("*/02_rdr_medrecord_list.csv"))), None)
    doc_paths = sorted(DATA.glob("*/02_rdr_medrecord_list.csv"))
    if not doc_paths:
        raise SystemExit("No document exports found")
    for path in doc_paths:
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            for row in csv.DictReader(handle):
                key = (row.get("患者ID", ""), row.get("性别", ""), row.get("就诊号", ""))
                if not all(key) or key[0] in EXCLUDED_PATIENTS:
                    continue
                item = agg[key]
                item["document_count"] += 1
                text = row.get("文本病历", "") or ""
                if text.strip():
                    item["nonempty_document_count"] += 1
                name = (row.get("文书名称", "") or "").strip()
                if name in DOC_NAMES["icu_entry_note_count"]:
                    item["icu_entry_note_count"] += 1
                if name in DOC_NAMES["icu_exit_note_count"]:
                    item["icu_exit_note_count"] += 1
                if name in DOC_NAMES["soap_note_count"]:
                    item["soap_note_count"] += 1
                for field, pattern in PATTERNS.items():
                    if pattern.search(text):
                        item[field] += 1

    rows = []
    for (patient_id, sex, visit_id), item in sorted(agg.items(), key=lambda x: (x[0][1], x[0][2])):
        age = ages.get((patient_id, visit_id))
        hf = item["hf_anchor_hit_count"] > 0
        cong = item["congestion_hit_count"] > 0
        alt = item["alternative_hit_count"] > 0
        rows.append({
            "patient_id": patient_id,
            "sex": sex,
            "visit_id": visit_id,
            "age_from_homepage": "" if age is None else age,
            "adult_flag_from_homepage": "" if age is None else int(age >= 18),
            **{k: item[k] for k in ["document_count", "nonempty_document_count", "icu_entry_note_count", "icu_exit_note_count", "soap_note_count", *PATTERNS]},
            "high_recall_hf_and_congestion_document_screen": int(hf and cong),
            "high_recall_hf_congestion_with_alternative_document_screen": int(hf and cong and alt),
            "screen_status": "recall_screen_only",
        })

    fields = list(rows[0]) if rows else []
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    adult = [r for r in rows if r["adult_flag_from_homepage"] == 1]
    summary = {
        "document_visit_rows": len(rows),
        "adult_rows_with_homepage_age": len(adult),
        "adult_hf_anchor_document_screen": sum(r["hf_anchor_hit_count"] > 0 for r in adult),
        "adult_congestion_document_screen": sum(r["congestion_hit_count"] > 0 for r in adult),
        "adult_hf_and_congestion_document_screen": sum(r["high_recall_hf_and_congestion_document_screen"] == 1 for r in adult),
        "adult_hf_congestion_with_alternative_document_screen": sum(r["high_recall_hf_congestion_with_alternative_document_screen"] == 1 for r in adult),
        "rows_without_homepage_age": sum(r["adult_flag_from_homepage"] == "" for r in rows),
    }
    REPORT.write_text(
        "# 任务报告：院内 DHF 文书高召回筛查层（2026-09-14）\n\n"
        "## 本次完成\n\n"
        f"- 从男女两组全部文书导出流式生成 {len(rows):,} 个就诊号级聚合行；已按用户确认排除未成年患者 9204020；未保留原文正文。\n"
        f"- 可连接病案首页年龄的成人行：{len(adult):,}；年龄缺失行：{summary['rows_without_homepage_age']:,}。\n"
        f"- 成人行中文书同时出现 HF 锚点和充血/失代偿关键词：{summary['adult_hf_and_congestion_document_screen']:,}；同时出现替代诊断关键词：{summary['adult_hf_congestion_with_alternative_document_screen']:,}。\n\n"
        "## 解释边界\n\n"
        "这是 NLP/规则的高召回排序层，不是 DHF 纳入人数。关键词可能来自否定、模板、鉴别诊断或 T12 后记录；文书创建日期不被当作 T0。病案首页年龄与用户已确认的 9204020 未成年状态存在冲突，后续以人工排除名单和实际出生/就诊核对为准。下一步需按已锁定的 ICU episode 和 T0/T12 时间门控，从原文证据片段中抽取 A（HF anchor）、B（失代偿/充血）、C（支持域）并进行人工校准。\n\n"
        "## 可复现命令\n\n"
        "`python3 project_control/build_internal_dhf_document_recall_screen_v20260914.py`\n",
        encoding="utf-8",
    )
    print(summary | {"output": str(OUT), "report": str(REPORT)})


if __name__ == "__main__":
    main()
