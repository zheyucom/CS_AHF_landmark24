#!/usr/bin/env python3
"""Create a deterministic 50-stay bedside-echo semantic/time QC sample."""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
MASTER = BASE / "icu_stay_master_20260912.csv"
AUDIT = BASE / "internal_echo_three_state_audit_20260912.csv"
OUT = BASE / "internal_echo_sample_qc_20260912.csv"
SUMMARY = BASE / "internal_echo_sample_qc_20260912.json"
EXAM_FILES = {
    "女": ROOT / "DHF_SRR/DHF--女_检查记录20260911202328833/02_rdr_exam_master_report.csv",
    "男": ROOT / "DHF_SRR/DHF--男_检查记录20260911203927514/02_rdr_exam_master_report.csv",
}

HEART_TYPE_RE = re.compile(r"心脏超声|心超")
HEART_NAME_RE = re.compile(r"超声心动图|心脏彩色多普勒|心超|TEE|心脏.*超声", re.I)
BEDSIDE_RE = re.compile(r"床旁|床边")


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\u3000", " ")).strip()


def parse_dt(value: str | None) -> dt.datetime | None:
    value = clean(value).replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def systematic(rows: list[dict], n: int) -> list[dict]:
    if len(rows) <= n:
        return rows
    # Deterministic spread across the sorted cohort, avoiding a date or ID-only sample.
    positions = [round(i * (len(rows) - 1) / (n - 1)) for i in range(n)]
    return [rows[p] for p in positions]


def main() -> None:
    with MASTER.open(encoding="utf-8-sig", newline="") as handle:
        master = {
            (r["sex"], r["visit_id"]): r
            for r in csv.DictReader(handle)
            if r["adult_flag"] == "1" and r["index_adult_icu_flag"] == "1"
        }
    with AUDIT.open(encoding="utf-8-sig", newline="") as handle:
        audit = {(r["sex"], r["visit_id"]): r for r in csv.DictReader(handle)}

    candidates = {
        sex: sorted(
            [r for key, r in audit.items() if r["sex"] == sex and int(r["window_bedside_echo_report_count"]) > 0],
            key=lambda r: (r["visit_id"], r["patient_id"]),
        )
        for sex in ("女", "男")
    }
    selected = {(r["sex"], r["visit_id"]): r for sex in candidates for r in systematic(candidates[sex], 25)}

    reports: dict[tuple[str, str], list[dict]] = {}
    for sex, path in EXAM_FILES.items():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (sex, clean(row.get("就诊号")))
                if key not in selected:
                    continue
                if not HEART_TYPE_RE.search(clean(row.get("检查类型"))) or not HEART_NAME_RE.search(clean(row.get("项目名称"))):
                    continue
                if not BEDSIDE_RE.search(clean(row.get("项目名称"))):
                    continue
                reports.setdefault(key, []).append(row)

    output = []
    for key, a in sorted(selected.items(), key=lambda x: (x[0][0], x[0][1])):
        m = master[key]
        t0 = parse_dt(m["t0_candidate"])
        t12 = t0 + dt.timedelta(hours=12) if t0 else None
        rows = reports.get(key, [])
        ranked = sorted(rows, key=lambda r: parse_dt(r.get("检查[报告]日期")) or dt.datetime.max)
        # Prefer the earliest report inside the prespecified window; retain a fallback
        # only if the audit/sample unexpectedly contains no such row.
        in_window = [
            r for r in ranked
            if t0 and (rd := parse_dt(r.get("检查[报告]日期"))) and t0 - dt.timedelta(hours=24) <= rd < t12
        ]
        chosen = (in_window or ranked)[0]
        report_dt = parse_dt(chosen.get("检查[报告]日期"))
        output.append({
            "patient_id": m["patient_id"],
            "sex": key[0],
            "visit_id": key[1],
            "t0_candidate": m["t0_candidate"],
            "t0_source": m["t0_candidate_source"],
            "t12_candidate": t12.strftime("%Y-%m-%d %H:%M:%S") if t12 else "",
            "report_time": clean(chosen.get("检查[报告]日期")),
            "audit_time": clean(chosen.get("审核日期")),
            "report_in_window": int(bool(t0 and report_dt and t0 - dt.timedelta(hours=24) <= report_dt < t12)),
            "project_name": clean(chosen.get("项目名称")),
            "check_type": clean(chosen.get("检查类型")),
            "finding": clean(chosen.get("检查所见")),
            "conclusion": clean(chosen.get("检查结论")),
            "database_abnormal_field": clean(chosen.get("是否异常")),
            "result_available": int(bool(clean(chosen.get("检查所见")) or clean(chosen.get("检查结论")))),
            "audit_bedside_report_count": a["window_bedside_echo_report_count"],
            "audit_window_result_available_flag": a["window_bedside_echo_result_available_flag"],
            "audit_window_abnormal_support_draft_flag": a["window_bedside_echo_abnormal_support_draft_flag"],
        })

    fields = list(output[0]) if output else []
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    summary = {
        "generated_at": "2026-09-12",
        "sample_size": len(output),
        "by_sex": {sex: sum(r["sex"] == sex for r in output) for sex in ("女", "男")},
        "selection": "systematic 25 per sex from adult index stays with at least one bedside echo report in [T0-24h,T12)",
        "report_rows_per_selected_stay": {"min": min(map(lambda k: len(reports.get(k, [])), selected)), "max": max(map(lambda k: len(reports.get(k, [])), selected))},
        "report_in_window": sum(r["report_in_window"] for r in output),
        "result_available": sum(r["result_available"] for r in output),
        "source_audit": str(AUDIT),
        "raw_data_modified": False,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"csv": str(OUT), "summary": str(SUMMARY), **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
