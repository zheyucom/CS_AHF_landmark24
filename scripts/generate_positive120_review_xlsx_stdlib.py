#!/usr/bin/env python3
"""Generate the positive-120 DHF second-pass review workbook using stdlib only."""

from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from generate_ai_triage_xlsx_stdlib import (
    column_name,
    content_types_xml,
    root_rels_xml,
    sheet_xml,
    styles_xml,
    workbook_rels_xml,
    workbook_xml,
)


RUN_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")
ALL_PATH = RUN_DIR / "positive120_second_pass_ai_review_v1.csv"
SUBSET_PATH = RUN_DIR / "positive120_physician_adjudication_subset_v1.csv"
SUMMARY_PATH = RUN_DIR / "positive120_second_pass_summary_v1.json"
OUTPUT = RUN_DIR / "positive120_AI_deep_review_and_physician_adjudication_20260929.xlsx"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


HEADERS = {
    "case_no": "序号",
    "sample_stratum": "抽样层",
    "patient_id": "病历号",
    "visit_id": "visit_id",
    "sex": "性别",
    "age": "年龄",
    "t0_time": "T0时间",
    "c_support_type": "C层类型",
    "algorithm_NP": "算法NP",
    "algorithm_echo": "算法心超",
    "algorithm_IV_loop": "算法静脉袢利尿",
    "ai_second_pass_label": "AI二轮预审",
    "ai_confidence": "AI置信度",
    "review_A_current_hf": "A域_当前心衰",
    "review_B_acute_decompensation": "B域_急性失代偿",
    "review_C_support": "C域_支持证据",
    "time_aligned_before_T12": "T12前时间对齐",
    "dominant_alternative": "主要替代解释",
    "false_positive_or_uncertainty_mechanism": "误纳/不确定机制",
    "ai_reason": "AI判断理由",
    "decisive_A_excerpt": "A域关键原文",
    "decisive_B_excerpt": "B域关键原文",
    "decisive_C_excerpt": "C域关键原文",
    "counter_evidence_excerpt": "反证/替代证据",
    "late_HF_signal_after_T12": "T12后HF信号",
    "physician_adjudication_needed": "需医生裁决",
    "physician_selection_reason": "入选医生审核原因",
    "physician_dhf_label": "医生DHF总标签",
    "physician_A_domain": "医生A域",
    "physician_B_domain": "医生B域",
    "physician_C_domain": "医生C域",
    "physician_t0_status": "医生T0核对",
    "physician_comments": "医生裁决备注",
}


ALL_FIELDS = list(HEADERS)
REVIEW_FIELDS = [
    "case_no", "physician_selection_reason", "patient_id", "visit_id", "sex", "age",
    "t0_time", "sample_stratum", "c_support_type", "ai_second_pass_label", "ai_confidence",
    "review_A_current_hf", "review_B_acute_decompensation", "review_C_support",
    "dominant_alternative", "false_positive_or_uncertainty_mechanism", "ai_reason",
    "decisive_A_excerpt", "decisive_B_excerpt", "decisive_C_excerpt",
    "counter_evidence_excerpt", "late_HF_signal_after_T12", "physician_dhf_label",
    "physician_A_domain", "physician_B_domain", "physician_C_domain",
    "physician_t0_status", "physician_comments",
]


def make_sheet(rows: list[dict[str, str]], fields: list[str]) -> list[list[str]]:
    return [[HEADERS[field] for field in fields]] + [
        [row.get(field, "") for field in fields] for row in rows
    ]


