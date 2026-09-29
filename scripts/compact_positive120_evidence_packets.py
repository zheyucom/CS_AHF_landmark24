#!/usr/bin/env python3
"""Compact the 120-case evidence packets into review-sized, category-labelled summaries."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


RUN_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")
INPUT = RUN_DIR / "positive120_time_aligned_evidence_packet_v1.json"
OUTPUT = RUN_DIR / "positive120_compact_evidence_v1.csv"
BATCH_DIR = RUN_DIR / "positive120_compact_review_batches_v1"

PATTERNS = {
    "acute_hf": re.compile(
        r"急性(?:左|右|全)?心(?:力)?衰(?:竭)?|急性心功能不全|失代偿.{0,4}心衰|"
        r"心源性肺水肿|急性肺水肿|Killip\s*(?:III|IV|Ⅲ|Ⅳ|3|4)"
    ),
    "current_hf_dx": re.compile(
        r"(?:目前诊断|入ICU诊断|入院诊断|初步诊断|修正诊断|临床诊断)"
        r".{0,100}(?:心力衰竭|心功能不全|心衰|心源性休克)"
    ),
    "strong_congestion": re.compile(
        r"肺水肿|肺淤血|肺充血|端坐呼吸|不能平卧|无法平卧|夜间阵发|"
        r"粉红色泡沫痰|颈静脉.{0,10}(?:怒张|充盈)|容量超负荷"
    ),
    "weak_congestion": re.compile(r"湿[啰罗]音|胸闷气急|气促|呼吸困难|双下肢.{0,8}水肿|胸腔积液"),
    "hf_treatment": re.compile(r"利尿|呋塞米|托拉塞米|强心|扩血管|无创(?:呼吸机|通气)|正压通气"),
    "alternative": re.compile(
        r"重症肺炎|肺部感染|吸入性肺炎|ARDS|急性呼吸窘迫|肺栓塞|肺不张|"
        r"COPD|慢阻肺|哮喘|脓毒症|感染性休克|失血性休克|消化道出血|"
        r"脑出血|蛛网膜下腔出血|脑梗死|创伤|术后|低蛋白血症|肝硬化|"
        r"心包填塞|大量心包积液|肾功能衰竭|尿毒症|CKD\s*[45]"
    ),
    "negative_or_uncertain": re.compile(
        r"否认.{0,25}(?:胸闷|气急|气促|呼吸困难|不能平卧)|"
        r"(?:双肺|两肺).{0,15}(?:清|未闻及|未及).{0,10}(?:湿[啰罗]音|干湿[啰罗]音)|"
        r"(?:双下肢|下肢).{0,10}(?:无|未见|未及).{0,6}水肿|"
        r"心功能不全[？?]|心力衰竭[？?]|(?:不考虑|可能性小|待排|可疑).{0,12}(?:心衰|心功能|心源性)"
    ),
}

BLOCKERS = re.compile(r"风险|可能出现|可出现|并发症|告知|APACHE|评分标准")


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def add_unique(target: list[str], value: str, limit: int) -> None:
    key = re.sub(r"\s+", "", value)
    if not key:
        return
    for existing in target:
        if key == re.sub(r"\s+", "", existing):
            return
        if len(key) > 80 and key[:80] in re.sub(r"\s+", "", existing):
            return
    if len(target) < limit:
        target.append(value)


def clipped(text: str, pattern: re.Pattern[str], radius: int = 105) -> list[str]:
    output = []
    for match in pattern.finditer(text):
        left = max(0, match.start() - radius)
        right = min(len(text), match.end() + radius)
        item = norm(text[left:right])
        if item:
            add_unique(output, item, 8)
    return output


def select_labs(values: list[dict[str, str]]) -> str:
    seen = set()
    output = []
    for item in values:
        key = (item["time"], item["name"], item["value"])
        if key in seen:
            continue
        seen.add(key)
        output.append(f"{item['time']} {item['name']}={item['value']} {item['flag']}")
    return " || ".join(output[:18])


def select_exams(values: list[dict[str, str]]) -> tuple[str, str]:
    echo, chest = [], []
    for item in values:
        text = norm(" ".join([item["project"], item["conclusion"], item["findings"]]))
        compact = f"{item['time']} {item['project']}：{norm(item['conclusion'])}；{norm(item['findings'])[:700]}"
        if re.search(r"心动图|心脏超声|心超|左心功能|室壁运动", text, re.I):
            add_unique(echo, compact, 3)
        elif re.search(r"胸部|胸片|肺|CT", text, re.I):
            add_unique(chest, compact, 3)
    return " || ".join(echo), " || ".join(chest)


def select_orders(values: list[dict[str, str]]) -> str:
    seen = set()
    output = []
    for item in values:
        key = (item["time"], item["drug"], item["dose"], item["unit"], item["route"])
        if key in seen:
            continue
        seen.add(key)
        output.append(
            f"{item['time']} {item['drug']} {item['dose']}{item['unit']} {item['route']} {item['status']}"
        )
    return " || ".join(output[:12])


def main() -> None:
    packets = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = []
    for packet in packets:
        categories = {name: [] for name in PATTERNS}
        early_notes = json.loads(packet["early_notes_json"])
        late_notes = json.loads(packet["late_notes_json"])
        for note in early_notes:
            title = note["title"]
            for raw in note["snippets"].split(" || "):
                text = norm(raw)
                for name, pattern in PATTERNS.items():
                    for snippet in clipped(text, pattern):
                        if name in {"acute_hf", "current_hf_dx"} and BLOCKERS.search(snippet):
                            continue
                        add_unique(categories[name], f"{note['time']}|{title}|{snippet}", 5)
        late_signal = []
        for note in late_notes:
            text = norm(note["snippets"])
            if PATTERNS["acute_hf"].search(text) or PATTERNS["current_hf_dx"].search(text):
                for snippet in clipped(text, re.compile(r"急性.{0,4}心|心力衰竭|心功能不全|心衰|心源性")):
                    add_unique(late_signal, f"{note['time']}|{note['title']}|{snippet}", 4)
        echo, chest = select_exams(json.loads(packet["exams_json"]))
        row = {
            **{key: packet[key] for key in [
                "case_no", "sample_stratum", "patient_id", "visit_id", "sex", "age", "t0_time",
                "c_support_type", "algorithm_A", "algorithm_B", "algorithm_NP", "algorithm_echo",
                "algorithm_IV_loop", "first_pass_ai_label",
            ]},
            "acute_hf_evidence": " || ".join(categories["acute_hf"]),
            "current_hf_dx_evidence": " || ".join(categories["current_hf_dx"]),
            "strong_congestion_evidence": " || ".join(categories["strong_congestion"]),
            "weak_congestion_evidence": " || ".join(categories["weak_congestion"]),
            "hf_treatment_text": " || ".join(categories["hf_treatment"]),
            "alternative_evidence": " || ".join(categories["alternative"]),
            "negative_or_uncertain_evidence": " || ".join(categories["negative_or_uncertain"]),
            "np_renal_troponin_labs": select_labs(json.loads(packet["labs_json"])),
            "echo_evidence": echo,
            "chest_imaging_evidence": chest,
            "iv_loop_orders": select_orders(json.loads(packet["orders_json"])),
            "late_hf_signal_after_T12": " || ".join(late_signal),
            "algorithm_a_excerpt": norm(packet["algorithm_a_excerpt"]),
            "algorithm_b_excerpt": norm(packet["algorithm_b_excerpt"]),
        }
        rows.append(row)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(rows), 10):
        batch = rows[start : start + 10]
        lines = [f"# 深度复核紧凑证据 {start + 1:03d}–{start + len(batch):03d}", ""]
        for row in batch:
            lines.extend(
                [
                    f"## {int(row['case_no']):03d} {row['visit_id']} [{row['sample_stratum']}]",
                    f"T0={row['t0_time']} age={row['age']} sex={row['sex']} C={row['c_support_type']} alg(NP/Echo/IV)={row['algorithm_NP']}/{row['algorithm_echo']}/{row['algorithm_IV_loop']}",
                    f"A-急性：{row['acute_hf_evidence'] or '无'}",
                    f"A-当前诊断：{row['current_hf_dx_evidence'] or '无'}",
                    f"B-强充血：{row['strong_congestion_evidence'] or '无'}",
                    f"B-弱证据：{row['weak_congestion_evidence'] or '无'}",
                    f"反证/不确定：{row['negative_or_uncertain_evidence'] or '无'}",
                    f"替代解释：{row['alternative_evidence'] or '无'}",
                    f"实验室：{row['np_renal_troponin_labs'] or '无'}",
                    f"心超：{row['echo_evidence'] or '无'}",
                    f"胸部影像：{row['chest_imaging_evidence'] or '无'}",
                    f"同窗IV袢利尿：{row['iv_loop_orders'] or '无'}",
                    f"治疗文本：{row['hf_treatment_text'] or '无'}",
                    f"T12后HF信号：{row['late_hf_signal_after_T12'] or '无'}",
                    f"旧A摘要：{row['algorithm_a_excerpt'] or '无'}",
                    f"旧B摘要：{row['algorithm_b_excerpt'] or '无'}",
                    "裁决：pending",
                    "",
                ]
            )
        (BATCH_DIR / f"cases_{start + 1:03d}_{start + len(batch):03d}.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )
    qc = {
        "n": len(rows),
        "category_nonempty": {
            key: sum(bool(row[key]) for row in rows)
            for key in [
                "acute_hf_evidence", "current_hf_dx_evidence", "strong_congestion_evidence",
                "negative_or_uncertain_evidence", "alternative_evidence", "echo_evidence",
                "chest_imaging_evidence", "iv_loop_orders", "late_hf_signal_after_T12",
            ]
        },
        "strata": dict(Counter(row["sample_stratum"] for row in rows)),
    }
    (BATCH_DIR / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
