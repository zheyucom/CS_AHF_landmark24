#!/usr/bin/env python3
"""AI-assisted pre-triage for the 290-case DHF phenotype calibration sample.

This script does not create a clinical gold standard. It extracts time-aligned evidence,
assigns transparent pre-review labels, and selects a smaller physician-review subset with
known sampling probabilities for later verification-bias adjustment.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


RUN_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")
SAMPLE_PATH = RUN_DIR / "clinical_review_sample_v1.csv"
NP_AUDIT_PATH = RUN_DIR / "clinical_review_290_np_window_audit_v1.csv"
PHYSICIAN_PATH = RUN_DIR / "clinical_review_first30_physician_labels_20260927.csv"
T0_CORRECTION_PATH = Path(
    "project_control/internal_validation/20260927_manual_review/t0_manual_corrections_v1.csv"
)
OUTPUT_ALL = RUN_DIR / "clinical_review_290_ai_pretriage_v1.csv"
OUTPUT_PHYSICIAN = RUN_DIR / "clinical_review_physician_subset_ai_triaged_v1.csv"
OUTPUT_SUMMARY = RUN_DIR / "clinical_review_290_ai_pretriage_summary_v1.json"
OUTPUT_METHOD = RUN_DIR / "AI_PRETRIAGE_METHOD_NOTE_V1_20260928.md"
LOW_NP_TARGET_PATH = RUN_DIR / "low_ntprobnp_under300_targeted_review_v1.csv"
LOW_NP_AI_OUTPUT = RUN_DIR / "low_ntprobnp_under300_ai_review_v1.csv"

SEED = "DHF_AI_PRETRIAGE_20260928_V1"
QC_RATE_CLEAR_NO = 0.15
QC_RATE_CLEAR_YES = 0.20
QC_RATE_LIKELY = 0.15


HF_TERMS = re.compile(
    r"急性(?:左|右|全)?心(?:力)?衰(?:竭)?|急性心功能不全|"
    r"失代偿(?:性)?心(?:力)?衰(?:竭)?|心源性肺水肿|心源性休克|"
    r"心力衰竭|心功能不全|心衰"
)
EXPLICIT_ACUTE_HF = re.compile(
    r"急性(?:左|右|全)?心(?:力)?衰(?:竭)?|急性心功能不全|"
    r"失代偿(?:性)?心(?:力)?衰(?:竭)?|心源性肺水肿"
)
CURRENT_DIAGNOSIS_HF = re.compile(
    r"(?:入ICU诊断|转入ICU诊断|当前诊断|初步诊断|修正诊断|临床诊断|诊断)"
    r".{0,60}?(?:心力衰竭|心功能不全|心衰|心源性休克)"
)
CHRONIC_OR_HISTORY_HF = re.compile(
    r"慢性心力衰竭|慢性心功能不全|心衰史|既往.{0,20}(?:心衰|心功能不全)|"
    r"心功能[ⅡIIⅢIV二三四]+级|NYHA"
)
TEMPLATE_BLOCKERS = re.compile(
    r"风险|可能出现|可出现|并发症|告知|鉴别诊断|待排|不排除|"
    r"否认|无|未见|未及|未闻及|不伴|暂不考虑|不考虑|可能性小|"
    r"排除|可疑|可能|拟诊|待查|倾向|[？?]"
)
EXCLUDED_NOTE_TITLES = re.compile(
    r"知情同意|谈话记录|APACHE|评分|评估单|风险告知|拒绝治疗|"
    r"护理计划|健康教育|授权委托|手术安全核查"
)

STRONG_B = re.compile(
    r"心源性肺水肿|肺水肿|肺淤血|肺充血|端坐呼吸|不能平卧|无法平卧|"
    r"夜间阵发性呼吸困难|粉红色泡沫痰|颈静脉怒张|容量超负荷|液体潴留"
)
DYSPNEA = re.compile(r"胸闷气急|气促|呼吸困难|呼吸急促|氧合下降|低氧")
RALES = re.compile(r"湿[啰罗]音|水泡音")
EDEMA = re.compile(r"双下肢.{0,12}水肿|全身水肿|凹陷性水肿|胸腔积液")
LOW_OUTPUT = re.compile(r"低心排|低灌注|心源性休克")

ALT_PATTERNS = {
    "肺炎/感染": re.compile(r"重症肺炎|肺部感染|吸入性肺炎|脓毒症|败血症"),
    "ARDS": re.compile(r"ARDS|急性呼吸窘迫综合征", re.I),
    "肺栓塞": re.compile(r"肺栓塞"),
    "出血/低容量": re.compile(r"失血性休克|消化道出血|大出血|低血容量"),
    "卒中/神经重症": re.compile(r"脑出血|蛛网膜下腔出血|脑梗死|动脉瘤破裂"),
    "创伤/术后": re.compile(r"多发伤|创伤|术后|手术后"),
    "COPD/哮喘": re.compile(r"慢性阻塞性肺|COPD|哮喘"),
    "肾衰/容量管理": re.compile(r"慢性肾脏病|肾功能衰竭|CKD\s*[45]|尿毒症|血液透析"),
    "低蛋白/肝病": re.compile(r"低蛋白血症|肝硬化"),
    "心包积液": re.compile(r"大量心包积液|心包填塞"),
}

STRONG_ECHO = re.compile(
    r"左室收缩功能(?:明显)?(?:减低|降低|不全)|右心功能不全|"
    r"右室收缩功能(?:明显)?(?:减低|降低)|舒张功能(?:明显)?(?:减低|障碍)|"
    r"重度(?:二尖瓣|三尖瓣|主动脉瓣).{0,8}(?:反流|狭窄)|"
    r"(?:二尖瓣|三尖瓣|主动脉瓣).{0,8}重度(?:反流|狭窄)|"
    r"重度肺动脉高压"
)
MILD_ECHO = re.compile(r"轻度.{0,12}反流|少量反流|左室肥厚|心包少量积液")
EF_PATTERN = re.compile(r"(?:EF|LVEF)\s*[:：]?\s*(\d{1,3})(?:\s*%)?", re.I)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("&gt;", ">").replace("&lt;", "<")).strip()


def nonblocked_matches(pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
    matches = []
    for match in pattern.finditer(text):
        context = text[max(0, match.start() - 35) : min(len(text), match.end() + 35)]
        if not TEMPLATE_BLOCKERS.search(context):
            matches.append(match)
    return matches


def snippets(text: str, pattern: re.Pattern[str], radius: int = 100, limit: int = 3) -> list[str]:
    output = []
    for match in pattern.finditer(text):
        item = text[max(0, match.start() - radius) : min(len(text), match.end() + radius)]
        item = normalize_text(item)
        if item and item not in output:
            output.append(item)
        if len(output) >= limit:
            break
    return output


def classify_a(text: str, algorithm_flag: str) -> tuple[str, list[str]]:
    reasons = []
    if nonblocked_matches(EXPLICIT_ACUTE_HF, text):
        return "strong", ["明确急性心衰/心源性肺水肿表述"]
    if nonblocked_matches(CURRENT_DIAGNOSIS_HF, text):
        return "moderate", ["当前诊断段存在心衰锚点"]
    if algorithm_flag == "1":
        if CHRONIC_OR_HISTORY_HF.search(text) or TEMPLATE_BLOCKERS.search(text):
            return "weak", ["仅见慢性/既往/模板性心衰表述"]
        return "weak", ["算法A域阳性，但T12前原文缺少可确认的当前锚点"]
    if HF_TERMS.search(text):
        reasons.append("存在心衰词，但算法未形成当前锚点")
        return "weak", reasons
    return "absent", ["未见当前心衰锚点"]


def classify_b(text: str, algorithm_flag: str) -> tuple[str, list[str]]:
    if nonblocked_matches(STRONG_B, text) or nonblocked_matches(LOW_OUTPUT, text):
        return "strong", ["存在特异性较高的急性充血/失代偿证据"]
    dyspnea = bool(nonblocked_matches(DYSPNEA, text))
    rales = bool(nonblocked_matches(RALES, text))
    edema = bool(nonblocked_matches(EDEMA, text))
    if dyspnea and (rales or edema):
        return "moderate", ["呼吸困难合并湿啰音/水肿"]
    if dyspnea or rales or edema:
        return "weak", ["仅有非特异症状体征"]
    if algorithm_flag == "1":
        return "weak", ["算法B域阳性，但T12前原文缺少可确认的失代偿证据"]
    return "absent", ["未见当前失代偿证据"]


def echo_strength(text: str) -> tuple[str, str, str]:
    values = [int(item) for item in EF_PATTERN.findall(text) if 0 <= int(item) <= 100]
    min_ef = min(values) if values else None
    if min_ef is not None and min_ef <= 40:
        return "strong", str(min_ef), f"LVEF/EF最低{min_ef}%"
    if STRONG_ECHO.search(text):
        return "strong", "" if min_ef is None else str(min_ef), "存在明显结构/功能异常"
    if min_ef is not None and 41 <= min_ef < 50:
        return "moderate", str(min_ef), f"LVEF/EF最低{min_ef}%"
    if MILD_ECHO.search(text):
        return "weak", "" if min_ef is None else str(min_ef), "仅轻度/非特异心超异常"
    return "absent", "" if min_ef is None else str(min_ef), "未提取到支持DHF的心超异常"


def deterministic_qc(visit_id: str, rate: float) -> bool:
    value = int(hashlib.sha256(f"{SEED}|{visit_id}".encode()).hexdigest()[:12], 16)
    return value / float(16**12) < rate


def main() -> None:
    sample_rows = load_csv(SAMPLE_PATH)
    sample = {row["visit_id"]: row for row in sample_rows}
    physician = {row["visit_id"]: row for row in load_csv(PHYSICIAN_PATH)}
    np_audit = {row["visit_id"]: row for row in load_csv(NP_AUDIT_PATH)}
    t0_corrections = {row.get("visit_id", ""): row for row in load_csv(T0_CORRECTION_PATH)}

    notes_early: dict[str, list[tuple[datetime, str, str]]] = defaultdict(list)
    notes_late: dict[str, list[tuple[datetime, str, str]]] = defaultdict(list)
    note_hf_times: dict[str, list[datetime]] = defaultdict(list)
    note_b_times: dict[str, list[datetime]] = defaultdict(list)
    alt_by_visit: dict[str, Counter[str]] = defaultdict(Counter)

    for path in glob.glob("DHF_SRR/*文书*/02_rdr_medrecord_list.csv"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
            for record in csv.DictReader(handle):
                visit_id = record.get("就诊号", "")
                if visit_id not in sample:
                    continue
                created = parse_dt(record.get("创建日期", ""))
                if created is None:
                    continue
                t0 = parse_dt(sample[visit_id]["t0_time"])
                if t0 is None or not (t0 - timedelta(hours=24) <= created <= t0 + timedelta(hours=72)):
                    continue
                text = normalize_text(record.get("文本病历", ""))
                title = normalize_text(record.get("文书名称", ""))
                if not text:
                    continue
                classifiable = not EXCLUDED_NOTE_TITLES.search(title)
                if classifiable and (
                    nonblocked_matches(EXPLICIT_ACUTE_HF, text)
                    or nonblocked_matches(CURRENT_DIAGNOSIS_HF, text)
                ):
                    note_hf_times[visit_id].append(created)
                if classifiable and nonblocked_matches(STRONG_B, text):
                    note_b_times[visit_id].append(created)
                is_early = created < t0 + timedelta(hours=12)
                if is_early and classifiable:
                    for category, pattern in ALT_PATTERNS.items():
                        if pattern.search(text):
                            alt_by_visit[visit_id][category] += 1
                focus = re.compile(
                    r"急性心|心力衰竭|心功能不全|心衰|心源性|肺水肿|肺淤血|端坐呼吸|"
                    r"不能平卧|无法平卧|粉红色泡沫痰|湿[啰罗]音|水肿|胸闷气急|"
                    r"重症肺炎|肺部感染|ARDS|肺栓塞|失血性休克|消化道出血|脑出血|"
                    r"蛛网膜下腔出血|脑梗死|肾功能衰竭|CKD|低蛋白血症"
                )
                selected = snippets(text, focus, radius=120, limit=4)
                if selected and classifiable:
                    target = notes_early if is_early else notes_late
                    target[visit_id].append((created, title, " || ".join(selected)))

    exams: dict[str, list[tuple[datetime, str, str]]] = defaultdict(list)
    for path in glob.glob("DHF_SRR/*检查*/02_rdr_exam_master_report.csv"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
            for record in csv.DictReader(handle):
                visit_id = record.get("就诊号", "")
                if visit_id not in sample:
                    continue
                report_time = parse_dt(record.get("检查[报告]日期", ""))
                t0 = parse_dt(sample[visit_id]["t0_time"])
                if report_time is None or t0 is None:
                    continue
                if not (t0 - timedelta(hours=24) <= report_time < t0 + timedelta(hours=12)):
                    continue
                item = normalize_text(record.get("项目名称", ""))
                exam_type = normalize_text(record.get("检查类型", ""))
                conclusion = normalize_text(record.get("检查结论", ""))
                findings = normalize_text(record.get("检查所见", ""))
                whole = " ".join([item, exam_type, conclusion, findings])
                if re.search(r"心脏|心动图|胸部|胸片|肺|CT", whole, re.I):
                    exams[visit_id].append((report_time, item or exam_type, whole[:1600]))

    results = []
    for visit_id, row in sample.items():
        t0 = parse_dt(row["t0_time"])
        note_entries = sorted(notes_early.get(visit_id, []), key=lambda item: item[0])
        late_note_entries = sorted(notes_late.get(visit_id, []), key=lambda item: item[0])
        note_text = " || ".join(item[2] for item in note_entries)
        # Only time-aligned raw notes enter the AI label. The historical A/B excerpts may
        # contain later documentation and are retained solely for audit display.
        evidence_text = normalize_text(note_text)
        exam_entries = sorted(exams.get(visit_id, []), key=lambda item: item[0])
        exam_text = " || ".join(item[2] for item in exam_entries)

        a_quality, a_reason = classify_a(evidence_text, row["a_hf_anchor_flag"])
        b_quality, b_reason = classify_b(evidence_text, row["b_decompensation_flag"])
        echo_quality, min_ef, echo_reason = echo_strength(exam_text)
        np_row = np_audit.get(visit_id, {})
        strong_negative_np = np_row.get("np_all_values_strong_negative", "0") == "1"
        np_measured = np_row.get("np_measured_t0m24_to_t12", "0") == "1"
        np_rule_in = row["c_ntprobnp_rule_in_flag"] == "1"
        iv_proxy = row["c_iv_loop_order_proxy_flag"] == "1"

        hf_times = sorted(note_hf_times.get(visit_id, []))
        b_times = sorted(note_b_times.get(visit_id, []))
        first_hf_time = hf_times[0] if hf_times else None
        first_b_time = b_times[0] if b_times else None
        early_hf = bool(t0 and any(item < t0 + timedelta(hours=12) for item in hf_times))
        early_b = bool(t0 and any(item < t0 + timedelta(hours=12) for item in b_times))
        late_hf_evidence = bool(
            t0 and not early_hf and any(item >= t0 + timedelta(hours=12) for item in hf_times)
        )
        late_b_evidence = bool(
            t0 and not early_b and any(item >= t0 + timedelta(hours=12) for item in b_times)
        )
        t0_issue = visit_id in t0_corrections

        alt_counts = alt_by_visit.get(visit_id, Counter())
        alt_categories = [name for name, count in alt_counts.most_common() if count]
        dominant_alt = any(
            name in alt_categories
            for name in [
                "肺炎/感染",
                "ARDS",
                "肺栓塞",
                "出血/低容量",
                "卒中/神经重症",
                "创伤/术后",
                "COPD/哮喘",
                "心包积液",
            ]
        )

        explicit_acute = bool(nonblocked_matches(EXPLICIT_ACUTE_HF, evidence_text))
        strong_a = a_quality == "strong"
        adequate_a = a_quality in {"strong", "moderate"}
        strong_b = b_quality == "strong"
        adequate_b = b_quality in {"strong", "moderate"}
        objective_c = np_rule_in or echo_quality in {"strong", "moderate"}
        any_c = objective_c or iv_proxy

        mechanisms = []
        conflicts = []
        if a_quality in {"absent", "weak"}:
            mechanisms.append("当前心衰锚点缺失或仅慢性/模板表述")
        if b_quality in {"absent", "weak"}:
            mechanisms.append("B域仅非特异症状体征或缺失")
        if row["c_support_type"] == "treatment_proxy_only_C":
            mechanisms.append("C域仅静脉袢利尿医嘱代理")
        if echo_quality == "weak" and row["c_echo_abnormal_flag"] == "1":
            mechanisms.append("心超仅轻度/非特异异常")
        if dominant_alt:
            mechanisms.append("存在可独立解释表现的替代诊断")
        if np_rule_in and ("肾衰/容量管理" in alt_categories):
            mechanisms.append("NT-proBNP升高可能受肾衰影响")
        if late_hf_evidence or late_b_evidence:
            mechanisms.append("心衰/失代偿证据可能晚于T12")
        if strong_negative_np:
            conflicts.append("同窗NT-proBNP均<300 pg/mL")
        if t0_issue:
            conflicts.append("T0已有人工纠正记录")

        if t0_issue:
            label = "uncertain"
            confidence = "low"
        elif strong_negative_np and not (explicit_acute and strong_b):
            label = "clear_no" if not adequate_a else "likely_no"
            confidence = "high" if label == "clear_no" else "medium"
        elif strong_a and strong_b and any_c and not (late_hf_evidence or late_b_evidence):
            if dominant_alt and not objective_c:
                label = "uncertain"
                confidence = "low"
            elif dominant_alt:
                label = "likely_yes"
                confidence = "medium"
            else:
                label = "clear_yes"
                confidence = "high"
        elif adequate_a and adequate_b and objective_c and not (late_hf_evidence or late_b_evidence):
            label = "uncertain" if dominant_alt else "likely_yes"
            confidence = "low" if dominant_alt else "medium"
        elif adequate_a and strong_b and iv_proxy and not objective_c:
            label = "uncertain"
            confidence = "low"
        elif a_quality == "absent" and b_quality in {"absent", "weak"}:
            label = "clear_no"
            confidence = "high"
        elif a_quality in {"absent", "weak"} and dominant_alt and not strong_b:
            label = "clear_no" if a_quality == "absent" else "likely_no"
            confidence = "high" if label == "clear_no" else "medium"
        elif not adequate_a or not adequate_b:
            label = "likely_no" if dominant_alt or not any_c else "uncertain"
            confidence = "medium" if label == "likely_no" else "low"
        elif late_hf_evidence or late_b_evidence:
            label = "uncertain"
            confidence = "low"
        elif row["c_support_type"] == "treatment_proxy_only_C":
            label = "uncertain"
            confidence = "low"
        else:
            label = "uncertain"
            confidence = "low"

        algorithm_positive = row["algorithmic_label_v1"] == "algorithmic_rule_supported"
        ai_positive = label in {"clear_yes", "likely_yes"}
        discordant = algorithm_positive != ai_positive and label != "uncertain"
        existing = physician.get(visit_id, {})
        existing_label = existing.get("reviewer_dhf_label", "")
        domain_conflict = bool(
            existing_label == "DHF_no"
            and existing.get("reviewer_A_domain") == "yes"
            and existing.get("reviewer_B_domain") == "yes"
            and existing.get("reviewer_C_domain") == "yes"
        ) or bool(
            existing_label == "DHF_yes"
            and existing.get("reviewer_A_domain") == "no"
        )
        physician_ai_polarity_conflict = bool(
            existing_label == "DHF_yes" and label in {"clear_no", "likely_no"}
        ) or bool(
            existing_label == "DHF_no" and label in {"clear_yes", "likely_yes"}
        )

        if domain_conflict or physician_ai_polarity_conflict or existing_label == "indeterminate":
            review_priority = "adjudication_needed"
            selection_probability = 1.0
            selection_reason = "既有人工标签与分域证据/AI时间对齐预审冲突，需二次裁决"
        elif existing_label:
            review_priority = "completed_existing_review"
            selection_probability = 1.0
            selection_reason = "已完成人工审核"
        elif row["sample_stratum"] == "algorithmic_unknown":
            review_priority = "review_now"
            selection_probability = 1.0
            selection_reason = "未知层前30例已有20%人工阳性，剩余病例不得由AI直接排除"
        elif label == "uncertain" or t0_issue or discordant or (strong_negative_np and adequate_a):
            review_priority = "review_now"
            selection_probability = 1.0
            selection_reason = "疑难、规则冲突或算法与AI预审不一致"
        elif label == "clear_no" and deterministic_qc(visit_id, QC_RATE_CLEAR_NO):
            review_priority = "qc_sample"
            selection_probability = QC_RATE_CLEAR_NO
            selection_reason = "明确阴性层15%确定性随机质控"
        elif label == "clear_yes" and deterministic_qc(visit_id, QC_RATE_CLEAR_YES):
            review_priority = "qc_sample"
            selection_probability = QC_RATE_CLEAR_YES
            selection_reason = "明确阳性层20%确定性随机质控"
        elif label in {"likely_no", "likely_yes"} and deterministic_qc(visit_id, QC_RATE_LIKELY):
            review_priority = "qc_sample"
            selection_probability = QC_RATE_LIKELY
            selection_reason = "较可能阴性/阳性层15%确定性随机质控"
        else:
            review_priority = "defer_after_ai_triage"
            selection_probability = 0.0
            selection_reason = "当前校准轮暂缓；正式性能估计前须采用全审或已登记两阶段抽样"

        if review_priority == "adjudication_needed":
            review_tier = "T1_existing_label_adjudication"
        elif review_priority == "review_now" and algorithm_positive:
            review_tier = "T2_main_positive_calibration"
        elif review_priority == "review_now" and row["sample_stratum"] == "algorithmic_unknown":
            review_tier = "T3_unknown_recall_check"
        elif review_priority == "review_now":
            review_tier = "T4_boundary_or_negative_check"
        elif review_priority == "qc_sample":
            review_tier = "T5_random_qc"
        elif review_priority == "completed_existing_review":
            review_tier = "completed"
        else:
            review_tier = "deferred"

        reason_parts = a_reason + b_reason + [echo_reason]
        if objective_c:
            reason_parts.append("存在客观C域支持")
        elif iv_proxy:
            reason_parts.append("仅有静脉袢利尿医嘱代理支持")
        else:
            reason_parts.append("未见C域支持")
        if dominant_alt:
            reason_parts.append("替代诊断：" + "、".join(alt_categories[:4]))
        if conflicts:
            reason_parts.append("冲突：" + "；".join(conflicts))

        results.append(
            {
                "sample_stratum": row["sample_stratum"],
                "patient_id": row["patient_id"],
                "visit_id": visit_id,
                "sex": row["sex"],
                "age": row["age"],
                "t0_time": row["t0_time"],
                "algorithmic_label_v1": row["algorithmic_label_v1"],
                "ai_pre_review_label": label,
                "ai_confidence": confidence,
                "ai_A_quality": a_quality,
                "ai_B_quality": b_quality,
                "ai_C_objective": "yes" if objective_c else "no",
                "ai_echo_quality": echo_quality,
                "min_extracted_ef": min_ef,
                "np_measured_t0m24_to_t12": "yes" if np_measured else "no",
                "strong_negative_np": "yes" if strong_negative_np else "no",
                "np_evidence": np_row.get("np_evidence", ""),
                "iv_loop_order_proxy": "yes" if iv_proxy else "no",
                "alternative_categories": "；".join(alt_categories),
                "late_evidence_flag": "yes" if late_hf_evidence or late_b_evidence else "no",
                "first_current_hf_note_time": "" if first_hf_time is None else first_hf_time.isoformat(sep=" "),
                "first_strong_B_note_time": "" if first_b_time is None else first_b_time.isoformat(sep=" "),
                "t0_correction_flag": "yes" if t0_issue else "no",
                "likely_false_positive_mechanism": "；".join(dict.fromkeys(mechanisms)),
                "ai_reason": "；".join(dict.fromkeys(reason_parts)),
                "algorithm_ai_discordant": "yes" if discordant else "no",
                "human_review_priority": review_priority,
                "human_review_tier": review_tier,
                "human_selection_probability": f"{selection_probability:.2f}",
                "human_selection_reason": selection_reason,
                "existing_physician_label": existing_label,
                "existing_physician_A": existing.get("reviewer_A_domain", ""),
                "existing_physician_B": existing.get("reviewer_B_domain", ""),
                "existing_physician_C": existing.get("reviewer_C_domain", ""),
                "existing_physician_comments": existing.get("reviewer_comments", ""),
                "a_evidence_excerpt": row.get("a_evidence_excerpt", ""),
                "b_evidence_excerpt": row.get("b_evidence_excerpt", ""),
                "echo_evidence_excerpt": " || ".join(
                    f"{item[0].isoformat(sep=' ')}|{item[1]}|{item[2][:500]}" for item in exam_entries[:4]
                ),
                "note_evidence_excerpt": " || ".join(
                    f"{item[0].isoformat(sep=' ')}|{item[1]}|{item[2][:500]}" for item in note_entries[:6]
                ),
                "late_note_evidence_excerpt": " || ".join(
                    f"{item[0].isoformat(sep=' ')}|{item[1]}|{item[2][:500]}" for item in late_note_entries[:4]
                ),
                "reviewer_dhf_label": existing_label,
                "reviewer_A_domain": existing.get("reviewer_A_domain", ""),
                "reviewer_B_domain": existing.get("reviewer_B_domain", ""),
                "reviewer_C_domain": existing.get("reviewer_C_domain", ""),
                "reviewer_evidence_sufficient": existing.get("reviewer_evidence_sufficient", ""),
                "reviewer_comments": existing.get("reviewer_comments", ""),
                "second_reviewer_label": existing.get("second_reviewer_label", ""),
                "adjudicated_label": existing.get("adjudicated_label", ""),
            }
        )

    with OUTPUT_ALL.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    physician_subset = [
        row
        for row in results
        if row["human_review_priority"] in {"review_now", "qc_sample", "adjudication_needed"}
    ]
    physician_subset.sort(
        key=lambda row: (
            row["human_review_tier"],
            row["sample_stratum"],
            row["visit_id"],
        )
    )
    with OUTPUT_PHYSICIAN.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(physician_subset)

    label_counts = Counter(row["ai_pre_review_label"] for row in results)
    priority_counts = Counter(row["human_review_priority"] for row in results)
    tier_counts = Counter(row["human_review_tier"] for row in results)
    stratum_label_counts = defaultdict(Counter)
    for row in results:
        stratum_label_counts[row["sample_stratum"]][row["ai_pre_review_label"]] += 1
    existing_cross_tab = Counter(
        (row["existing_physician_label"], row["ai_pre_review_label"])
        for row in results
        if row["existing_physician_label"]
    )
    summary = {
        "version": "v1_20260928",
        "seed": SEED,
        "n_total": len(results),
        "n_existing_physician_review": sum(bool(row["existing_physician_label"]) for row in results),
        "n_new_physician_subset": len(physician_subset),
        "ai_label_counts": dict(label_counts),
        "human_review_priority_counts": dict(priority_counts),
        "human_review_tier_counts": dict(tier_counts),
        "strong_negative_np_count": sum(row["strong_negative_np"] == "yes" for row in results),
        "algorithm_ai_discordant_count": sum(row["algorithm_ai_discordant"] == "yes" for row in results),
        "stratum_by_ai_label": {key: dict(value) for key, value in stratum_label_counts.items()},
        "existing_physician_by_ai_label": {
            f"{key[0]}|{key[1]}": value for key, value in existing_cross_tab.items()
        },
        "calibration_warning": (
            "The first 30 algorithmic-unknown cases include 6 physician-positive cases, "
            "so AI-negative labels cannot be used as automatic exclusions."
        ),
        "caveat": "AI labels are pre-triage only and are not a clinical reference standard.",
    }
    OUTPUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    method = f"""# 290例DHF表型AI预审分诊方法说明 V1

