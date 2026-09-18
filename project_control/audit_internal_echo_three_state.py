#!/usr/bin/env python3
"""Audit internal echo report availability without changing the raw exports.

The export contains reports from the selected ICU-visit universe.  This audit
keeps report availability, a strict bedside-echo candidate flag, and a
conservative text-based abnormal-support *draft* flag as separate states.
The last flag is not a clinical adjudication and must be reviewed before use.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "project_control/internal_validation/20260912/icu_stay_master_20260912.csv"
OUT = ROOT / "project_control/internal_validation/20260912"
EXAM_FILES = {
    "女": ROOT / "DHF_SRR/DHF--女_检查记录20260911202328833/02_rdr_exam_master_report.csv",
    "男": ROOT / "DHF_SRR/DHF--男_检查记录20260911203927514/02_rdr_exam_master_report.csv",
}

HEART_TYPE_RE = re.compile(r"心脏超声|心超")
HEART_NAME_RE = re.compile(r"超声心动图|心脏彩色多普勒|心超|TEE|心脏.*超声", re.I)
BEDSIDE_RE = re.compile(r"床旁|床边")
# Screening only: these terms indicate potentially abnormal structure/function,
# but negation and clinical relevance still require adjudication.
ABNORMAL_RE = re.compile(
    r"反流|狭窄|肺动脉高压|室壁运动.{0,6}(?:异常|减弱|欠协调)|"
    r"(?:左|右)房.{0,4}(?:增大|扩大)|(?:左|右)室.{0,4}(?:增大|扩大|肥厚)|"
    r"心室壁.{0,8}(?:增厚|肥厚|减弱|异常)|心包积液|心脏压塞|"
    r"舒张功能|充盈压|EF\s*[:：]?\s*(?:[0-4]?\d(?:\.\d+)?)\s*%|"
    r"射血分数\s*(?:降低|减低|下降)|占位|血栓|分流|返流"
    , re.I)


def read_csv(path: Path):
    return path.open("r", encoding="utf-8-sig", newline="")


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\u3000", " ")).strip()


def parse_dt(value: str | None) -> dt.datetime | None:
    value = clean(value)
    if not value:
        return None
    value = value.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def main() -> None:
    with MASTER.open("r", encoding="utf-8-sig", newline="") as handle:
        master = list(csv.DictReader(handle))
    index = {
        (row["sex"], row["visit_id"]): row
        for row in master
        if row["adult_flag"] == "1" and row["index_adult_icu_flag"] == "1"
    }
    all_candidate_visits = {(row["sex"], row["visit_id"]): row for row in master}

    stats = defaultdict(lambda: {
        "echo_report_count": 0,
        "bedside_echo_report_count": 0,
        "result_available_count": 0,
        "bedside_result_available_count": 0,
        "abnormal_support_draft_count": 0,
        "bedside_abnormal_support_draft_count": 0,
        "first_echo_report_time": "",
        "first_bedside_echo_time": "",
        "window_echo_report_count": 0,
        "window_bedside_echo_report_count": 0,
        "window_result_available_count": 0,
        "window_bedside_result_available_count": 0,
        "window_abnormal_support_draft_count": 0,
        "window_bedside_abnormal_support_draft_count": 0,
        "project_names": set(),
    })
    row_counts = Counter()
    report_rows = []
    for sex, path in EXAM_FILES.items():
        with read_csv(path) as handle:
            for row in csv.DictReader(handle):
                visit = clean(row.get("就诊号"))
                key = (sex, visit)
                if key not in all_candidate_visits:
                    continue
                check_type = clean(row.get("检查类型"))
                name = clean(row.get("项目名称"))
                if not HEART_TYPE_RE.search(check_type) or not HEART_NAME_RE.search(name):
                    continue
                finding = clean(row.get("检查所见"))
                conclusion = clean(row.get("检查结论"))
                result_available = bool(finding or conclusion)
                text = f"{conclusion} {finding}"
                abnormal_draft = bool(result_available and ABNORMAL_RE.search(text))
                bedside = bool(BEDSIDE_RE.search(name))
                report_time = clean(row.get("检查[报告]日期"))
                report_dt = parse_dt(report_time)
                t0 = parse_dt(all_candidate_visits[key].get("t0_candidate"))
                window_ok = bool(
                    t0 and report_dt and t0 - dt.timedelta(hours=24) <= report_dt < t0 + dt.timedelta(hours=12)
                )
                s = stats[key]
                s["echo_report_count"] += 1
                s["bedside_echo_report_count"] += int(bedside)
                s["result_available_count"] += int(result_available)
                s["bedside_result_available_count"] += int(bedside and result_available)
                s["abnormal_support_draft_count"] += int(abnormal_draft)
                s["bedside_abnormal_support_draft_count"] += int(bedside and abnormal_draft)
                s["window_echo_report_count"] += int(window_ok)
                s["window_bedside_echo_report_count"] += int(window_ok and bedside)
                s["window_result_available_count"] += int(window_ok and result_available)
                s["window_bedside_result_available_count"] += int(window_ok and bedside and result_available)
                s["window_abnormal_support_draft_count"] += int(window_ok and abnormal_draft)
                s["window_bedside_abnormal_support_draft_count"] += int(window_ok and bedside and abnormal_draft)
                s["project_names"].add(name)
                if report_time and (not s["first_echo_report_time"] or report_time < s["first_echo_report_time"]):
                    s["first_echo_report_time"] = report_time
                if bedside and report_time and (not s["first_bedside_echo_time"] or report_time < s["first_bedside_echo_time"]):
                    s["first_bedside_echo_time"] = report_time
                row_counts[(sex, "echo_report_rows")] += 1
                row_counts[(sex, "bedside_echo_rows")] += int(bedside)
                report_rows.append({
                    "sex": sex, "patient_id": row.get("患者ID", ""), "visit_id": visit,
                    "report_time": report_time, "project_name": name,
                    "result_available": int(result_available),
                    "abnormal_support_draft": int(abnormal_draft),
                    "database_abnormal_field": clean(row.get("是否异常")),
                })

    audit_rows = []
    for key, row in sorted(index.items(), key=lambda x: (x[0][0], x[0][1])):
        s = stats[key]
        audit_rows.append({
            "patient_id": row["patient_id"], "sex": row["sex"], "visit_id": row["visit_id"],
            "adult_index_flag": 1,
            "echo_report_count": s["echo_report_count"],
            "bedside_echo_report_count": s["bedside_echo_report_count"],
            "echo_performed_flag": int(s["echo_report_count"] > 0),
            "bedside_echo_performed_flag": int(s["bedside_echo_report_count"] > 0),
            "echo_result_available_flag": int(s["result_available_count"] > 0),
            "bedside_echo_result_available_flag": int(s["bedside_result_available_count"] > 0),
            "echo_abnormal_support_draft_flag": int(s["abnormal_support_draft_count"] > 0),
            "bedside_echo_abnormal_support_draft_flag": int(s["bedside_abnormal_support_draft_count"] > 0),
            "window_echo_report_count": s["window_echo_report_count"],
            "window_bedside_echo_report_count": s["window_bedside_echo_report_count"],
            "window_echo_result_available_flag": int(s["window_result_available_count"] > 0),
            "window_bedside_echo_result_available_flag": int(s["window_bedside_result_available_count"] > 0),
            "window_echo_abnormal_support_draft_flag": int(s["window_abnormal_support_draft_count"] > 0),
            "window_bedside_echo_abnormal_support_draft_flag": int(s["window_bedside_abnormal_support_draft_count"] > 0),
            "first_echo_report_time": s["first_echo_report_time"],
            "first_bedside_echo_time": s["first_bedside_echo_time"],
            "project_names": " | ".join(sorted(s["project_names"])),
        })
    audit_path = OUT / "internal_echo_three_state_audit_20260912.csv"
    fields = list(audit_rows[0]) if audit_rows else []
    with audit_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(audit_rows)

    def count(field: str, sex: str | None = None) -> int:
        return sum(int(r[field]) for r in audit_rows if sex is None or r["sex"] == sex)

    summary = {
        "generated_at": "2026-09-12",
        "source_files": {k: str(v) for k, v in EXAM_FILES.items()},
        "scope": "adult first eligible ICU candidate stay; candidate-specific exam exports",
        "raw_data_modified": False,
        "counts": {
            "adult_index_stays": len(audit_rows),
            "adult_index_patients": len({r["patient_id"] for r in audit_rows}),
            "echo_report_rows": len(report_rows),
            "echo_report_visits": sum(r["echo_performed_flag"] for r in audit_rows),
            "bedside_echo_report_rows": sum(1 for r in report_rows if any(x in r["project_name"] for x in ("床旁", "床边"))),
            "bedside_echo_visits": count("bedside_echo_performed_flag"),
            "bedside_echo_result_available_visits": count("bedside_echo_result_available_flag"),
            "bedside_echo_abnormal_support_draft_visits": count("bedside_echo_abnormal_support_draft_flag"),
            "window_echo_report_visits": sum(r["window_echo_report_count"] > 0 for r in audit_rows),
            "window_bedside_echo_report_visits": sum(r["window_bedside_echo_report_count"] > 0 for r in audit_rows),
            "window_bedside_echo_result_available_visits": count("window_bedside_echo_result_available_flag"),
            "window_bedside_echo_abnormal_support_draft_visits": count("window_bedside_echo_abnormal_support_draft_flag"),
        },
        "by_sex": {
            sex: {
                "adult_index_stays": sum(r["sex"] == sex for r in audit_rows),
                "echo_report_visits": count("echo_performed_flag", sex),
                "bedside_echo_visits": count("bedside_echo_performed_flag", sex),
                "bedside_echo_result_available_visits": count("bedside_echo_result_available_flag", sex),
                "bedside_echo_abnormal_support_draft_visits": count("bedside_echo_abnormal_support_draft_flag", sex),
                "window_bedside_echo_report_visits": sum(r["window_bedside_echo_report_count"] > 0 for r in audit_rows if r["sex"] == sex),
                "window_bedside_echo_result_available_visits": count("window_bedside_echo_result_available_flag", sex),
                "window_bedside_echo_abnormal_support_draft_visits": count("window_bedside_echo_abnormal_support_draft_flag", sex),
            }
            for sex in ("女", "男")
        },
        "definitions": {
            "echo_performed": "at least one report row with 检查类型 containing 心脏超声 and a heart-echo project name",
            "bedside_echo_performed": "above plus 项目名称 containing 床旁 or 床边",
            "result_available": "检查所见 or 检查结论 non-empty",
            "abnormal_support_draft": "result text contains a prespecified structural/function keyword; clinical adjudication required",
            "database_是否异常": "retained for row audit only; not used as abnormal-support truth",
        },
        "note": "This audit does not establish T0/T12 eligibility or DHF diagnosis; report and time semantics require manual field confirmation.",
    }
    summary_path = OUT / "internal_echo_three_state_audit_qc_20260912.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"audit": str(audit_path), "summary": str(summary_path), **summary["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
