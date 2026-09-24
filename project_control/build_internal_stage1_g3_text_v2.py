#!/usr/bin/env python3
"""Build a non-outcome-driven V2 text/diagnosis recall layer for internal DHF.

V1 is immutable. This script adds a narrow semantic bridge for notes that link a
current or tentative HF judgment to HF-directed treatment. It also audits
time-valid structured HF diagnoses. It never uses outcomes, model fit, or
clinical adjudication to alter the rule.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_RUN = ROOT / "project_control/runs/20260924_internal_stage1_g3_phenotype"
V1_LEDGER = V1_RUN / "dhf_abc_evidence_ledger_v1.csv"
T0_EVIDENCE = ROOT / "project_control/internal_validation/20260916_semantic_corrected/time_gated_evidence.csv"
QUARANTINE = ROOT / "project_control/internal_validation/20260916_semantic_corrected/document_quarantine.csv"
RAW = ROOT / "DHF_SRR"
RUN_ID = "20260924_internal_stage1_g3_text_v2"
DEFAULT_OUT = ROOT / "project_control/runs" / RUN_ID
HOUR = timedelta(hours=1)

HF_TERM = re.compile(
    r"急性心力衰竭|急性心衰|心力衰竭|心衰|心功能不全|心源性休克",
    re.I,
)
HF_TREATMENT = re.compile(
    r"呋塞米|速尿|托拉塞米|布美他尼|依他尼酸|利尿(?:治疗|处理)?|"
    r"硝酸甘油|硝普钠|扩血管|强心|多巴胺|多巴酚丁胺|米力农|左西孟旦|"
    r"无创通气|BiPAP|CPAP|抗心衰",
    re.I,
)
TREATMENT_DIRECTIVE = re.compile(
    r"予|给予|加用|使用|应用|调整|加强|静推|静滴|泵入|改用|继续",
    re.I,
)
TENTATIVE = re.compile(r"考虑|可能|疑似|待排|不能排除|不除外")
HYPOTHETICAL = re.compile(r"警惕|风险|预防|必要时|如出现|可能发生|避免|伴或不伴")
LOW_PROBABILITY = re.compile(r"可能性(?:小|低)|可能不大|不太可能|可能性不高")
QUESTION_MARK = re.compile(r"[?？]")
HISTORY = re.compile(r"既往|既往史|曾有|多年病史|基础慢性")
NEGATION = re.compile(r"否认|无|未见|未闻及|未发现|不支持|排除")
CURRENT = re.compile(r"目前|当前|本次|此次|现|入院后|转入后|合并")
EXCLUDED_DIAGNOSIS = re.compile(r"鉴别诊断|鉴别考虑|排除诊断")
RETRO_DOC = re.compile(r"出ICU|转病房|转出记录|死亡|出院|谈话|告知|同意|须知|评分|评估表|知情|病危|病重|作废|麻醉前访视")
DIAGNOSIS_EXCLUDED = re.compile(r"待查|鉴别诊断|鉴别考虑|排除诊断")
DIAGNOSIS_ALLOWED = re.compile(r"初步诊断|明确诊断|修正诊断|补充诊断|主诊断")
HF_DIAGNOSIS = re.compile(r"急性心力衰竭|急性心衰|心力衰竭|心衰|心功能不全|心源性休克", re.I)


def parse_time(value: str | None) -> datetime | None:
    s = str(value or "").strip()
    if not s or not re.search(r"\d:\d{2}", s):
        return None
    s = s.replace("年", "-").replace("月", "-").replace("日", " ")
    s = s.replace("号", " ").replace("：", ":").replace("/", "-").replace(".", "-")
    s = re.sub(r"\s+", " ", s.replace("T", " ")).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def compact(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _segments(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？!?；;\n])", str(text or "")) if part.strip()]


def _local_status(segment: str, start: int, end: int) -> str:
    prefix = segment[max(0, start - 40):start]
    local = segment[max(0, start - 50):min(len(segment), end + 45)]
    if EXCLUDED_DIAGNOSIS.search(segment):
        return "excluded_differential"
    if LOW_PROBABILITY.search(local):
        return "low_probability"
    if QUESTION_MARK.search(local):
        return "uncertain_question"
    if HYPOTHETICAL.search(local):
        return "hypothetical"
    if HISTORY.search(prefix) and not CURRENT.search(prefix):
        return "historical"
    if NEGATION.search(prefix) and not TENTATIVE.search(prefix):
        return "negated"
    if TENTATIVE.search(prefix + segment[end:min(len(segment), end + 12)]):
        return "uncertain"
    return "affirmed"


def analyze_hf_text(text: str) -> list[dict[str, str]]:
    """Return auditable HF mentions and their nearest treatment relationship.

    affirmed_with_treatment_support is deliberately narrower than a generic
    HF mention: treatment must be a named HF-directed treatment, and the
    judgment must not be historical, hypothetical, negated, or differential.
    Same/adjacent sentence is automatic; a farther same-paragraph link is
    review-only (probable_current_hf).
    """
    segments = _segments(text)
    events: list[dict[str, str]] = []
    for i, segment in enumerate(segments):
        treatments = list(HF_TREATMENT.finditer(segment))
        for match in HF_TERM.finditer(segment):
            status = _local_status(segment, match.start(), match.end())
            event = {
                "status": status,
                "hf_term": match.group(),
                "treatment_term": "",
                "relation": "none",
                "reason": "text_mention_only",
                "excerpt": compact(segment),
            }
            if status in {"excluded_differential", "hypothetical", "low_probability", "uncertain_question", "historical", "negated"}:
                events.append(event)
                continue
            candidates: list[tuple[int, int, re.Match[str], str]] = []
            for j in range(max(0, i - 4), min(len(segments), i + 5)):
                for treatment in HF_TREATMENT.finditer(segments[j]):
                    if LOW_PROBABILITY.search(segment) or HYPOTHETICAL.search(segments[j]):
                        continue
                    if j == i and not TREATMENT_DIRECTIVE.search(segment[max(0, match.start() - 30):treatment.end() + 15]):
                        continue
                    distance = abs(j - i)
                    candidates.append((distance, j, treatment, segments[j]))
            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]))
                distance, j, treatment, treatment_segment = candidates[0]
                if distance == 0:
                    event.update(
                        status="affirmed_with_treatment_support",
                        treatment_term=treatment.group(),
                        relation="same_sentence",
                        reason="current_or_tentative_hf_judgment_linked_to_named_hf_treatment",
                        excerpt=compact(segment),
                    )
                elif distance == 1:
                    event.update(
                        status="affirmed_with_treatment_support",
                        treatment_term=treatment.group(),
                        relation="adjacent_sentence",
                        reason="current_or_tentative_hf_judgment_linked_to_named_hf_treatment",
                        excerpt=compact(segment + " " + treatment_segment),
                    )
                elif "\n" not in segment and "\n" not in treatment_segment:
                    event.update(
                        status="probable_current_hf",
                        treatment_term=treatment.group(),
                        relation="same_paragraph_far_sentence",
                        reason="treatment_link_requires_review_due_to_sentence_distance",
                        excerpt=compact(segment + " " + treatment_segment),
                    )
            events.append(event)
    return events


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fields:
        fields = ["status"]
    elif fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool1(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def in_time_window(t0: datetime | None, event: datetime | None) -> bool:
    return bool(t0 and event and t0 - 24 * HOUR <= event < t0 + 12 * HOUR)


def source_key(source_file: str, source_row: str) -> tuple[str, str]:
    return str(source_file), str(source_row)


def main(out: Path = DEFAULT_OUT) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    v1_rows = read_csv(V1_LEDGER)
    v1 = {row["visit_id"]: row for row in v1_rows}
    evidence_rows = read_csv(T0_EVIDENCE)
    quarantine = {
        source_key(row.get("source_file", ""), row.get("source_row", ""))
        for row in read_csv(QUARANTINE)
    } if QUARANTINE.exists() else set()

    raw_rows: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(RAW.glob("*/02_rdr_medrecord_list.csv")):
        rel = str(path.relative_to(ROOT))
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            for row_no, row in enumerate(csv.DictReader(handle), 2):
                visit_id = row.get("就诊号", "")
                if visit_id not in v1:
                    continue
                raw_rows[(rel, str(row_no))] = row

    text_evidence: list[dict[str, object]] = []
    text_by_visit: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    visited_sources = {
        source_key(r.get("source_file", ""), r.get("source_row", ""))
        for r in evidence_rows
        if r.get("domain") in {"hf", "management"} and r.get("source_file", "").endswith("02_rdr_medrecord_list.csv")
    }
    for (rel, row_no), row in raw_rows.items():
        visit_id = row.get("就诊号", "")
        if source_key(rel, row_no) in quarantine:
            continue
        name = row.get("文书名称", "")
        if RETRO_DOC.search(name):
            continue
        t0 = parse_time(v1[visit_id].get("t0_time"))
        created = parse_time(row.get("创建日期"))
        if not in_time_window(t0, created):
            continue
        if visited_sources and source_key(rel, row_no) not in visited_sources:
            continue
        text = row.get("文本病历", "")
        for result in analyze_hf_text(text):
            if result["status"] not in {
                "affirmed_with_treatment_support",
                "probable_current_hf",
                "uncertain",
                "affirmed",
            }:
                continue
            record = {
                "visit_id": visit_id,
                "patient_id": row.get("患者ID", ""),
                "available_time_proxy": row.get("创建日期", ""),
                "source_file": rel,
                "source_row": row_no,
                "document_name": name,
                **result,
            }
            text_evidence.append(record)
            text_by_visit[visit_id].append(record)

    diagnosis_evidence: list[dict[str, object]] = []
    dx_by_visit: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for path in sorted(RAW.glob("*/02_rdr_diagnosis.csv")):
        rel = str(path.relative_to(ROOT))
        with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            for row_no, row in enumerate(csv.DictReader(handle), 2):
                visit_id = row.get("就诊号", "")
                if visit_id not in v1 or not HF_DIAGNOSIS.search(row.get("诊断名称", "")):
                    continue
                dtype = row.get("诊断类型", "")
                dx_time = parse_time(row.get("诊断时间"))
                t0 = parse_time(v1[visit_id].get("t0_time"))
                if DIAGNOSIS_EXCLUDED.search(dtype):
                    status = "excluded_differential_or_pending"
                elif not dx_time:
                    status = "unknown_time"
                elif not in_time_window(t0, dx_time):
                    status = "outside_t12_identifiable_window"
                elif not DIAGNOSIS_ALLOWED.search(dtype):
                    status = "unclassified_diagnosis_type"
                else:
                    status = "affirmed_current_structured_diagnosis"
                record = {
                    "visit_id": visit_id,
                    "patient_id": row.get("患者ID", ""),
                    "diagnosis_type": dtype,
                    "diagnosis_time": row.get("诊断时间", ""),
                    "diagnosis_name": row.get("诊断名称", ""),
                    "status": status,
                    "source_file": rel,
                    "source_row": row_no,
                }
                diagnosis_evidence.append(record)
                if status == "affirmed_current_structured_diagnosis":
                    dx_by_visit[visit_id].append(record)

    ledger: list[dict[str, object]] = []
    for old in v1_rows:
        visit_id = old["visit_id"]
        text_rows = text_by_visit.get(visit_id, [])
        dx_rows = dx_by_visit.get(visit_id, [])
        text_support = any(r["status"] == "affirmed_with_treatment_support" for r in text_rows)
        text_review = any(r["status"] == "probable_current_hf" for r in text_rows)
        dx_support = bool(dx_rows)
        old_a = bool1(old.get("a_hf_anchor_flag"))
        a_v2 = old_a or text_support or dx_support
        b = bool1(old.get("b_decompensation_flag"))
        objective_c = bool1(old.get("c_ntprobnp_rule_in_flag")) or bool1(old.get("c_echo_abnormal_flag"))
        any_c = objective_c or bool1(old.get("c_iv_loop_order_proxy_flag"))
        main_v2 = a_v2 and b and any_c
        strict_v2 = a_v2 and b and objective_c
        if main_v2:
            label_v2 = "algorithmic_rule_supported"
        elif old.get("old_pre_review_label") == "unknown":
            label_v2 = "algorithmic_unknown"
        else:
            label_v2 = "algorithmic_rule_not_supported"
        reasons = []
        if old.get("alternative_mentioned_flag") in {"1", "True", "true"}:
            reasons.append("alternative_explanation_present")
        if bool1(old.get("c_iv_loop_order_proxy_flag")) and not objective_c:
            reasons.append("treatment_proxy_only_C")
        if label_v2 == "algorithmic_unknown":
            reasons.append("uncertain_or_missing_anchor")
        if text_review:
            reasons.append("probable_text_link_requires_review")
        row = dict(old)
        row.update({
            "algorithmic_label_v2": label_v2,
            "main_rule_supported_flag_v2": int(main_v2),
            "strict_objective_rule_supported_flag_v2": int(strict_v2),
            "a_hf_anchor_flag_v2": int(a_v2),
            "a_hf_text_treatment_support_v2_flag": int(text_support),
            "a_hf_text_treatment_support_v2_refs": " || ".join(
                f"{r['source_file']}#row={r['source_row']}" for r in text_rows if r["status"] == "affirmed_with_treatment_support"
            ),
            "a_hf_text_treatment_support_v2_excerpts": " || ".join(
                compact(str(r["excerpt"]), 180) for r in text_rows if r["status"] == "affirmed_with_treatment_support"
            )[:600],
            "a_hf_structured_diagnosis_v2_flag": int(dx_support),
            "a_hf_structured_diagnosis_v2_refs": " || ".join(
                f"{r['source_file']}#row={r['source_row']}" for r in dx_rows
            ),
            "a_hf_structured_diagnosis_v2_excerpts": " || ".join(
                f"{r['diagnosis_type']}:{r['diagnosis_name']}" for r in dx_rows
            )[:600],
            "probable_text_review_v2_flag": int(text_review),
            "probable_text_review_v2_refs": " || ".join(
                f"{r['source_file']}#row={r['source_row']}" for r in text_rows if r["status"] == "probable_current_hf"
            ),
            "new_main_supported_v2_flag": int(main_v2 and not bool1(old.get("main_rule_supported_flag"))),
            "new_strict_objective_supported_v2_flag": int(strict_v2 and not bool1(old.get("strict_objective_rule_supported_flag"))),
            "main_strict_t12_riskset_flag_v2": int(main_v2 and bool1(old.get("strict_t12_time_eligible_flag"))),
            "main_broad_t12_riskset_flag_v2": int(main_v2 and bool1(old.get("broad_t12_time_eligible_flag"))),
            "strict_objective_t12_riskset_flag_v2": int(strict_v2 and bool1(old.get("strict_t12_time_eligible_flag"))),
            "clinical_review_priority_reason_v2": "|".join(reasons) if reasons else "routine_sampling",
        })
        ledger.append(row)

    flow_names = [
        ("source_echo_assessed_adult_icu_candidates", len(ledger)),
        ("A_hf_anchor_supported_v1", sum(bool1(r.get("a_hf_anchor_flag")) for r in ledger)),
        ("A_hf_text_treatment_support_v2", sum(bool1(r.get("a_hf_text_treatment_support_v2_flag")) for r in ledger)),
        ("A_hf_structured_diagnosis_v2", sum(bool1(r.get("a_hf_structured_diagnosis_v2_flag")) for r in ledger)),
        ("A_hf_anchor_supported_v2", sum(bool1(r.get("a_hf_anchor_flag_v2")) for r in ledger)),
        ("B_decompensation_supported", sum(bool1(r.get("b_decompensation_flag")) for r in ledger)),
        ("C_supported_any", sum(bool1(r.get("c_ntprobnp_rule_in_flag")) or bool1(r.get("c_echo_abnormal_flag")) or bool1(r.get("c_iv_loop_order_proxy_flag")) for r in ledger)),
        ("main_algorithmic_rule_supported_v1", sum(bool1(r.get("main_rule_supported_flag")) for r in ledger)),
        ("main_algorithmic_rule_supported_v2", sum(bool1(r.get("main_rule_supported_flag_v2")) for r in ledger)),
        ("strict_objective_rule_supported_v1", sum(bool1(r.get("strict_objective_rule_supported_flag")) for r in ledger)),
        ("strict_objective_rule_supported_v2", sum(bool1(r.get("strict_objective_rule_supported_flag_v2")) for r in ledger)),
        ("main_strict_T12_riskset_v2", sum(bool1(r.get("main_strict_t12_riskset_flag_v2")) for r in ledger)),
        ("main_broad_T12_sensitivity_riskset_v2", sum(bool1(r.get("main_broad_t12_riskset_flag_v2")) for r in ledger)),
        ("strict_objective_T12_riskset_v2", sum(bool1(r.get("strict_objective_t12_riskset_flag_v2")) for r in ledger)),
    ]
    flow = [{"stage": name, "n": count, "status": "algorithmic_not_clinical_gold_standard"} for name, count in flow_names]
    transitions = Counter((r.get("algorithmic_label_v1", ""), r.get("algorithmic_label_v2", "")) for r in ledger)
    transition_rows = [{"algorithmic_label_v1": old, "algorithmic_label_v2": new, "n": count} for (old, new), count in sorted(transitions.items())]
    new_cases = [r for r in ledger if bool1(r.get("new_main_supported_v2_flag"))]
    review_queue = [r for r in ledger if bool1(r.get("probable_text_review_v2_flag"))]

    write_csv(out / "dhf_abc_evidence_ledger_v2.csv", ledger)
    write_csv(out / "text_semantic_evidence_v2.csv", text_evidence)
    write_csv(out / "structured_diagnosis_evidence_v2.csv", diagnosis_evidence)
    write_csv(out / "phenotype_flow_counts_v2.csv", flow, ["stage", "n", "status"])
    write_csv(out / "phenotype_label_change_matrix_v2.csv", transition_rows)
    write_csv(out / "newly_supported_cases_v2.csv", new_cases)
    write_csv(out / "probable_text_review_queue_v2.csv", review_queue)

    inputs = [V1_LEDGER, T0_EVIDENCE]
    if QUARANTINE.exists():
        inputs.append(QUARANTINE)
    qc = {
        "run_id": RUN_ID,
        "status": "PASS_V2_TEXT_AND_STRUCTURED_DIAGNOSIS_RECALL_LAYER_CLINICAL_CALIBRATION_PENDING",
        "source_rows": len(ledger),
        "text_evidence_rows": len(text_evidence),
        "text_supported_visit_n": sum(bool1(r.get("a_hf_text_treatment_support_v2_flag")) for r in ledger),
        "probable_text_review_visit_n": len(review_queue),
        "structured_diagnosis_rows": len(diagnosis_evidence),
        "structured_current_diagnosis_visit_n": sum(bool1(r.get("a_hf_structured_diagnosis_v2_flag")) for r in ledger),
        "v1_main_supported_n": sum(bool1(r.get("main_rule_supported_flag")) for r in ledger),
        "v2_main_supported_n": sum(bool1(r.get("main_rule_supported_flag_v2")) for r in ledger),
        "v1_strict_objective_supported_n": sum(bool1(r.get("strict_objective_rule_supported_flag")) for r in ledger),
        "v2_strict_objective_supported_n": sum(bool1(r.get("strict_objective_rule_supported_flag_v2")) for r in ledger),
        "new_main_supported_n": len(new_cases),
        "new_strict_objective_supported_n": sum(bool1(r.get("new_strict_objective_supported_v2_flag")) for r in ledger),
        "v2_main_strict_t12_riskset_n": sum(bool1(r.get("main_strict_t12_riskset_flag_v2")) for r in ledger),
        "v2_main_broad_t12_riskset_n": sum(bool1(r.get("main_broad_t12_riskset_flag_v2")) for r in ledger),
        "v2_strict_objective_t12_riskset_n": sum(bool1(r.get("strict_objective_t12_riskset_flag_v2")) for r in ledger),
        "selection_uses_outcomes": False,
        "clinical_gold_standard": False,
        "v1_overwritten": False,
        "limitations": [
            "V2 uses the same time-gated clinical source universe as V1; it is not a complete note universe.",
            "Named treatment is an order/document proxy; it is not eMAR execution.",
            "Same-sentence or adjacent-sentence promotion is an algorithmic rule, not clinical adjudication.",
            "Far-sentence links are review-only and do not enter the V2 A anchor.",
            "Structured diagnoses outside the T12-identifiable window are retained as audit rows but do not support V2 early eligibility.",
        ],
    }
    snapshot = {
        "run_id": RUN_ID,
        "inputs": [{"path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size} for p in inputs],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rule_version": "text_current_treatment_link_v2",
    }
    (out / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "input_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**qc, "out": str(out)}, ensure_ascii=False, indent=2))
    return qc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    main(args.out.resolve())