日期：2026-09-28
状态：校准用途，非临床金标准

## 目的

先由机器读取290例的A/B/C证据、T0前24小时至T12的NT-proBNP、T0附近文书与心超/胸部检查，识别明显阴性、明显阳性、冲突和疑难病例；医生只优先审核疑难/冲突病例及明确层的随机质控样本。

## 关键纠正

- 290例是分层校准样本，不是773例算法阳性病例：120例来自算法支持层，170例来自未知、边界和阴性对照层。
- 原表按抽样层排序，前50例均为`algorithmic_unknown`，因此前30例的低阳性率不能代表773例主队列PPV。
- NT-proBNP<300 pg/mL作为强负证据，但不是不看其他证据的绝对机械金标准；低值而有明确肺水肿/急性心衰证据者进入冲突复核。
- 静脉袢利尿医嘱仅为代理，不能等同实际执行，也不能单独确诊DHF。

## AI标签

`clear_no`、`likely_no`、`uncertain`、`likely_yes`、`clear_yes`。这些标签仅用于排序和抽样，不替代医生裁决。

## 医生抽样

- 所有`uncertain`、算法与AI不一致、T0异常、低利钠肽冲突病例：抽样概率1.00；
- `clear_no`按{QC_RATE_CLEAR_NO:.0%}确定性随机质控；
- `clear_yes`按{QC_RATE_CLEAR_YES:.0%}确定性随机质控；
- `likely_no/likely_yes`按{QC_RATE_LIKELY:.0%}确定性随机质控；
- 未完成审核的`algorithmic_unknown`全部保留复核，因为前30例已有6例人工判为阳性，AI不得直接排除；
- 已完成的前30例保留，不要求重复填写；总标签与A/B/C冲突者进入裁决。

