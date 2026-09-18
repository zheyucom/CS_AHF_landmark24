#!/usr/bin/env python3
"""Build a versioned patient-level DHF evidence audit.

The output separates imaging modality, echo procedure availability, and
actual echo-result availability. It is a rule-supported operational phenotype
audit, not a clinical gold-standard diagnosis.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "project_control/bigquery"
CANDIDATES = BASE / "dhf_radiology_candidates.csv"
RAW = BASE / "dhf_radiology_raw_v2.csv"
OUTCOME = ROOT / "project_control/runs/20260827_v3_2_outcome_label_audit/data/096_strict_main_label_v33.csv"
ECHO = BASE / "structured_echo_screen_v33.csv"
OUTPUT_DIR = BASE / "controlled_annotation_20260830_v2/processed_20260903"

# Only inspect examination/title/technique text near the report start. Searching
# the whole report would misclassify a chest radiograph that merely compares
# itself with a chest CT, or an abdominal/head CT whose indication mentions a
# chest study.
SECTION_RE = re.compile(
    r"^\s*(?P<label>examination|exam|study|procedure|technique|indication|clinical history|history|comparison|comparisons|findings|impression|comment|clinical information)\s*:\s*",
    re.I,
)
CT_RE = re.compile(
    r"\b(?:ct|cta)\b[^\n]{0,100}\b(?:chest|thorax)\b"
    r"|\b(?:chest|thorax)\b[^\n]{0,100}\b(?:ct|cta)\b"
    r"|\bcomputed\s+tomograph(?:y|ic)\b[^\n]{0,100}\b(?:chest|thorax)\b"
    r"|\b(?:chest|thorax)\b[^\n]{0,100}\bcomputed\s+tomograph(?:y|ic)\b",
    re.I,
)
CXR_RE = re.compile(
    r"\b(?:portable\s+)?(?:ap|pa)\s+(?:portable\s+)?chest\b"
    r"|\b(?:portable\s+)?chest\s+(?:radiograph|x[- ]?ray)\b"
    r"|\bchest\s+(?:pa\s+and\s+lat(?:eral)?|two\s+views|2\s+views|portable\s+ap)\b"
    r"|\b(?:pa\s+and\s+lat(?:eral)?|two\s+views|2\s+views)\s+of\s+the\s+chest\b"
    r"|\bportable\s+chest\b"
    r"|\bchest\s*\(\s*(?:portable\s+)?(?:ap|pa\s+and\s+lat(?:eral)?)\s*\)",
    re.I,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def flag(row: dict[str, str], key: str) -> bool:
    return row.get(key, "") in {"1", "1.0", "True", "true"}


def modality(text: str) -> str:
    header_parts: list[str] = []
    current_section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        section = SECTION_RE.match(line)
        if section:
            current_section = section.group("label").lower()
            if current_section in {"findings", "impression", "comment"}:
                break
            if current_section in {"examination", "exam", "study", "procedure", "technique"}:
                header_parts.append(line[section.end():])
            continue
        if current_section in {"examination", "exam", "study", "procedure", "technique"}:
            header_parts.append(line)
            continue
        # Some legacy reports use a direct title such as "AP CHEST, 6:35
        # P.M." without an EXAMINATION/STUDY label. CXR titles are safe to
        # recognize after a history section; CT titles are restricted to the
        # report preamble so comparison continuations cannot trigger them.
        direct_cxr = re.search(
            r"^(?:ap|pa)\s+(?:portable\s+)?chest\b"
            r"|^portable\s+chest\b"
            r"|^two\s+views\s+of\s+the\s+chest\b",
            line,
            re.I,
        )
        direct_ct = (
            current_section is None
            and re.search(
                r"^computed\s+tomograph(?:y|ic)\b[^\n]{0,100}\b(?:chest|thorax)\b"
                r"|^(?:ct|cta)\b[^\n]{0,100}\b(?:chest|thorax)\b",
                line,
                re.I,
            )
        )
        if direct_cxr or direct_ct:
            header_parts.append(line)
    header = "\n".join(header_parts)
    if CT_RE.search(header):
        return "chest_ct"
    if re.fullmatch(r"\s*chest\s*", header, re.I) or CXR_RE.search(header):
        return "chest_xray"
    return "other_or_unclassified"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def outcome_counts(rows: list[dict[str, object]]) -> tuple[int, int, int]:
    return (
        sum(row["final_state"] == "event" for row in rows),
        sum(row["final_state"] == "compete" for row in rows),
        sum(row["final_state"] == "censor" for row in rows),
    )


def main() -> None:
    candidates = {
        row["stay_id"]: row for row in read_csv(CANDIDATES)
        if row.get("admittime", "") <= row.get("intime", "")
    }
    raw = read_csv(RAW)
    outcomes = {row["stay_id"]: row for row in read_csv(OUTCOME)}
    echo = {row["stay_id"]: row for row in read_csv(ECHO)}
    valid_ids = set(candidates) & set(outcomes)

    reports_by_stay: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        if row["stay_id"] in valid_ids:
            row = dict(row)
            row["modality"] = modality(row.get("text", ""))
            reports_by_stay[row["stay_id"]].append(row)

    rows: list[dict[str, object]] = []
    for stay_id in sorted(valid_ids, key=int):
        candidate = candidates[stay_id]
        reports = reports_by_stay.get(stay_id, [])
        definite = [
            r for r in reports
            if flag(r, "positive_congestion_evidence_flag")
            and not flag(r, "uncertainty_hit")
            and r["modality"] in {"chest_xray", "chest_ct"}
        ]
        definite_cxr = [r for r in definite if r["modality"] == "chest_xray"]
        definite_ct = [r for r in definite if r["modality"] == "chest_ct"]
        available_definite = [r for r in definite if flag(r, "report_available_pre_t0_flag")]
        available_nonchest_definite = [
            r for r in reports
            if flag(r, "positive_congestion_evidence_flag")
            and not flag(r, "uncertainty_hit")
            and r["modality"] == "other_or_unclassified"
            and flag(r, "report_available_pre_t0_flag")
        ]
        available_cxr = [r for r in available_definite if r["modality"] == "chest_xray"]
        available_ct = [r for r in available_definite if r["modality"] == "chest_ct"]
        echo_row = echo.get(stay_id, {})
        echo_procedure = flag(echo_row, "echo_any_procedure_pre12_flag")
        echo_lvef = flag(echo_row, "structured_lvef_pre12_available_flag")
        # A procedure or an isolated LVEF value is not an abnormal echo
        # interpretation.  Keep these states separate until a report/result
        # source supports an explicit abnormality adjudication.
        echo_result_available = echo_lvef
        echo_abnormal_support = flag(echo_row, "echo_abnormal_support_pre12_flag")
        # The candidate export was generated from hf_icd_any=1. Acute/acute-on-
        # chronic coding is retained as a descriptive audit field, not the
        # inclusion anchor, because DHF may be de novo or gradually recognized.
        hf_anchor = True
        loop = flag(candidate, "pre_t0_iv_loop_emar_flag")
        ntprobnp = flag(candidate, "pre_t0_ntprobnp_ge300_flag")
        management = loop
        objective = bool(available_definite) or echo_abnormal_support
        final_state = outcomes[stay_id].get("final_state", "")
        rows.append({
            "stay_id": stay_id,
            "subject_id": candidate["subject_id"],
            "hadm_id": candidate["hadm_id"],
            "hf_icd_anchor_flag": int(hf_anchor),
            "acute_hf_icd_anchor_flag": int(flag(candidate, "acute_hf_icd_anchor_flag")),
            "pre_t0_iv_loop_flag": int(loop),
            "pre_t0_ntprobnp_support_flag": int(ntprobnp),
            "n_pre_t0_reports": len(reports),
            "n_pre_t0_chest_xray_reports": sum(r["modality"] == "chest_xray" for r in reports),
            "n_pre_t0_chest_ct_reports": sum(r["modality"] == "chest_ct" for r in reports),
            "n_pre_t0_other_or_unclassified_reports": sum(r["modality"] == "other_or_unclassified" for r in reports),
            "definite_cxr_charttime_flag": int(bool(definite_cxr)),
            "definite_ct_charttime_flag": int(bool(definite_ct)),
            "definite_cxr_or_ct_charttime_flag": int(bool(definite_cxr or definite_ct)),
            "definite_cxr_available_pre_t0_flag": int(bool(available_cxr)),
            "definite_ct_available_pre_t0_flag": int(bool(available_ct)),
            "definite_cxr_or_ct_available_pre_t0_flag": int(bool(available_cxr or available_ct)),
            "definite_nonchest_available_pre_t0_flag": int(bool(available_nonchest_definite)),
            "echo_procedure_pre12_flag": int(echo_procedure),
            "echo_procedure_0_12h_flag": int(flag(echo_row, "echo_any_procedure_0_12h_flag")),
            "structured_lvef_available_pre12_flag": int(echo_lvef),
            "structured_lvef_last_lt40_flag": int(flag(echo_row, "structured_lvef_last_lt40_flag")),
            "echo_result_available_pre12_flag": int(echo_result_available),
            "echo_abnormal_support_pre12_flag": int(echo_abnormal_support),
            "echo_result_supported_flag": int(echo_abnormal_support),
            "multidomain_cxr_or_ct_loop_flag": int(bool(available_cxr or available_ct) and management),
            "multidomain_cxr_or_ct_loop_or_ntprobnp_flag": int(bool(available_cxr or available_ct) and (loop or ntprobnp)),
            "multidomain_echo_result_loop_flag": int(echo_abnormal_support and management),
            "multidomain_echo_or_lung_loop_flag": int(objective and management),
            "final_state": final_state,
            "event_flag": int(final_state == "event"),
            "competing_alive_icu_discharge_flag": int(final_state == "compete"),
            "administrative_censor_flag": int(final_state == "censor"),
        })

    if len(rows) != 5549:
        raise SystemExit(f"Expected 5,549 rows after outcome reconciliation, got {len(rows)}")

    prefix = "dhf_multidomain_patient_level_audit_20260903"
    write_csv(OUTPUT_DIR / f"{prefix}.csv", rows)

    definitions = {
        "broad_hf_anchor": lambda r: r["hf_icd_anchor_flag"] == 1,
        "radiology_cxr_available": lambda r: r["definite_cxr_available_pre_t0_flag"] == 1,
        "radiology_ct_available": lambda r: r["definite_ct_available_pre_t0_flag"] == 1,
        "radiology_cxr_or_ct_available": lambda r: r["definite_cxr_or_ct_available_pre_t0_flag"] == 1,
        "radiology_cxr_and_ct_available": lambda r: r["definite_cxr_available_pre_t0_flag"] == 1 and r["definite_ct_available_pre_t0_flag"] == 1,
        "radiology_cxr_or_ct_plus_iv_loop": lambda r: r["multidomain_cxr_or_ct_loop_flag"] == 1,
        "radiology_cxr_or_ct_plus_iv_loop_or_ntprobnp": lambda r: r["multidomain_cxr_or_ct_loop_or_ntprobnp_flag"] == 1,
        "echo_result_plus_iv_loop": lambda r: r["multidomain_echo_result_loop_flag"] == 1,
        "echo_or_lung_objective_plus_iv_loop": lambda r: r["multidomain_echo_or_lung_loop_flag"] == 1,
    }
    audit: list[dict[str, object]] = []
    for name, predicate in definitions.items():
        subset = [r for r in rows if predicate(r)]
        event, compete, censor = outcome_counts(subset)
        n = len(subset)
        audit.append({
            "phenotype": name,
            "rule_status": "rule_supported_operational_phenotype",
            "n_stays": n,
            "events": event,
            "competing_alive_icu_discharge": compete,
            "administrative_censor": censor,
            "event_rate": round(event / n, 6) if n else None,
            "epv_at_45_predictors": round(event / 45, 4) if n else None,
            "definition": {
                "broad_hf_anchor": "candidate export source hf_icd_any=1; no DHF confirmation",
                "radiology_cxr_available": "HF anchor + pre-T0 available definite congestion on CXR",
                "radiology_ct_available": "HF anchor + pre-T0 available definite congestion on chest CT",
                "radiology_cxr_or_ct_available": "HF anchor + pre-T0 available definite congestion on CXR or chest CT",
                "radiology_cxr_and_ct_available": "HF anchor + both CXR and chest CT available with definite congestion",
                "radiology_cxr_or_ct_plus_iv_loop": "CXR or CT objective congestion + pre-T0 IV loop",
                "radiology_cxr_or_ct_plus_iv_loop_or_ntprobnp": "CXR or CT objective congestion + IV loop or NT-proBNP support",
                "echo_result_plus_iv_loop": "echo result explicitly supporting structural/functional abnormality + pre-T0 IV loop; unavailable in current MIMIC audit",
                "echo_or_lung_objective_plus_iv_loop": "echo abnormality or CXR/CT objective evidence + pre-T0 IV loop",
            }[name],
        })
    write_csv(OUTPUT_DIR / f"{prefix}_outcome_epv.csv", audit)

    modality_counts = Counter()
    for report in raw:
        modality_counts[modality(report.get("text", ""))] += 1
    with (OUTPUT_DIR / "DHF_MULTIDOMAIN_AUDIT_2026-09-03.md").open("w", encoding="utf-8") as handle:
        handle.write("# DHF 多域证据患者级审计\n\n")
        handle.write("日期：2026-09-03\n\n")
        handle.write("## 当前入组口径\n\n")
        handle.write("成人 ICU 患者在 `[T0-24 h, T12)` 内具备可追溯 DHF 操作性表型；不要求 T0 入 ICU 时已经完成 DHF 诊断。所有证据必须早于 T12，T12 后信息不得回填入组。\n\n")
        handle.write("院内严格主队列要求每例满足心超三级 QC：实际完成 TTE/TEE/心脏 POCUS 或床旁心超、结果在 T12 前可用、且结果支持心脏结构或功能异常；未检查/结果不可用者保留在全 ICU 选择性审计层，不能判为阴性。当前 MIMIC 本地结构化表仅能审计 TTE/TEE 检查发生；没有可用的完整心超结果或异常判定来源，因此当前 MIMIC 不能称为 `echo-confirmed`。\n\n")
        handle.write("CXR 与胸部 CT 是互补肺部证据，主规则为 OR；`CXR AND CT` 仅作为极严格敏感性分析，不作为主纳入门槛，因为临床上并非每位患者都需要两种检查。模态分类只读取报告开头的检查名称/技术段；腹部、头部、脊柱等 CT，以及比较段中提到的 CT 不进入胸部 CT 层。\n\n")
        handle.write("## 抽取覆盖与全量结果\n\n")
        handle.write(f"106/107 原始报告按可解释检查类型初步分为：CXR {modality_counts['chest_xray']}、胸部 CT {modality_counts['chest_ct']}、其他/未分类 {modality_counts['other_or_unclassified']}。这只是模态规则审计，尚未等同人工影像诊断。\n\n")
        handle.write("| 表型层 | stays | event | compete | censor | EPV/45 |\n|---|---:|---:|---:|---:|---:|\n")
        for row in audit:
            handle.write(f"| `{row['phenotype']}` | {row['n_stays']} | {row['events']} | {row['competing_alive_icu_discharge']} | {row['administrative_censor']} | {row['epv_at_45_predictors']} |\n")
        handle.write("\n所有层均为规则支持的 operational phenotype，不是全量人工确诊 DHF。\n\n")
        handle.write("## 解释边界\n\n")
        handle.write("1. BNP/NT-proBNP 只能作支持证据，不能单独 rule-in DHF；肾功能、年龄、房颤、肺部疾病、PE 和脓毒症均可影响数值。\n")
        handle.write("2. HF ICD anchor 来自候选导出的 `hf_icd_any=1`；acute/acute-on-chronic 编码只作描述性审计，不等于 T12 前实际失代偿。最终表型需要临床/客观证据和管理/治疗域。\n")
        handle.write("3. 影像文本 regex 仅经报告级分层人工验证，不能替代患者级金标准。\n")
        handle.write("4. `echo_procedure_pre12_flag=1` 只说明做过 TTE/TEE；单独的结构化 LVEF 数值只能说明部分结果可用，不能直接说明存在异常。必须有可解析报告/结构化结果并单独完成 `echo_abnormal_support_pre12_flag` 判定。当前字段 `echo_result_available_pre12_flag` 与 `echo_abnormal_support_pre12_flag` 均不应由 procedure flag 推导。\n")
        handle.write("5. 院内严格主队列为 `echo-supported DHF`；宽口径多域层仅作桥接/敏感性分析。应先冻结最终表型，再按事件数重新冻结低维预测器；当前 45 个预测器不可直接用于低事件层。\n")
    print(f"Wrote {prefix} outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
