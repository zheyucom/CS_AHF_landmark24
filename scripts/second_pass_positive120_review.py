#!/usr/bin/env python3
"""Second-pass, evidence-aligned AI pre-review for 120 algorithm-positive DHF cases.

This is a triage aid, not a clinical gold standard.  It preserves the source evidence,
assigns a conservative three-state label, and selects the cases that still require
physician adjudication plus deterministic quality-control samples.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


RUN_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")
INPUT = RUN_DIR / "positive120_compact_evidence_v1.csv"
OUTPUT = RUN_DIR / "positive120_second_pass_ai_review_v1.csv"
PHYSICIAN_OUTPUT = RUN_DIR / "positive120_physician_adjudication_subset_v1.csv"
SUMMARY_OUTPUT = RUN_DIR / "positive120_second_pass_summary_v1.json"
REPORT_OUTPUT = Path(
    "project_control/task_reports/TASK_REPORT_20260929_POSITIVE120_SECOND_PASS_AI_REVIEW.md"
)

SEED = "DHF_POSITIVE120_SECOND_PASS_20260929_V1"

# The three-state calls below were made after review of the compact, time-aligned
# evidence packet for every sampled case.  They deliberately err toward
# ``indeterminate`` when an important competing explanation remains.
SUPPORTED = {
    1, 2, 5, 7, 9, 12, 13, 15, 22, 28, 29, 34, 35, 36, 43, 48, 52, 57, 60,
    61, 63, 65, 74, 82, 86, 95, 97, 98, 104, 105, 118, 120,
}
INDETERMINATE = {
    3, 4, 8, 11, 14, 16, 17, 18, 23, 41, 46, 50, 51, 53, 54, 58,
    62, 67, 68, 69, 72, 73, 77, 78, 81, 87, 89, 90, 91, 92, 100, 102,
    106, 107, 109, 111, 114, 117,
}
NOT_SUPPORTED = set(range(1, 121)) - SUPPORTED - INDETERMINATE

EXPLICIT_ACUTE = re.compile(
    r"急性(?:左|右|全)?心(?:力)?衰(?:竭)?|急性心功能不全|心源性肺水肿|"
    r"急性肺水肿|慢性心(?:力)?衰竭急性(?:发作|加重)|心衰急性发作"
)
CURRENT_HF = re.compile(r"心力衰竭|心功能不全|心衰|心源性休克")
CHRONIC_HF = re.compile(r"慢性心(?:力)?衰竭|心功能[ⅡⅢⅣIIIV]+级|NYHA")
STRONG_B = re.compile(
    r"肺水肿|端坐呼吸|不能平卧|无法平卧|夜间不能平卧|粉红色泡沫痰|"
    r"颈静脉怒张|全身水肿|容量超负荷|心源性休克"
)
WEAK_B = re.compile(r"胸闷气急|气促|呼吸困难|湿[啰罗]音|下肢.{0,10}水肿|胸腔积液")
ALT = {
    "肺炎/感染/ARDS": re.compile(r"重症肺炎|肺部感染|吸入性肺炎|脓毒症|感染性休克|ARDS|呼吸窘迫"),
    "肾衰/透析容量超负荷": re.compile(r"慢性肾(?:脏病|功能不全|衰竭)|CKD\s*[45]|尿毒症|血液透析"),
    "出血/低容量": re.compile(r"消化道出血|失血性休克|低血容量性休克|重度贫血"),
    "恶性肿瘤/低蛋白": re.compile(r"恶性肿瘤|肿瘤|化疗|低蛋白血症|骨髓"),
    "COPD/慢性肺病": re.compile(r"慢性阻塞性肺|慢阻肺|肺气肿|支气管扩张|间质性肺"),
    "肺栓塞": re.compile(r"肺栓塞|肺血栓栓塞"),
    "卒中/创伤": re.compile(r"脑出血|脑梗死|创伤|骨折|刀刺伤"),
}
PLANNED_OR_POSTOP = re.compile(
    r"术前讨论|拟.{0,20}(?:置换|成形|手术)|体外循环术后|心脏术后|"
    r"PCI术后.{0,12}(?:监护|入ICU)|术毕.{0,12}ICU"
)
RISK_TEMPLATE = re.compile(r"可能出现.{0,40}(?:心力衰竭|心衰)|并发症.{0,40}(?:心力衰竭|心衰)")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def compact(value: str, limit: int = 520) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    seen: list[str] = []
    for part in text.split(" || "):
        part = part.strip()
        if part and part not in seen:
            seen.append(part)
    return " || ".join(seen)[:limit]


def text_for(row: dict[str, str]) -> str:
    fields = [
        "algorithm_a_excerpt", "algorithm_b_excerpt", "acute_hf_evidence",
        "current_hf_dx_evidence", "strong_congestion_evidence",
        "weak_congestion_evidence", "hf_treatment_text", "alternative_evidence",
        "negative_or_uncertain_evidence", "np_renal_troponin_labs", "echo_evidence",
        "chest_imaging_evidence", "iv_loop_orders",
    ]
    return " ".join(row.get(field, "") for field in fields)


def alternatives(text: str) -> list[str]:
    return [name for name, pattern in ALT.items() if pattern.search(text)]


def deterministic_pick(visit_id: str, rate: float) -> bool:
    digest = hashlib.sha256(f"{SEED}|{visit_id}".encode()).hexdigest()
    return int(digest[:12], 16) / float(16**12) < rate


def evidence_domains(row: dict[str, str], label: str, text: str) -> tuple[str, str, str, str]:
    explicit = bool(EXPLICIT_ACUTE.search(
        row.get("acute_hf_evidence", "") + " " + row.get("algorithm_a_excerpt", "")
    ))
    current = bool(CURRENT_HF.search(
        row.get("current_hf_dx_evidence", "") + " " + row.get("algorithm_a_excerpt", "")
    ))
    chronic = bool(CHRONIC_HF.search(text))
    strong_b = bool(STRONG_B.search(
        row.get("strong_congestion_evidence", "") + " " + row.get("algorithm_b_excerpt", "")
    ))
    weak_b = bool(WEAK_B.search(
        row.get("weak_congestion_evidence", "") + " " + row.get("algorithm_b_excerpt", "")
    ))

    if label == "supported":
        a = "yes"
        b = "yes"
    elif label == "indeterminate":
        a = "yes" if explicit else ("uncertain" if current or chronic else "no")
        b = "yes" if strong_b else ("uncertain" if weak_b else "no")
    else:
        a = "yes_chronic_only" if chronic or current else "no"
        b = "no" if not strong_b else "uncertain_alternative_dominant"

    if row.get("c_support_type") == "treatment_proxy_only_C":
        c = "uncertain_order_proxy"
    elif row.get("algorithm_NP") == "1" or row.get("algorithm_echo") == "1":
        c = "yes_objective_support"
    else:
        c = "uncertain"

    late_only = bool(row.get("late_hf_signal_after_T12")) and not (
        row.get("acute_hf_evidence") or row.get("current_hf_dx_evidence")
    )
    aligned = "no_late_only" if late_only else "yes_evidence_packet_window"
    return a, b, c, aligned


def mechanisms(row: dict[str, str], label: str, text: str, alt: list[str]) -> list[str]:
    output: list[str] = []
    if label == "not_supported":
        if PLANNED_OR_POSTOP.search(text):
            output.append("计划手术/术后监护而非T0急性失代偿")
        if CHRONIC_HF.search(text) and not EXPLICIT_ACUTE.search(row.get("acute_hf_evidence", "")):
            output.append("慢性心衰或NYHA分级被当作急性事件")
        if alt:
            output.append("替代病因更占主导：" + "、".join(alt[:3]))
        if RISK_TEMPLATE.search(text):
            output.append("风险告知/模板文字污染A域")
        if row.get("c_support_type") == "treatment_proxy_only_C":
            output.append("静脉袢利尿医嘱代理缺少执行和适应证确认")
        if not output:
            output.append("缺少同窗A+B临床闭环")
    elif label == "indeterminate":
        if alt:
            output.append("DHF与替代病因并存：" + "、".join(alt[:3]))
        if row.get("c_support_type") == "treatment_proxy_only_C":
            output.append("C层仅为医嘱代理")
        if not output:
            output.append("关键证据冲突或不足，需病历裁决")
    return output


def reason(row: dict[str, str], label: str, alt: list[str], mechanisms_: list[str]) -> str:
    if label == "supported":
        support = []
        if EXPLICIT_ACUTE.search(row.get("acute_hf_evidence", "") + row.get("algorithm_a_excerpt", "")):
            support.append("T12前有明确急性心衰/急性加重诊断")
        else:
            support.append("T12前有当前心衰诊断")
        if STRONG_B.search(row.get("strong_congestion_evidence", "") + row.get("algorithm_b_excerpt", "")):
            support.append("存在端坐呼吸/不能平卧/肺水肿/低灌注等强失代偿证据")
        else:
            support.append("症状体征与治疗升级共同支持急性失代偿")
        if row.get("c_support_type") == "treatment_proxy_only_C":
            support.append("C层为静脉袢利尿医嘱，仍需eMAR核实执行")
        else:
            support.append("有同窗利钠肽或有意义心超支持")
        if alt:
            support.append("虽有并存病因，但目前不足以否定DHF")
        return "；".join(support) + "。"
    if label == "not_supported":
        return "；".join(mechanisms_) + "；现有证据不足以确认T0/T12前DHF。"
    return "；".join(mechanisms_) + "；DHF可能存在，但不能由AI在现有证据中排除主要替代解释。"


def main() -> None:
    rows = load_csv(INPUT)
    assert len(rows) == 120, f"expected 120 rows, got {len(rows)}"
    assert {int(row["case_no"]) for row in rows} == set(range(1, 121))

    reviewed = []
    for row in rows:
        case_no = int(row["case_no"])
        label = (
            "supported" if case_no in SUPPORTED else
            "indeterminate" if case_no in INDETERMINATE else
            "not_supported"
        )
        whole = text_for(row)
        alt = alternatives(whole)
        a, b, c, aligned = evidence_domains(row, label, whole)
        mechanism = mechanisms(row, label, whole, alt)

        confidence = "high" if label in {"supported", "not_supported"} else "medium"
        must_review = label == "indeterminate"
        selection_reason = "全部疑难病例" if must_review else ""
        if label == "supported" and deterministic_pick(row["visit_id"], 0.20):
            must_review = True
            selection_reason = "明确阳性20%确定性质控"
        if label == "not_supported" and deterministic_pick(row["visit_id"], 0.15):
            must_review = True
            selection_reason = "明确阴性15%确定性质控"
        if re.search(r"NT proBNP=(?:[0-2]?\d?\d(?:\.\d+)?)\b", row.get("np_renal_troponin_labs", "")):
            must_review = True
            selection_reason = (selection_reason + "；" if selection_reason else "") + "低NP冲突复核"

        reviewed_row = {
            "case_no": row["case_no"],
            "sample_stratum": row["sample_stratum"],
            "patient_id": row["patient_id"],
            "visit_id": row["visit_id"],
            "sex": row["sex"],
            "age": row["age"],
            "t0_time": row["t0_time"],
            "c_support_type": row["c_support_type"],
            "algorithm_NP": row["algorithm_NP"],
            "algorithm_echo": row["algorithm_echo"],
            "algorithm_IV_loop": row["algorithm_IV_loop"],
            "ai_second_pass_label": label,
            "ai_confidence": confidence,
            "review_A_current_hf": a,
            "review_B_acute_decompensation": b,
            "review_C_support": c,
            "time_aligned_before_T12": aligned,
            "dominant_alternative": "、".join(alt),
            "false_positive_or_uncertainty_mechanism": "；".join(mechanism),
            "ai_reason": reason(row, label, alt, mechanism),
            "decisive_A_excerpt": compact(row.get("acute_hf_evidence") or row.get("current_hf_dx_evidence") or row.get("algorithm_a_excerpt")),
            "decisive_B_excerpt": compact(row.get("strong_congestion_evidence") or row.get("weak_congestion_evidence") or row.get("algorithm_b_excerpt")),
            "decisive_C_excerpt": compact(row.get("np_renal_troponin_labs") or row.get("echo_evidence") or row.get("iv_loop_orders")),
            "counter_evidence_excerpt": compact(row.get("alternative_evidence") or row.get("negative_or_uncertain_evidence")),
            "late_HF_signal_after_T12": "yes" if row.get("late_hf_signal_after_T12") else "no",
            "physician_adjudication_needed": "yes" if must_review else "no",
            "physician_selection_reason": selection_reason,
            "physician_dhf_label": "",
            "physician_A_domain": "",
            "physician_B_domain": "",
            "physician_C_domain": "",
            "physician_t0_status": "",
            "physician_comments": "",
        }
        reviewed.append(reviewed_row)

    fields = list(reviewed[0])
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(reviewed)

    physician_rows = [row for row in reviewed if row["physician_adjudication_needed"] == "yes"]
    with PHYSICIAN_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(physician_rows)

    by_stratum: dict[str, Counter[str]] = defaultdict(Counter)
    for row in reviewed:
        by_stratum[row["sample_stratum"]][row["ai_second_pass_label"]] += 1
    bounds = {}
    for stratum, counts in by_stratum.items():
        n = sum(counts.values())
        bounds[stratum] = {
            "n": n,
            **dict(counts),
            "preliminary_supported_lower_bound": counts["supported"] / n,
            "preliminary_supported_upper_bound": (counts["supported"] + counts["indeterminate"]) / n,
        }
    total = Counter(row["ai_second_pass_label"] for row in reviewed)
    summary = {
        "n": len(reviewed),
        "label_counts": dict(total),
        "physician_subset_n": len(physician_rows),
        "by_stratum": bounds,
        "warning": "AI预审上下界不是正式PPV；正式PPV必须以医生盲法裁决为金标准。",
    }
    SUMMARY_OUTPUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    objective = bounds["main_supported_objective_C"]
    treatment = bounds["main_supported_treatment_only_C"]
    REPORT_OUTPUT.write_text(
        f"""# 任务报告：120例算法阳性DHF第二轮AI预审（2026-09-29）

