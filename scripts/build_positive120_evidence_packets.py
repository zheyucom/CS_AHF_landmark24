#!/usr/bin/env python3
"""Build compact, time-aligned evidence packets for 120 algorithm-positive DHF cases."""

from __future__ import annotations

import csv
import glob
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


RUN_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")
SAMPLE_PATH = RUN_DIR / "clinical_review_sample_v1.csv"
AI_PATH = RUN_DIR / "clinical_review_290_ai_pretriage_v1.csv"
OUTPUT_CSV = RUN_DIR / "positive120_time_aligned_evidence_packet_v1.csv"
OUTPUT_JSON = RUN_DIR / "positive120_time_aligned_evidence_packet_v1.json"
OUTPUT_DIR = RUN_DIR / "positive120_review_batches_v1"

EARLY_START_HOURS = -24
EARLY_END_HOURS = 12
LATE_END_HOURS = 72

EXCLUDED_TITLE = re.compile(
    r"知情同意|谈话记录|APACHE|评分|评估单|风险告知|授权委托|健康教育|"
    r"手术安全核查|护理计划|跌倒|压疮|营养筛查|疼痛评估|VTE|血栓风险|"
    r"输血记录|麻醉记录|植入物|死亡讨论"
)
HIGH_VALUE_TITLE = re.compile(
    r"入ICU|转ICU|首次病程|入院记录|会诊结果|会诊意见|查房记录|抢救记录|"
    r"转科记录|入科记录|病房转|急诊记录|出院记录|死亡记录"
)
FOCUS = re.compile(
    r"急性.{0,4}心|心力衰竭|心功能不全|心衰|心源性|Killip|肺水肿|肺淤血|"
    r"肺充血|端坐呼吸|不能平卧|无法平卧|夜间阵发|粉红色泡沫痰|颈静脉|"
    r"胸闷|气急|气促|呼吸困难|湿[啰罗]音|水肿|胸腔积液|容量超负荷|"
    r"EF\s*[:：]?\s*\d+|射血分数|左室收缩|右心功能|舒张功能|肺动脉高压|"
    r"BNP|NT.?proBNP|利尿|呋塞米|托拉塞米|无创|正压通气|强心|扩血管|"
    r"肺炎|感染|ARDS|肺栓塞|误吸|肺不张|COPD|哮喘|肾功能不全|肾衰|"
    r"血液透析|低蛋白|肝硬化|心包积液|失血|消化道出血|创伤|术后|"
    r"目前诊断|入ICU诊断|入院诊断|初步诊断|修正诊断"
)
NEGATIVE = re.compile(
    r"否认.{0,30}(?:胸闷|气急|气促|呼吸困难|不能平卧)|"
    r"(?:双肺|两肺).{0,18}(?:清|未闻及|未及).{0,12}(?:湿[啰罗]音|干湿[啰罗]音)|"
    r"(?:双下肢|下肢).{0,12}(?:无|未见|未及).{0,8}水肿|"
    r"颈静脉.{0,12}(?:无|未见|未及).{0,8}(?:充盈|怒张)|"
    r"心功能不全.{0,8}(?:可能性小|不考虑|排除)|"
    r"心源性休克.{0,8}(?:可能性小|不考虑|排除)"
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def normalize(value: str) -> str:
    text = (value or "").replace("&nbsp;", " ").replace("&ensp;", " ")
    text = text.replace("&gt;", ">").replace("&lt;", "<")
    return re.sub(r"\s+", " ", text).strip()


def unique(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        key = re.sub(r"\s+", "", item)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def relevant_snippets(text: str, limit: int = 10, radius: int = 150) -> list[str]:
    candidates = []
    for pattern in (FOCUS, NEGATIVE):
        for match in pattern.finditer(text):
            left = max(0, match.start() - radius)
            right = min(len(text), match.end() + radius)
            snippet = normalize(text[left:right])
            if snippet:
                candidates.append((match.start(), snippet))
    candidates.sort(key=lambda item: item[0])
    return unique([item[1] for item in candidates])[:limit]


def parse_float(value: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value or "")
    return float(match.group()) if match else None


def main() -> None:
    sample_rows = [
        row
        for row in load_csv(SAMPLE_PATH)
        if row["sample_stratum"]
        in {"main_supported_objective_C", "main_supported_treatment_only_C"}
    ]
    assert len(sample_rows) == 120
    sample = {row["visit_id"]: row for row in sample_rows}
    ai = {row["visit_id"]: row for row in load_csv(AI_PATH)}

    early_notes: dict[str, list[dict[str, str]]] = defaultdict(list)
    late_notes: dict[str, list[dict[str, str]]] = defaultdict(list)
    title_counter = Counter()
    for path in glob.glob("DHF_SRR/*文书*/02_rdr_medrecord_list.csv"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
            for record in csv.DictReader(handle):
                visit_id = record.get("就诊号", "")
                if visit_id not in sample:
                    continue
                created = parse_dt(record.get("创建日期", ""))
                t0 = parse_dt(sample[visit_id]["t0_time"])
                title = normalize(record.get("文书名称", ""))
                if created is None or t0 is None or EXCLUDED_TITLE.search(title):
                    continue
                start = t0 + timedelta(hours=EARLY_START_HOURS)
                early_end = t0 + timedelta(hours=EARLY_END_HOURS)
                late_end = t0 + timedelta(hours=LATE_END_HOURS)
                if not (start <= created < late_end):
                    continue
                text = normalize(record.get("文本病历", ""))
                if not text:
                    continue
                snippets = relevant_snippets(text)
                if not snippets and not HIGH_VALUE_TITLE.search(title):
                    continue
                if not snippets:
                    snippets = [text[:1200]]
                item = {
                    "time": created.isoformat(sep=" "),
                    "title": title,
                    "snippets": " || ".join(snippets),
                }
                title_counter[title] += 1
                (early_notes if created < early_end else late_notes)[visit_id].append(item)

    labs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in glob.glob("DHF_SRR/*检验*/02_rdr_lab_test_data.csv"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
            for record in csv.DictReader(handle):
                visit_id = record.get("就诊号", "")
                if visit_id not in sample:
                    continue
                name = normalize(record.get("检验指标", ""))
                if not re.search(r"BNP|利钠|脑钠|肌钙蛋白|肌酐|尿素", name, re.I):
                    continue
                report_time = parse_dt(record.get("检验[报告]日期", ""))
                t0 = parse_dt(sample[visit_id]["t0_time"])
                if report_time is None or t0 is None:
                    continue
                if not (t0 + timedelta(hours=-24) <= report_time < t0 + timedelta(hours=12)):
                    continue
                labs[visit_id].append(
                    {
                        "time": report_time.isoformat(sep=" "),
                        "name": name,
                        "value": normalize(
                            record.get("检验结果值", "") or record.get("检验结果数值", "")
                        ),
                        "flag": normalize(record.get("异常标志", "")),
                    }
                )

    exams: dict[str, list[dict[str, str]]] = defaultdict(list)
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
                if not (t0 + timedelta(hours=-24) <= report_time < t0 + timedelta(hours=12)):
                    continue
                project = normalize(record.get("项目名称", ""))
                exam_type = normalize(record.get("检查类型", ""))
                conclusion = normalize(record.get("检查结论", ""))
                findings = normalize(record.get("检查所见", ""))
                whole = " ".join([project, exam_type, conclusion, findings])
                if not re.search(r"心脏|心动图|心超|胸部|胸片|肺|CT", whole, re.I):
                    continue
                exams[visit_id].append(
                    {
                        "time": report_time.isoformat(sep=" "),
                        "project": project or exam_type,
                        "conclusion": conclusion,
                        "findings": findings[:2200],
                    }
                )

    orders: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in glob.glob("DHF_SRR/*用药*/02_rdr_orders.csv"):
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as handle:
            for record in csv.DictReader(handle):
                visit_id = record.get("就诊号", "")
                if visit_id not in sample:
                    continue
                drug = normalize(record.get("药品名称", ""))
                if not re.search(r"呋塞米|托拉塞米|布美他尼|依他尼酸", drug):
                    continue
                order_time = parse_dt(record.get("开嘱时间", ""))
                t0 = parse_dt(sample[visit_id]["t0_time"])
                if order_time is None or t0 is None:
                    continue
                if not (t0 + timedelta(hours=-24) <= order_time < t0 + timedelta(hours=12)):
                    continue
                orders[visit_id].append(
                    {
                        "time": order_time.isoformat(sep=" "),
                        "drug": drug,
                        "dose": normalize(record.get("剂量", "")),
                        "unit": normalize(record.get("剂量单位", "")),
                        "route": normalize(record.get("给药途径", "")),
                        "status": normalize(record.get("医嘱状态", "")),
                    }
                )

    packets = []
    for row in sample_rows:
        visit_id = row["visit_id"]
        early = sorted(early_notes.get(visit_id, []), key=lambda item: item["time"])
        late = sorted(late_notes.get(visit_id, []), key=lambda item: item["time"])
        lab_values = sorted(labs.get(visit_id, []), key=lambda item: (item["time"], item["name"]))
        exam_values = sorted(exams.get(visit_id, []), key=lambda item: item["time"])
        order_values = sorted(orders.get(visit_id, []), key=lambda item: item["time"])
        ai_row = ai.get(visit_id, {})
        packet = {
            "case_no": len(packets) + 1,
            "sample_stratum": row["sample_stratum"],
            "patient_id": row["patient_id"],
            "visit_id": visit_id,
            "sex": row["sex"],
            "age": row["age"],
            "t0_time": row["t0_time"],
            "c_support_type": row["c_support_type"],
            "algorithm_A": row["a_hf_anchor_flag"],
            "algorithm_B": row["b_decompensation_flag"],
            "algorithm_NP": row["c_ntprobnp_rule_in_flag"],
            "algorithm_echo": row["c_echo_abnormal_flag"],
            "algorithm_IV_loop": row["c_iv_loop_order_proxy_flag"],
            "first_pass_ai_label": ai_row.get("ai_pre_review_label", ""),
            "first_pass_ai_reason": ai_row.get("ai_reason", ""),
            "algorithm_a_excerpt": row.get("a_evidence_excerpt", ""),
            "algorithm_b_excerpt": row.get("b_evidence_excerpt", ""),
            "early_notes_json": json.dumps(early, ensure_ascii=False),
            "labs_json": json.dumps(lab_values, ensure_ascii=False),
            "exams_json": json.dumps(exam_values, ensure_ascii=False),
            "orders_json": json.dumps(order_values, ensure_ascii=False),
            "late_notes_json": json.dumps(late, ensure_ascii=False),
            "early_note_count": str(len(early)),
            "late_note_count": str(len(late)),
            "lab_count": str(len(lab_values)),
            "exam_count": str(len(exam_values)),
            "loop_order_count": str(len(order_values)),
        }
        packets.append(packet)

    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(packets[0]))
        writer.writeheader()
        writer.writerows(packets)
    OUTPUT_JSON.write_text(json.dumps(packets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for batch_start in range(0, len(packets), 10):
        batch = packets[batch_start : batch_start + 10]
        lines = [
            f"# 120例算法阳性深度复核：病例{batch_start + 1:03d}–{batch_start + len(batch):03d}",
            "",
            "时间窗：T0前24小时至T12；T12–T72只作时间错位审计，不用于入组。",
            "",
        ]
        for packet in batch:
            lines.extend(
                [
                    f"## {packet['case_no']:03d}｜{packet['visit_id']}｜{packet['sample_stratum']}",
                    "",
                    f"- 年龄/性别：{packet['age']}/{packet['sex']}；T0：{packet['t0_time']}",
                    f"- 算法：A={packet['algorithm_A']} B={packet['algorithm_B']} NP={packet['algorithm_NP']} Echo={packet['algorithm_echo']} IV-loop={packet['algorithm_IV_loop']}",
                    f"- 第一轮AI：{packet['first_pass_ai_label']}｜{packet['first_pass_ai_reason']}",
                    f"- A原摘要：{packet['algorithm_a_excerpt']}",
                    f"- B原摘要：{packet['algorithm_b_excerpt']}",
                    "- 同窗实验室：" + packet["labs_json"],
                    "- 同窗检查：" + packet["exams_json"],
                    "- 同窗袢利尿医嘱：" + packet["orders_json"],
                    "- T12前关键文书：" + packet["early_notes_json"],
                    "- T12后至T72关键文书（仅审计）：" + packet["late_notes_json"],
                    "",
                    "裁决：`pending`",
                    "",
                ]
            )
        path = OUTPUT_DIR / f"cases_{batch_start + 1:03d}_{batch_start + len(batch):03d}.md"
        path.write_text("\n".join(lines), encoding="utf-8")

    qc = {
        "n": len(packets),
        "strata": dict(Counter(row["sample_stratum"] for row in packets)),
        "zero_early_note": sum(int(row["early_note_count"]) == 0 for row in packets),
        "zero_exam": sum(int(row["exam_count"]) == 0 for row in packets),
        "zero_lab": sum(int(row["lab_count"]) == 0 for row in packets),
        "zero_loop_order": sum(int(row["loop_order_count"]) == 0 for row in packets),
        "top_titles": title_counter.most_common(30),
    }
    (OUTPUT_DIR / "qc.json").write_text(
        json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(qc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
