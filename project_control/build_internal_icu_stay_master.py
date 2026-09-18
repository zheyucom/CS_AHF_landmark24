#!/usr/bin/env python3
"""Build a reproducible, token-only ICU stay master from DHF_SRR exports.

The raw exports are left untouched.  This script joins the short ICU candidate
lists to the all-visit exports, parses only labelled ICU times from the ICU
document table, and writes a stay-level table plus a JSON QC summary.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "DHF_SRR"
OUT_ROOT = ROOT / "project_control" / "internal_validation" / "20260912"

CONFIG = {
    "女": {
        "candidate": DATA_ROOT / "DHF--女_病案首页20260911195949092" / "01_rdr_pat_visit.csv",
        "all_visits": DATA_ROOT / "DHF--女_就诊记录20260911201027004" / "01_rdr_pat_visit.csv",
        "docs": DATA_ROOT / "DHF--女_全部文书20260911195929593" / "02_rdr_medrecord_list.csv",
    },
    "男": {
        "candidate": DATA_ROOT / "DHF--男_病案首页20260911203904117" / "01_rdr_pat_visit.csv",
        "all_visits": DATA_ROOT / "DHF--男_就诊记录20260911204048370" / "01_rdr_pat_visit.csv",
        "docs": DATA_ROOT / "DHF--男_全部文书20260911203830551" / "02_rdr_medrecord_list.csv",
    },
}

TARGET_DOCS = {"入ICU记录", "出ICU记录", "ICU转病房记录"}
DATE_TOKEN = r"(?:19|20)\d{2}\s*(?:年|[-/.])\s*\d{1,2}\s*(?:月|[-/.])\s*\d{1,2}(?:\s*日|\s*号)?(?:\s+|T)\s*\d{1,2}:\d{2}(?::\d{2})?"
DATE_RE = re.compile(DATE_TOKEN)
IN_RE = re.compile(r"(?:入\s*ICU\s*时间|入ICU时间)\s*[:：]?\s*(%s)" % DATE_TOKEN)
OUT_RE = re.compile(r"(?:出\s*ICU\s*(?:日期|时间)|出ICU(?:日期|时间))\s*[:：]?\s*(%s)" % DATE_TOKEN)
TRANSFER_RE = re.compile(
    r"患者\s*于\s*(%s)\s*由[^。；\n]{0,180}?(?:ICU|重症|监护)[^。；\n]{0,180}?转入" % DATE_TOKEN
)
ICU_TERM_RE = re.compile(r"ICU|重症|监护|EICU|CCU", re.IGNORECASE)


def read_csv(path: Path):
    return path.open("r", encoding="utf-8-sig", newline="")


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    s = value.strip().replace("年", "-").replace("月", "-").replace("日", "")
    s = s.replace("号", "").replace("/", "-").replace(".", "-").replace("T", " ")
    s = re.sub(r"\s+", " ", s).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    ):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def fmt_dt(value: dt.datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def extract_date(regex: re.Pattern[str], text: str) -> dt.datetime | None:
    match = regex.search(text or "")
    return parse_dt(match.group(1)) if match else None


def norm_text(text: str) -> str:
    return re.sub(r"[\u3000\r\n\t]+", " ", text or "")


def age_from_dates(dob: str, anchor: dt.datetime | None) -> float | None:
    birth = parse_dt(dob)
    if not birth or not anchor:
        return None
    years = anchor.year - birth.year - ((anchor.month, anchor.day) < (birth.month, birth.day))
    return float(years)


def choose_visit_row(rows: list[dict[str, str]]) -> dict[str, str]:
    """Choose the most ICU-like duplicate row while retaining duplicate counts."""

    def score(row: dict[str, str]) -> tuple[int, int, int, int]:
        department = " ".join(
            row.get(k, "") for k in ("就诊科室名称", "入院科室", "病区名称", "出院科室")
        )
        return (
            int(bool(ICU_TERM_RE.search(department))) * 100,
            int(bool(row.get("病区名称"))) * 10,
            int(row.get("就诊类型") == "住院") * 5,
            int(bool(row.get("出院时间"))),
        )

    return max(rows, key=score)


def build_gender(gender: str, cfg: dict[str, Path]):
    candidates: dict[str, dict[str, str]] = {}
    candidate_counts: Counter[str] = Counter()
    candidate_rows = 0
    with read_csv(cfg["candidate"]) as handle:
        for row in csv.DictReader(handle):
            candidate_rows += 1
            visit = row.get("就诊号", "").strip()
            if not visit:
                continue
            # The short lists repeat the same visit in a few export rows.  Keep
            # the first identity row; the raw row count is reported separately.
            candidates.setdefault(visit, row)
            candidate_counts[visit] += 1

    full_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    with read_csv(cfg["all_visits"]) as handle:
        for row in csv.DictReader(handle):
            visit = row.get("就诊号", "").strip()
            if visit in candidates:
                full_rows[visit].append(row)

    docs: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "counts": Counter(),
            "missing_text": 0,
            "in_times": [],
            "out_times": [],
            "transfer_times": [],
            "created_times": [],
        }
    )
    doc_rows = 0
    with read_csv(cfg["docs"]) as handle:
        for row in csv.DictReader(handle):
            visit = row.get("就诊号", "").strip()
            name = row.get("文书名称", "").strip()
            if visit not in candidates or name not in TARGET_DOCS:
                continue
            doc_rows += 1
            item = docs[visit]
            counts: Counter = item["counts"]  # type: ignore[assignment]
            counts[name] += 1
            text = norm_text(row.get("文本病历", ""))
            if not text:
                item["missing_text"] = int(item["missing_text"]) + 1
            created = parse_dt(row.get("创建日期", ""))
            if created:
                item["created_times"].append(created)  # type: ignore[index]
            if name == "入ICU记录":
                value = extract_date(IN_RE, text)
                if value:
                    item["in_times"].append(value)  # type: ignore[index]
            elif name == "出ICU记录":
                value = extract_date(OUT_RE, text)
                if value:
                    item["out_times"].append(value)  # type: ignore[index]
            else:
                value = extract_date(TRANSFER_RE, text)
                if value:
                    item["transfer_times"].append(value)  # type: ignore[index]

    rows: list[dict[str, object]] = []
    for visit, identity in candidates.items():
        variants = full_rows.get(visit, [])
        chosen = choose_visit_row(variants) if variants else identity
        docs_item = docs.get(visit, {})
        in_times = sorted(docs_item.get("in_times", []))
        out_times = sorted(docs_item.get("out_times", []))
        transfer_times = sorted(docs_item.get("transfer_times", []))
        created_times = sorted(docs_item.get("created_times", []))
        structured_anchor = parse_dt(chosen.get("入区时间", ""))
        doc_t0 = in_times[0] if in_times else None
        t0 = doc_t0 or structured_anchor or parse_dt(chosen.get("就诊日期", ""))
        t0_source = (
            "icu_document_in_time"
            if doc_t0
            else "structured_in_area_proxy"
            if structured_anchor
            else "encounter_date_proxy"
            if t0
            else "missing"
        )
        age_structured = None
        try:
            age_structured = float(chosen.get("就诊年龄", ""))
        except (TypeError, ValueError):
            pass
        age_calculated = age_from_dates(chosen.get("出生年月", ""), t0)
        age = age_structured if age_structured is not None else age_calculated
        age_discrepant = bool(
            age_structured is not None
            and age_calculated is not None
            and abs(age_structured - age_calculated) > 1
        )
        department_text = " ".join(
            chosen.get(k, "") for k in ("就诊科室名称", "入院科室", "病区名称", "出院科室")
        )
        rows.append(
            {
                "patient_id": identity.get("患者ID", "").strip(),
                "sex": identity.get("性别", gender).strip() or gender,
                "date_of_birth": identity.get("出生年月", "").strip(),
                "visit_id": visit,
                "raw_candidate_row_count": candidate_counts.get(visit, 0),
                "full_visit_row_count": len(variants),
                "full_visit_duplicate_flag": int(len(variants) > 1),
                "chosen_row_icu_term_flag": int(bool(ICU_TERM_RE.search(department_text))),
                "encounter_date": chosen.get("就诊日期", ""),
                "structured_in_area_time": chosen.get("入区时间", ""),
                "structured_discharge_time": chosen.get("出院时间", ""),
                "department": chosen.get("就诊科室名称", ""),
                "admission_department": chosen.get("入院科室", ""),
                "ward": chosen.get("病区名称", ""),
                "discharge_department": chosen.get("出院科室", ""),
                "admission_route": chosen.get("入院方式", ""),
                "encounter_status": chosen.get("就诊状态", ""),
                "age_at_encounter": age if age is not None else "",
                "age_structured": age_structured if age_structured is not None else "",
                "age_calculated": age_calculated if age_calculated is not None else "",
                "age_discrepant_gt1y": int(age_discrepant),
                "adult_flag": int(age is not None and age >= 18),
                "icu_doc_count": sum(docs_item.get("counts", Counter()).values()),
                "icu_doc_in_count": docs_item.get("counts", Counter()).get("入ICU记录", 0),
                "icu_doc_out_count": docs_item.get("counts", Counter()).get("出ICU记录", 0),
                "icu_doc_transfer_count": docs_item.get("counts", Counter()).get("ICU转病房记录", 0),
                "icu_doc_missing_text_count": docs_item.get("missing_text", 0),
                "icu_doc_in_time_count": len(in_times),
                "icu_doc_out_time_count": len(out_times),
                "icu_doc_transfer_time_count": len(transfer_times),
                "icu_doc_created_time_count": len(created_times),
                "icu_in_time_first": fmt_dt(in_times[0] if in_times else None),
                "icu_in_time_last": fmt_dt(in_times[-1] if in_times else None),
                "icu_out_time_first": fmt_dt(out_times[0] if out_times else None),
                "icu_out_time_last": fmt_dt(out_times[-1] if out_times else None),
                "icu_transfer_time_first": fmt_dt(transfer_times[0] if transfer_times else None),
                "icu_transfer_time_last": fmt_dt(transfer_times[-1] if transfer_times else None),
                "doc_created_time_first": fmt_dt(created_times[0] if created_times else None),
                "doc_created_time_last": fmt_dt(created_times[-1] if created_times else None),
                "t0_candidate": fmt_dt(t0),
                "t0_candidate_source": t0_source,
                "time_qc_status": (
                    "document_in_and_out"
                    if in_times and out_times
                    else "document_in_only"
                    if in_times
                    else "document_out_only"
                    if out_times
                    else "structured_proxy_only"
                    if structured_anchor
                    else "missing"
                ),
            }
        )

    rows.sort(key=lambda row: (str(row["patient_id"]), str(row["t0_candidate"]), str(row["visit_id"])))
    by_patient: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_patient[str(row["patient_id"])].append(row)
    for patient_rows in by_patient.values():
        adult_rank = 0
        for rank, row in enumerate(patient_rows, start=1):
            row["patient_candidate_rank"] = rank
            if row["adult_flag"] == 1:
                adult_rank += 1
                row["index_adult_icu_flag"] = int(adult_rank == 1)
            else:
                row["index_adult_icu_flag"] = 0

    summary = {
        "gender": gender,
        "candidate_raw_rows": candidate_rows,
        "candidate_unique_visits": len(candidates),
        "candidate_unique_patients": len({r.get("患者ID", "") for r in candidates.values()}),
        "full_visit_missing_for_candidate": sum(1 for visit in candidates if not full_rows.get(visit)),
        "full_visit_duplicate_visits": sum(1 for values in full_rows.values() if len(values) > 1),
        "doc_target_rows": doc_rows,
        "doc_target_visits": len(docs),
        "doc_target_patients": len({candidates[v].get("患者ID", "") for v in docs}),
        "doc_counts": {
            name: sum(int(d.get("counts", Counter()).get(name, 0)) for d in docs.values())
            for name in sorted(TARGET_DOCS)
        },
        "doc_visits_with_missing_text": sum(1 for d in docs.values() if d.get("missing_text", 0)),
    }
    return rows, summary


def main() -> None:
    missing = [str(path) for cfg in CONFIG.values() for path in cfg.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Configured DHF_SRR export(s) not found:\n" + "\n".join(missing))
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, object]] = []
    gender_summaries = []
    for gender, cfg in CONFIG.items():
        rows, summary = build_gender(gender, cfg)
        all_rows.extend(rows)
        gender_summaries.append(summary)

    all_rows.sort(key=lambda row: (str(row["patient_id"]), str(row["t0_candidate"]), str(row["visit_id"])))
    fields = [
        "patient_id", "sex", "date_of_birth", "visit_id", "raw_candidate_row_count",
        "full_visit_row_count", "full_visit_duplicate_flag", "chosen_row_icu_term_flag",
        "encounter_date", "structured_in_area_time", "structured_discharge_time",
        "department", "admission_department", "ward", "discharge_department",
        "admission_route", "encounter_status", "age_at_encounter", "age_structured",
        "age_calculated", "age_discrepant_gt1y", "adult_flag", "icu_doc_count",
        "icu_doc_in_count", "icu_doc_out_count", "icu_doc_transfer_count",
        "icu_doc_missing_text_count", "icu_doc_in_time_count", "icu_doc_out_time_count",
        "icu_doc_transfer_time_count", "icu_doc_created_time_count", "icu_in_time_first",
        "icu_in_time_last", "icu_out_time_first", "icu_out_time_last",
        "icu_transfer_time_first", "icu_transfer_time_last", "doc_created_time_first",
        "doc_created_time_last", "t0_candidate", "t0_candidate_source", "time_qc_status",
        "patient_candidate_rank", "index_adult_icu_flag",
    ]
    master_path = OUT_ROOT / "icu_stay_master_20260912.csv"
    with master_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    patients = {str(row["patient_id"]) for row in all_rows}
    adult_rows = [row for row in all_rows if row["adult_flag"] == 1]
    adult_patients = {str(row["patient_id"]) for row in adult_rows}
    index_rows = [row for row in adult_rows if row["index_adult_icu_flag"] == 1]
    summary = {
        "generated_at": "2026-09-12",
        "source": "DHF_SRR",
        "source_contract": {
            "analysis_unit": "first adult eligible ICU candidate visit per patient",
            "link_key": "患者ID + 就诊号",
            "t0_priority": [
                "nursing explicit transfer-to-ICU event time (not present in current bedside export)",
                "labelled 入ICU记录 event time",
                "structured 入区时间 proxy",
                "就诊日期 proxy",
            ],
            "raw_data_modified": False,
        },
        "counts": {
            "raw_candidate_rows": sum(int(s["candidate_raw_rows"]) for s in gender_summaries),
            "unique_candidate_visits": len({str(row["visit_id"]) for row in all_rows}),
            "unique_candidate_patients": len(patients),
            "adult_candidate_visits": len(adult_rows),
            "adult_candidate_patients": len(adult_patients),
            "excluded_under18_visits": len(all_rows) - len(adult_rows),
            "excluded_under18_patients": len(patients) - len(adult_patients),
            "index_adult_icu_rows": len(index_rows),
            "duplicate_candidate_visit_rows": sum(int(row["full_visit_duplicate_flag"]) for row in all_rows),
        },
        "by_gender": gender_summaries,
        "age_distribution": dict(Counter(str(row["age_at_encounter"]) for row in all_rows if row["age_at_encounter"])),
        "adult_flag_distribution": dict(Counter(str(row["adult_flag"]) for row in all_rows)),
        "t0_source_distribution": dict(Counter(str(row["t0_candidate_source"]) for row in all_rows)),
        "time_qc_distribution": dict(Counter(str(row["time_qc_status"]) for row in all_rows)),
        "age_discrepant_rows_gt1y": sum(int(row["age_discrepant_gt1y"]) for row in all_rows),
        "missing_t0_rows": sum(1 for row in all_rows if not row["t0_candidate"]),
        "adult_index_by_gender": dict(Counter(str(row["sex"]) for row in index_rows)),
        "note": "Document-created timestamps are retained for audit only; they are not used as T0 when labelled ICU event times are absent.",
    }
    summary_path = OUT_ROOT / "icu_stay_master_qc_20260912.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"master": str(master_path), "summary": str(summary_path), **summary["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