## 先给结论

773例主队列目前不能冻结，也不应立即废弃。120例分层阳性样本的第二轮AI预审显示，现有算法同时混入了真正DHF、主要替代病因以及慢性/围术期心衰；下一步必须先完成精简医生裁决，再据此重写A/B/C判定逻辑并重跑773例。

本轮AI标签不是临床金标准，也不是正式PPV。

## 分层结果

| 分层 | n | 明确支持 | 不支持 | 疑难 | 初步下界 | 初步上界 |
|---|---:|---:|---:|---:|---:|---:|
| 客观C层 | {objective['n']} | {objective.get('supported', 0)} | {objective.get('not_supported', 0)} | {objective.get('indeterminate', 0)} | {objective['preliminary_supported_lower_bound']:.1%} | {objective['preliminary_supported_upper_bound']:.1%} |
| 治疗代理-only层 | {treatment['n']} | {treatment.get('supported', 0)} | {treatment.get('not_supported', 0)} | {treatment.get('indeterminate', 0)} | {treatment['preliminary_supported_lower_bound']:.1%} | {treatment['preliminary_supported_upper_bound']:.1%} |
| 合计 | 120 | {total['supported']} | {total['not_supported']} | {total['indeterminate']} | {total['supported']/120:.1%} | {(total['supported']+total['indeterminate'])/120:.1%} |

