#!/usr/bin/env python3
"""Inventory the local DHF_SRR export without emitting patient-level content."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "DHF_SRR"
OUT_JSON = ROOT / "project_control/internal_dhf_source_inventory_20260914.json"
OUT_MD = ROOT / "project_control/task_reports/TASK_REPORT_2026-09-14_INTERNAL_SOURCE_INVENTORY.md"

PATTERNS = {
    "icu_entry": re.compile(r"入\s*ICU|进入监护室|进入重症监护室|转入ICU|转入重症", re.I),
    "icu_exit": re.compile(r"出\s*ICU|转出ICU|转出重症|转入病房|转入专科", re.I),
    "hf_anchor": re.compile(r"急性心衰|心力衰竭|心功能不全|心源性休克|心肌病|严重瓣膜", re.I),
    "congestion": re.compile(r"肺水肿|肺充血|肺淤血|湿啰音|端坐呼吸|呼吸困难|水肿", re.I),
    "alternative": re.compile(r"肺炎|ARDS|误吸|脓毒症|感染|肺出血|创伤|术后|肾功能不全", re.I),
    "soap": re.compile(r"SOAP|查房|病程录|日常病程", re.I),
}


def iter_csvs():
    for path in sorted(DATA.glob("*/02_*.csv")):
        if path.is_file():
            yield path


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        yield from csv.DictReader(handle)


def category(path: Path) -> str:
    name = path.name
    if name == "02_rdr_medrecord_list.csv":
        return "documents"
    if name == "02_rdr_bedside.csv":
        return "bedside"
    if name == "02_rdr_orders.csv":
        return "orders"
    if name == "02_rdr_lab_test_data.csv":
        return "labs"
    if name == "02_rdr_exam_master_report.csv":
        return "exams"
    if name == "02_rdr_tube.csv":
        return "tubes"
    if name == "02_rdr_emr_inp_homepage.csv":
        return "homepage"
    if name == "02_rdr_diagnosis.csv":
        return "diagnosis"
    if name == "02_rdr_admit_info.csv":
        return "admission_history"
    if name == "02_rdr_nur_assessment.csv":
        return "nursing_assessment"
    return "other"


def main() -> None:
    files = []
    totals = Counter()
    sex_totals = Counter()
    doc_hits = Counter()
    doc_names = Counter()
    unique_visits = {c: set() for c in {category(p) for p in iter_csvs()}}
    field_sets = {}
    for path in iter_csvs():
        cat = category(path)
        count = 0
        nonempty_text = 0
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            field_sets[str(path.relative_to(ROOT))] = fields
            for row in reader:
                count += 1
                totals[cat] += 1
                sex = row.get("性别", "")
                if sex:
                    sex_totals[f"{cat}:{sex}"] += 1
                visit = row.get("就诊号", "")
                if visit:
                    unique_visits.setdefault(cat, set()).add(visit)
                if cat == "documents":
                    text = row.get("文本病历", "") or ""
                    if text.strip():
                        nonempty_text += 1
                    name = row.get("文书名称", "") or ""
                    if name:
                        doc_names[name] += 1
                    for key, pattern in PATTERNS.items():
                        if pattern.search(text):
                            doc_hits[key] += 1
        files.append({
            "path": str(path.relative_to(ROOT)),
            "category": cat,
            "rows": count,
            "size_bytes": path.stat().st_size,
            "nonempty_text_rows": nonempty_text if cat == "documents" else None,
            "fields": fields,
        })

    summary = {
        "generated_at": "2026-09-14",
        "scope": "local DHF_SRR source inventory; aggregate metadata only; no patient-level text emitted",
        "raw_data_modified": False,
        "file_count": len(files),
        "rows_by_category": dict(sorted(totals.items())),
        "unique_visit_count_by_category": {k: len(v) for k, v in sorted(unique_visits.items())},
        "sex_row_counts_by_category": dict(sorted(sex_totals.items())),
        "documents": {
            "nonempty_text_rows": sum(f["nonempty_text_rows"] or 0 for f in files if f["category"] == "documents"),
            "keyword_hit_row_counts": dict(sorted(doc_hits.items())),
            "document_name_counts_top30": doc_names.most_common(30),
        },
        "files": files,
        "field_sets": field_sets,
        "interpretation": [
            "文书关键词命中仅用于召回审计，不是 DHF 诊断或人工金标准。",
            "创建日期、报告日期和医嘱区间不能替代执行级治疗时间；最终结局仍需可追溯 ICU episode 与执行记录。",
            "男女文件在后续处理时按 patient_id/visit_id 合并，并排除已确认的未成年患者 9204020。",
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 任务报告：院内 DHF 原始源数据库存审计（2026-09-14）",
        "",
        "## 审计范围",
        "",
        "对 `DHF_SRR` 中所有 `02_*.csv` 做只读流式清点，仅输出文件/行数/就诊覆盖和聚合关键词计数，不输出患者 ID、文书正文或原始检验值。",
        "",
        "## 结果",
        "",
        f"- CSV 文件数：{len(files)}。",
        "- 各类别行数与就诊覆盖见 `project_control/internal_dhf_source_inventory_20260914.json`。",
        f"- 全部文书非空正文行：{summary['documents']['nonempty_text_rows']:,}。",
        "- 文书中的 ICU/HF/充血/替代诊断关键词仅作高召回候选，不能直接生成 DHF 纳入人数。",
        "",
        "## 对研究的影响",
        "",
        "院内原始导出已经具备用 NLP/规则进行全量 A+B+C 证据抽取的材料基础。下一步可在本地按 episode 和 T0/T12 时间门控生成候选证据表，再对抽样和边界病例人工裁决；但 ICU 出入 episode、实际给药/治疗升级和结局时间若缺失，仍不能计算最终 event/competing/censor。",
        "",
        "## 可复现命令",
        "",
        "`python3 project_control/audit_internal_dhf_source_inventory_v20260914.py`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "file_count": len(files),
        "rows_by_category": dict(sorted(totals.items())),
        "document_keyword_hit_row_counts": dict(sorted(doc_hits.items())),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
