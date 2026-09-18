#!/usr/bin/env python3
"""Build the versioned internal DHF three-tier audit for 2026-09-14.

This table is an auditable phenotype bridge, not a clinical gold standard.
It keeps the full adult ICU denominator, report-time echo gating, text-based
abnormal-support weak labels, the completed 45-case semantic audit, and the
current outcome-data availability state in separate fields.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
MASTER = BASE / "icu_stay_master_20260912.csv"
ECHO = BASE / "internal_echo_three_state_audit_20260912.csv"
SEMANTIC = BASE / "internal_gate3_semantic_evidence_20260914_adjudicated.csv"
OUT = BASE / "internal_dhf_three_tier_audit_20260914.csv"
SUMMARY = BASE / "internal_dhf_three_tier_audit_qc_20260914.json"
REPORT = ROOT / "project_control/task_reports/TASK_REPORT_2026-09-14_INTERNAL_THREE_TIER_AUDIT.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def yes(row: dict[str, str], key: str) -> int:
    return int(row.get(key, "") in {"1", "1.0", "True", "true"})


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    master = {
        (r["sex"], r["visit_id"]): r
        for r in read_csv(MASTER)
        if yes(r, "adult_flag") and yes(r, "index_adult_icu_flag")
    }
    echo = {(r["sex"], r["visit_id"]): r for r in read_csv(ECHO)}
    semantic = {(r["sex"], r["visit_id"]): r for r in read_csv(SEMANTIC)}

    rows: list[dict[str, object]] = []
    for key, m in sorted(master.items(), key=lambda item: (item[0][0], item[0][1])):
        e = echo.get(key, {})
        s = semantic.get(key, {})
        window_performed = int(float(e.get("window_bedside_echo_report_count", "0") or 0) > 0)
        window_result = yes(e, "window_bedside_echo_result_available_flag")
        window_abnormal = yes(e, "window_bedside_echo_abnormal_support_draft_flag")
        semantic_status = s.get("codex_adjudication_status", "not_reviewed")
        semantic_tier = s.get("dhf_tier_adjudicated", "not_reviewed")
        # A semantic retain/exclude label is only available for the sampled
        # 45 cases. It must never be propagated to the unreviewed denominator.
        if semantic_status == "retain_candidate":
            dhf_evidence = "semantic_retain_candidate_draft"
        elif semantic_status == "exclude_draft":
            dhf_evidence = "semantic_not_supported_draft"
        else:
            dhf_evidence = "not_reviewed"
        rows.append({
            "patient_id": m["patient_id"],
            "sex": m["sex"],
            "visit_id": m["visit_id"],
            "adult_index_flag": 1,
            "t0_candidate": m["t0_candidate"],
            "t0_source_candidate": m["t0_candidate_source"],
            "t12_candidate": f"{m['t0_candidate']}+12h" if m["t0_candidate"] else "",
            "window_definition": "report_time_proxy_[T0-24h,T12)",
            "window_bedside_echo_performed_flag": window_performed,
            "window_bedside_echo_result_available_flag": window_result,
            "window_bedside_echo_abnormal_support_draft_flag": window_abnormal,
            "echo_supported_dhf_draft_flag": int(window_performed and window_result and window_abnormal),
            "semantic_review_status": semantic_status,
            "semantic_dhf_tier_adjudicated": semantic_tier,
            "dhf_composite_evidence_status": dhf_evidence,
            "hf_anchor_support_final": s.get("hf_anchor_support_final", "not_reviewed"),
            "decompensation_domain_final": s.get("decompensation_domain_final", "not_reviewed"),
            "management_evidence_final": s.get("management_evidence_final", "not_reviewed"),
            "alternative_explanation_evidence": s.get("alternative_explanation_evidence", "not_reviewed"),
            "event_flag": "not_yet_reconstructed_from_existing_sources",
            "competing_alive_icu_discharge_flag": "not_yet_reconstructed_from_existing_sources",
            "administrative_censor_flag": "not_yet_reconstructed_from_existing_sources",
            "outcome_data_status": "pending_existing_source_reconstruction",
        })

    if len(rows) != 8385:
        raise SystemExit(f"Expected 8,385 adult index stays, got {len(rows)}")

    write_csv(OUT, rows)

    def count(field: str, value: object = 1) -> int:
        return sum(r[field] == value for r in rows)

    summary = {
        "generated_at": "2026-09-14",
        "scope": "merged female/male adult first index ICU stay; under-18 patient 9204020 excluded",
        "raw_data_modified": False,
        "counts": {
            "adult_index_icu_denominator": len(rows),
            "female": sum(r["sex"] == "女" for r in rows),
            "male": sum(r["sex"] == "男" for r in rows),
            "window_bedside_echo_performed": count("window_bedside_echo_performed_flag"),
            "window_bedside_echo_result_available": count("window_bedside_echo_result_available_flag"),
            "window_bedside_echo_abnormal_support_draft": count("window_bedside_echo_abnormal_support_draft_flag"),
            "echo_supported_dhf_draft": count("echo_supported_dhf_draft_flag"),
            "semantic_retain_candidate_draft": count("semantic_review_status", "retain_candidate"),
            "semantic_not_supported_draft": count("semantic_review_status", "exclude_draft"),
            "semantic_unreviewed_full_cohort": count("semantic_review_status", "not_reviewed"),
            "event": None,
            "competing_alive_icu_discharge": None,
            "administrative_censor": None,
            "outcome_unreconstructed_rows": count("outcome_data_status", "pending_existing_source_reconstruction"),
        },
        "definitions": {
            "echo_window": "bedside echo report-time proxy in [T0-24 h,T0+12 h); execution time is not available",
            "result_available": "检查所见 or 检查结论 is non-empty",
            "abnormal_support_draft": "prespecified text keyword screen; requires clinical adjudication",
            "echo_supported_dhf_draft": "three echo states only; not a DHF diagnosis",
            "semantic_audit": "45 sampled cases only; retain/exclude labels are weak-label audit records and are not propagated to the other 8,340 stays",
            "outcomes": "not yet reconstructed; existing notes, nursing and orders are authorized sources; orders remain execution proxies, not measured infusion rates",
        },
        "literature_basis": [
            "Bozkurt et al. Universal Definition of HF, Eur J Heart Fail 2021",
            "McDonagh et al. ESC HF guideline, Eur Heart J 2021",
            "Chapman et al. NegEx, J Biomed Inform 2001",
            "Irvin et al. CheXpert, AAAI 2019, doi:10.1609/aaai.v33i01.3301590",
            "Collins et al. TRIPOD+AI, BMJ 2024",
            "Wolff et al. PROBAST, Ann Intern Med 2019",
            "Fine & Gray competing-risk model, JASA 1999",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    REPORT.write_text(
        "# 任务报告：院内 DHF 三级表型审计（2026-09-14）\n\n"
        "## 本次完成\n\n"
        f"- 男女数据合并后的成人 index ICU 分母：{len(rows):,}（女 {summary['counts']['female']:,}，男 {summary['counts']['male']:,}）；17 岁患者 9204020 已排除。\n"
        f"- 报告时间窗口 `[T0-24 h,T12)` 内床旁心超：完成 {summary['counts']['window_bedside_echo_performed']:,}，结果可用 {summary['counts']['window_bedside_echo_result_available']:,}，关键词异常支持 draft {summary['counts']['window_bedside_echo_abnormal_support_draft']:,}。\n"
        f"- 三个心超状态同时满足的 `echo_supported_dhf_draft`：{summary['counts']['echo_supported_dhf_draft']:,}；这不是 DHF 确诊人数。\n"
        f"- 45 例语义优先抽样：retain candidate {summary['counts']['semantic_retain_candidate_draft']}、not supported {summary['counts']['semantic_not_supported_draft']}、未抽审 {summary['counts']['semantic_unreviewed_full_cohort']}。\n"
        "- 事件、存活出 ICU 竞争事件和删失：尚未从现有院内文书、护理与医嘱重建；不是要求重复补提已有数据。医嘱可作为执行代理，但不能视为泵速时序。\n\n"
        "## 交付文件\n\n"
        f"- `{OUT.relative_to(ROOT)}`：逐 stay 三级审计表。\n"
        f"- `{SUMMARY.relative_to(ROOT)}`：计数、定义、文献依据和缺失原因。\n\n"
        "## 冻结边界\n\n"
        "本表为旧T0/床旁专项审计，不是最终DHF人数。最新全量episode时间重建和表型预审核见internal_validation/20260915_time_gated/，当前入口见RESEARCH_DASHBOARD.md。按用户确认使用现有原始资料及医嘱代理，随后对代理时间做敏感性更新。\n",
        encoding="utf-8",
    )
    print(json.dumps({"audit": str(OUT), "summary": str(SUMMARY), "report": str(REPORT), **summary["counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