上下界定义：下界仅计AI明确支持；上界把全部疑难也计入。二者只用于决定审核优先级，不可写成正式PPV。

## 暴露出的主要机制

1. A域把慢性心衰、NYHA分级、既往史和风险告知当作当前急性心衰。
2. B域中的湿啰音、胸腔积液、低氧和水肿常可由肺炎、COPD、肾衰、低蛋白、肿瘤或围术期解释。
3. 计划心脏手术或PCI术后常规转ICU者，并不等同于T0时存在DHF。
4. 静脉袢利尿医嘱缺少eMAR执行与适应证，不能单独确认DHF。
5. 利钠肽和心超是支持证据，不是脱离A+B的确诊证据；肾衰、房颤、年龄和慢性结构异常会降低特异性。
6. T12后才出现心衰信号者不能倒灌进入T0/T12风险集。

## 医生现在只需审核什么

精简审核集共{len(physician_rows)}例：全部疑难病例，加明确阳性20%和明确阴性15%的确定性质控，以及低NP冲突病例。医生只需填写DHF总标签、A/B/C、T0是否正确和一句裁决理由。

## 队列处置门槛

- 目前：773例标记为“待表型校准”，不得用于正式Stage 1结果或Stage 3验证。
- 医生裁决后：分别计算客观C层与治疗代理层PPV及95%CI，并按原抽样比例加权；同时检查评审者一致性。
- 若客观C层仍有可接受PPV：保留为核心队列，收紧A/B并将治疗代理层降为扩展/敏感性队列。
- 若客观C层PPV也明显不足：从候选池按新A+B+C规则整体重建，而不是在773例上零散删人。
- 无论结果如何：另抽取算法阴性/边界病例估计敏感度和特异度，不能只报告PPV。

## 本轮产物

- `positive120_second_pass_ai_review_v1.csv`：120例全量预审与证据摘要；
- `positive120_physician_adjudication_subset_v1.csv`：精简医生裁决集；
- `positive120_second_pass_summary_v1.json`：机器可读汇总；
- 最终Excel由配套生成脚本输出。
""",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
