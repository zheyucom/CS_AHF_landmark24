#!/usr/bin/env python3
"""Build a deterministic case-level audit of vasoactive order proxies against notes."""

from __future__ import annotations

import csv
import json
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "internal_validation" / "20260916_semantic_corrected"
CACHE = ROOT / "internal_validation" / "20260916_case_review"
OUT = CACHE / "order_proxy_text_validation_50.csv"
QC = CACHE / "order_proxy_text_validation_50_qc.json"

DRUG_RE = re.compile(
    r"去甲肾上腺素|肾上腺素|多巴胺|多巴酚丁胺|米力农|去氧肾上腺素|"
    r"垂体后叶素|血管加压素|左西孟旦|异丙肾上腺素|升压药|血管活性药"
)
CURRENT_RE = re.compile(r"予|使用|应用|泵入|泵注|维持|上调|下调|加用|停用|撤除|减量|增量|续用|改为")
PLANNED_RE = re.compile(r"建议|计划|拟|必要时|备用|可予|考虑使用|如.*则")
NEGATED_RE = re.compile(r"未予|不予|无需|暂不|未使用|未应用|无血管活性药")
TEMPLATE_RE = re.compile(r"3233-101102|MAP\s*[≥<>]|mmHgMAP|SOFA|GCS评分|评分标准|药物知情同意书")


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_time(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def evidence_fragments(text: str):
    clean = re.sub(r"\s+", " ", text)
    out = []
    for match in DRUG_RE.finditer(clean):
        start = max(0, match.start() - 55)
        end = min(len(clean), match.end() + 85)
        fragment = clean[start:end]
        if TEMPLATE_RE.search(fragment):
            status = "template_or_score"
        elif NEGATED_RE.search(fragment):
            status = "explicit_no_current_use"
        elif PLANNED_RE.search(fragment):
            status = "planned_or_recommended"
        elif CURRENT_RE.search(fragment):
            status = "current_or_adjusted"
        else:
            status = "mention_without_action"
        out.append((status, fragment))
    return out


def main():
    times = {row["visit_id"]: row for row in read_csv(RUN / "encounter_icu_time_audit.csv")}
    orders = read_csv(RUN / "pre12_vaso_order_evidence.csv")
    orders_by_visit = defaultdict(list)
    for row in orders:
        orders_by_visit[row["visit_id"]].append(row)

    documents = defaultdict(list)
    for filename, source_type in [("source_notes.jsonl", "note"), ("nursing_remarks.jsonl", "nursing")]:
        with (CACHE / filename).open() as handle:
            for line in handle:
                row = json.loads(line)
                row["source_type"] = source_type
                documents[row["visit_id"]].append(row)

    case_rows = []
    for visit_id, docs in documents.items():
        time_row = times.get(visit_id, {})
        t0 = parse_time(time_row.get("t0_time", ""))
        t12 = t0 + timedelta(hours=12) if t0 else None
        relevant_docs = []
        fragments = []
        for doc in docs:
            created = parse_time(doc.get("created", ""))
            in_window = bool(t0 and created and t0 <= created < t12)
            if doc["source_type"] == "note":
                in_window = bool(doc.get("in_phenotype_window")) and bool(
                    t0 and created and created < t12
                )
            if not in_window:
                continue
            relevant_docs.append(doc)
            for status, fragment in evidence_fragments(doc.get("text", "")):
                fragments.append(
                    {
                        "status": status,
                        "fragment": fragment,
                        "source_file": doc.get("source_file", ""),
                        "source_row": doc.get("source_row", ""),
                        "created": doc.get("created", ""),
                    }
                )

        visit_orders = orders_by_visit.get(visit_id, [])
        classes = {row["pre12_order_class"] for row in visit_orders}
        if "preT0_order_continuation_uncertain" in classes:
            stratum = "continuation_uncertain"
        elif "IV_infusion_interval_overlaps_pre12" in classes:
            stratum = "infusion_overlap"
        elif "IV_infusion_started_pre12" in classes:
            stratum = "infusion_started"
        elif "IV_point_order_pre12" in classes:
            stratum = "point_only"
        elif fragments:
            stratum = "no_order_text_mention"
        else:
            stratum = "no_order_no_text_mention"

        current = [x for x in fragments if x["status"] == "current_or_adjusted"]
        planned = [x for x in fragments if x["status"] == "planned_or_recommended"]
        negative = [x for x in fragments if x["status"] == "explicit_no_current_use"]
        if visit_orders and current:
            pre_review = "text_corroborated_lower_bound"
        elif visit_orders and planned and not current:
            pre_review = "planned_only_possible_proxy_mismatch"
        elif visit_orders and negative and not current:
            pre_review = "text_negative_possible_timing_mismatch"
        elif visit_orders:
            pre_review = "order_only_not_disproven"
        elif current:
            pre_review = "text_current_without_pre12_order"
        elif planned:
            pre_review = "planned_only_without_order"
        else:
            pre_review = "negative_control_no_signal"

        order_summary = "; ".join(
            sorted(
                {
                    f"{x['medication']}|{x['route']}|{x['pre12_order_class']}|{x['start_time']}--{x['stop_time']}"
                    for x in visit_orders
                }
            )
        )
        top_fragments = current[:3] + negative[:2] + planned[:2] + [
            x for x in fragments if x["status"] == "mention_without_action"
        ][:1]
        text_summary = " || ".join(
            f"{x['status']}:{x['created']}:{x['source_file']}#row={x['source_row']}:{x['fragment']}"
            for x in top_fragments
        )
        case_rows.append(
            {
                "visit_id": visit_id,
                "t0_time": time_row.get("t0_time", ""),
                "sample_stratum": stratum,
                "order_count": len(visit_orders),
                "order_classes": ";".join(sorted(classes)),
                "order_summary": order_summary,
                "in_window_document_count": len(relevant_docs),
                "current_text_fragment_count": len(current),
                "planned_text_fragment_count": len(planned),
                "text_evidence": text_summary,
                "AI_pre_review": pre_review,
                "final_audit_status": "not_independent_clinical_gold_standard",
                "review_note": "Text absence does not prove non-execution; point orders cannot establish sustained infusion.",
            }
        )

    by_stratum = defaultdict(list)
    for row in case_rows:
        by_stratum[row["sample_stratum"]].append(row)
    rng = random.Random(20260916)
    targets = {
        "infusion_started": 12,
        "infusion_overlap": 10,
        "point_only": 10,
        "continuation_uncertain": 7,
        "no_order_text_mention": 6,
        "no_order_no_text_mention": 5,
    }
    selected = []
    for stratum, target in targets.items():
        rows = sorted(by_stratum[stratum], key=lambda x: x["visit_id"])
        selected.extend(rng.sample(rows, min(target, len(rows))))
    if len(selected) < 50:
        chosen = {row["visit_id"] for row in selected}
        remaining = sorted(
            [row for row in case_rows if row["visit_id"] not in chosen],
            key=lambda x: (x["sample_stratum"], x["visit_id"]),
        )
        selected.extend(rng.sample(remaining, min(50 - len(selected), len(remaining))))
    selected = sorted(selected[:50], key=lambda x: (x["sample_stratum"], x["visit_id"]))

    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)

    qc = {
        "audit_version": "order_proxy_text_validation_v1",
        "sample_seed": 20260916,
        "eligible_cached_visits": len(case_rows),
        "sampled_visits": len(selected),
        "sample_strata": dict(sorted((k, sum(r["sample_stratum"] == k for r in selected)) for k in targets)),
        "pre_review_counts": dict(
            sorted(
                (k, sum(r["AI_pre_review"] == k for r in selected))
                for k in {r["AI_pre_review"] for r in selected}
            )
        ),
        "interpretation": "Text corroboration is a lower bound. This audit cannot estimate true administration sensitivity or specificity without eMAR.",
        "independent_clinical_gold_standard": False,
    }
    QC.write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