若后续用本次部分复核估计表型性能，必须按已登记抽样概率进行两阶段/逆概率加权并报告验证偏倚；若要形成最稳妥的临床金标准，则仍应完成预先抽出的全部290例人工审核。

随机种子：`{SEED}`。
"""
    OUTPUT_METHOD.write_text(method, encoding="utf-8")

    low_np_rows = load_csv(LOW_NP_TARGET_PATH)
    low_np_output = []
    for item in low_np_rows:
        combined = normalize_text(
            " || ".join([item.get("a_evidence_excerpt", ""), item.get("b_evidence_excerpt", "")])
        )
        if re.search(r"活动后胸闷气急半年|术后诊断", combined) and not re.search(
            r"突发|不能平卧|肺水肿|急性心", combined
        ):
            ai_label = "likely_no"
            ai_reason = "更符合慢性结构性心脏病/择期术后场景，缺少T0急性失代偿证据"
        elif re.search(r"Killip.*IV|心功能.?级.*Killip", combined, re.I) and RALES.search(combined):
            ai_label = "likely_yes"
            ai_reason = "急性冠脉事件伴Killip IV级/收缩功能下降及湿啰音，低NT-proBNP与其他强证据冲突"
        elif STRONG_B.search(combined) and re.search(r"重度|心功能IV级|心源性休克", combined):
            ai_label = "likely_yes"
            ai_reason = "存在不能平卧/明显充血并合并严重结构性心脏病或心源性休克，低值不能机械排除"
        else:
            ai_label = "uncertain"
            ai_reason = "NT-proBNP<300与其他A/B/C证据冲突，需人工核对事件时间、样本和诊断归因"
        out = dict(item)
        out["ai_pre_review_label"] = ai_label
        out["ai_reason"] = ai_reason
        out["review_priority"] = "review_now_low_np_conflict"
        low_np_output.append(out)
    if low_np_output:
        with LOW_NP_AI_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(low_np_output[0]))
            writer.writeheader()
            writer.writerows(low_np_output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