def main() -> None:
    all_rows = load_csv(ALL_PATH)
    subset_rows = load_csv(SUBSET_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    assert len(all_rows) == 120

    all_sheet = make_sheet(all_rows, ALL_FIELDS)
    all_widths = [
        8, 28, 12, 18, 7, 8, 20, 25, 10, 10, 14, 18, 12, 20, 20, 22, 22,
        35, 48, 65, 55, 55, 55, 55, 14, 14, 35, 18, 14, 14, 14, 16, 60,
    ]

    review_sheet = make_sheet(subset_rows, REVIEW_FIELDS)
    review_widths = [
        8, 32, 12, 18, 7, 8, 20, 28, 25, 18, 12, 20, 20, 22, 35, 48, 65,
        55, 55, 55, 55, 14, 20, 14, 14, 14, 16, 65,
    ]
    col = {field: column_name(index + 1) for index, field in enumerate(REVIEW_FIELDS)}
    n_review = len(review_sheet)
    validations = [
        (f'{col["physician_dhf_label"]}2:{col["physician_dhf_label"]}{n_review}', "DHF_yes,DHF_no,indeterminate"),
        (f'{col["physician_A_domain"]}2:{col["physician_A_domain"]}{n_review}', "yes,no,unknown"),
        (f'{col["physician_B_domain"]}2:{col["physician_B_domain"]}{n_review}', "yes,no,unknown"),
        (f'{col["physician_C_domain"]}2:{col["physician_C_domain"]}{n_review}', "yes,no,unknown"),
        (f'{col["physician_t0_status"]}2:{col["physician_t0_status"]}{n_review}', "correct,incorrect,uncertain"),
    ]

    strata_rows = [["分层", "n", "明确支持", "不支持", "疑难", "初步下界", "初步上界", "说明"]]
    labels = {
        "main_supported_objective_C": "客观C层",
        "main_supported_treatment_only_C": "治疗代理-only层",
    }
    for key, display in labels.items():
        item = summary["by_stratum"][key]
        strata_rows.append([
            display, item["n"], item.get("supported", 0), item.get("not_supported", 0),
            item.get("indeterminate", 0), f'{item["preliminary_supported_lower_bound"]:.1%}',
            f'{item["preliminary_supported_upper_bound"]:.1%}', "非正式PPV，须医生金标准",
        ])
    total = Counter(row["ai_second_pass_label"] for row in all_rows)
    strata_rows.append([
        "合计", 120, total["supported"], total["not_supported"], total["indeterminate"],
        f'{total["supported"]/120:.1%}',
        f'{(total["supported"] + total["indeterminate"])/120:.1%}', "仅用于审核分诊",
    ])

    mechanism_counts: Counter[str] = Counter()
    for row in all_rows:
        for item in row["false_positive_or_uncertainty_mechanism"].split("；"):
            if item:
                mechanism_counts[item] += 1
    mechanism_rows = [["误纳/不确定机制", "例数", "解释"]]
    for mechanism, count in mechanism_counts.most_common():
        mechanism_rows.append([mechanism, count, "一例可有多个机制"])

    guide_rows = [
        ["主题", "执行口径"],
        ["先填哪个表", "只填写“医生裁决病例”；“120例AI深度审核”用于追溯，不要求逐行重审。"],
        ["AI标签性质", "supported/not_supported/indeterminate仅为AI预审，不能作为临床金标准或正式PPV。"],
        ["A域", "确认本次episode在T12前存在当前心衰；慢性史、NYHA分级、风险告知或问号诊断不能单独满足。"],
        ["B域", "确认当前急性失代偿：优先肺水肿、端坐呼吸、不能平卧、粉红泡沫痰、明确容量超负荷或低灌注。"],
        ["C域", "仅为支持证据。NP需结合肾衰/房颤/年龄；心超需与本次事件相关；静脉袢利尿医嘱仍需eMAR确认执行。"],
        ["计划手术/术后ICU", "慢性心衰患者计划心脏手术或PCI后常规入ICU，不等同于T0时DHF。"],
        ["时间轴", "只用[T0-24h,T0+12h)确认入组；T12后新发心衰不能倒灌入T0/T12风险集。"],
        ["医生填写", "填写DHF总标签、A/B/C、T0是否正确；疑难病例在备注写明主要冲突或需要补看的原病历。"],
        ["后续统计", "完成裁决后分层计算PPV及95%CI；再按抽样设计加权。另需审核阴性/边界样本估计敏感度和特异度。"],
    ]

    sheets = [
        ("120例AI深度审核", sheet_xml(all_sheet, all_widths, wrap_body=True)),
        ("医生裁决病例", sheet_xml(review_sheet, review_widths, wrap_body=True, data_validations=validations)),
        ("分层初步区间", sheet_xml(strata_rows, [28, 10, 14, 14, 14, 16, 16, 40], wrap_body=True)),
        ("误纳机制", sheet_xml(mechanism_rows, [65, 12, 35], wrap_body=True)),
        ("审核口径", sheet_xml(guide_rows, [28, 115], wrap_body=True)),
    ]
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("xl/workbook.xml", workbook_xml([name for name, _ in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", styles_xml())
        for index, (_, content) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", content)
        archive.writestr(
            "docProps/core.xml",
            f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>DHF positive-120 second-pass review</dc:title><dc:creator>Codex</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created></cp:coreProperties>''',
        )
        archive.writestr(
            "docProps/app.xml",
            '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Python stdlib</Application></Properties>''',
        )
    print(OUTPUT)
    print(f"all={len(all_rows)} physician_subset={len(subset_rows)}")


if __name__ == "__main__":
    main()
