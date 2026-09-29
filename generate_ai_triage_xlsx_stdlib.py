#!/usr/bin/env python3
"""Generate the AI-triaged DHF review workbook using only Python stdlib."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path


RUN_DIR = Path("project_control/runs/20260924_internal_stage1_g3_phenotype")
ALL_PATH = RUN_DIR / "clinical_review_290_ai_pretriage_v1.csv"
SUBSET_PATH = RUN_DIR / "clinical_review_physician_subset_ai_triaged_v1.csv"
SUMMARY_PATH = RUN_DIR / "clinical_review_290_ai_pretriage_summary_v1.json"
LOW_NP_PATH = RUN_DIR / "low_ntprobnp_under300_ai_review_v1.csv"
OUTPUT = RUN_DIR / "clinical_review_AI_triage_and_physician_subset_20260928.xlsx"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_xml(value: object) -> str:
    text = "" if value is None else str(value)
    text = text[:32700]
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return escape(text, quote=False)


def column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell_xml(row: int, col: int, value: object, style: int = 0) -> str:
    ref = f"{column_name(col)}{row}"
    return (
        f'<c r="{ref}" t="inlineStr" s="{style}">'
        f'<is><t xml:space="preserve">{clean_xml(value)}</t></is></c>'
    )


def sheet_xml(
    rows: list[list[object]],
    widths: list[float],
    wrap_body: bool = False,
    data_validations: list[tuple[str, str]] | None = None,
) -> str:
    max_col = max((len(row) for row in rows), default=1)
    max_row = max(len(rows), 1)
    cols = "".join(
        f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>'
        for idx, width in enumerate(widths, start=1)
    )
    row_parts = []
    for row_idx, values in enumerate(rows, start=1):
        style = 1 if row_idx == 1 else (2 if wrap_body else 0)
        height = 28 if row_idx == 1 else (54 if wrap_body else 24)
        cells = "".join(
            cell_xml(row_idx, col_idx, value, style)
            for col_idx, value in enumerate(values, start=1)
        )
        row_parts.append(f'<row r="{row_idx}" ht="{height}" customHeight="1">{cells}</row>')
    validations_xml = ""
    if data_validations:
        parts = []
        for sqref, formula in data_validations:
            parts.append(
                '<dataValidation type="list" allowBlank="1" showErrorMessage="1" '
                f'sqref="{sqref}"><formula1>"{clean_xml(formula)}"</formula1></dataValidation>'
            )
        validations_xml = f'<dataValidations count="{len(parts)}">{"".join(parts)}</dataValidations>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>{cols}</cols>
  <sheetData>{"".join(row_parts)}</sheetData>
  <autoFilter ref="A1:{column_name(max_col)}{max_row}"/>
  {validations_xml}
</worksheet>'''


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{clean_xml(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, name in enumerate(sheet_names, start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="14000"/></bookViews>
  <sheets>{sheets}</sheets>
</workbook>'''


def styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="10"/><name val="Arial"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD9E2F3"/></left><right style="thin"><color rgb="FFD9E2F3"/></right><top style="thin"><color rgb="FFD9E2F3"/></top><bottom style="thin"><color rgb="FFD9E2F3"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="top" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def content_types_xml(sheet_count: int) -> str:
    sheet_parts = "".join(
        f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for idx in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  {sheet_parts}
</Types>'''


def root_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def workbook_rels_xml(sheet_count: int) -> str:
    items = "".join(
        f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        for idx in range(1, sheet_count + 1)
    )
    items += (
        f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{items}</Relationships>'''


def main() -> None:
    all_rows = load_csv(ALL_PATH)
    subset_rows = load_csv(SUBSET_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    low_np_rows = load_csv(LOW_NP_PATH)

    all_fields = [
        "sample_stratum", "patient_id", "visit_id", "sex", "age", "t0_time",
        "algorithmic_label_v1", "ai_pre_review_label", "ai_confidence", "ai_A_quality",
        "ai_B_quality", "ai_C_objective", "ai_echo_quality", "min_extracted_ef",
        "strong_negative_np", "np_evidence", "iv_loop_order_proxy", "alternative_categories",
        "late_evidence_flag", "t0_correction_flag", "likely_false_positive_mechanism",
        "ai_reason", "algorithm_ai_discordant", "human_review_priority",
        "human_review_tier", "human_selection_probability", "human_selection_reason", "existing_physician_label",
        "existing_physician_comments",
    ]
    all_sheet = [all_fields] + [[row.get(field, "") for field in all_fields] for row in all_rows]
    all_widths = [25, 12, 18, 7, 8, 20, 27, 18, 12, 13, 13, 15, 16, 12, 16, 38, 17, 34, 15, 15, 42, 55, 17, 25, 30, 16, 45, 18, 55]

    review_fields = [
        "human_review_tier", "human_review_priority", "sample_stratum", "patient_id", "visit_id", "sex", "age", "t0_time",
        "algorithmic_label_v1", "ai_pre_review_label", "ai_confidence", "ai_A_quality", "ai_B_quality",
        "ai_C_objective", "strong_negative_np", "np_evidence", "iv_loop_order_proxy",
        "alternative_categories", "late_evidence_flag", "t0_correction_flag",
        "likely_false_positive_mechanism", "ai_reason", "a_evidence_excerpt", "b_evidence_excerpt",
        "echo_evidence_excerpt", "note_evidence_excerpt", "late_note_evidence_excerpt",
        "reviewer_dhf_label", "reviewer_A_domain", "reviewer_B_domain", "reviewer_C_domain",
        "reviewer_evidence_sufficient", "reviewer_t0_status", "corrected_t0_time",
        "dhf_onset_relative_to_t0", "first_dhf_onset_time", "reviewer_comments",
        "second_reviewer_label", "adjudicated_label",
    ]
    review_sheet = [review_fields]
    for row in subset_rows:
        enriched = dict(row)
        for field in [
            "reviewer_t0_status", "corrected_t0_time", "dhf_onset_relative_to_t0",
            "first_dhf_onset_time",
        ]:
            enriched.setdefault(field, "")
        review_sheet.append([enriched.get(field, "") for field in review_fields])
    review_widths = [30, 23, 26, 12, 18, 7, 8, 20, 27, 18, 12, 13, 13, 15, 16, 38, 17, 34, 15, 15, 42, 55, 55, 55, 55, 65, 55, 18, 14, 14, 14, 20, 18, 20, 24, 22, 60, 20, 20]
    n_review = len(review_sheet)
    field_col = {field: column_name(index + 1) for index, field in enumerate(review_fields)}
    validations = [
        (f'{field_col["reviewer_dhf_label"]}2:{field_col["reviewer_dhf_label"]}{n_review}', "DHF_yes,DHF_no,indeterminate"),
        (f'{field_col["reviewer_A_domain"]}2:{field_col["reviewer_A_domain"]}{n_review}', "yes,no,unknown"),
        (f'{field_col["reviewer_B_domain"]}2:{field_col["reviewer_B_domain"]}{n_review}', "yes,no,unknown"),
        (f'{field_col["reviewer_C_domain"]}2:{field_col["reviewer_C_domain"]}{n_review}', "yes,no,unknown"),
        (f'{field_col["reviewer_evidence_sufficient"]}2:{field_col["reviewer_evidence_sufficient"]}{n_review}', "yes,no"),
        (f'{field_col["reviewer_t0_status"]}2:{field_col["reviewer_t0_status"]}{n_review}', "correct,incorrect,uncertain"),
        (f'{field_col["dhf_onset_relative_to_t0"]}2:{field_col["dhf_onset_relative_to_t0"]}{n_review}', "before_T0,T0_to_T12,after_T12,no_DHF,uncertain"),
        (f'{field_col["second_reviewer_label"]}2:{field_col["second_reviewer_label"]}{n_review}', "DHF_yes,DHF_no,indeterminate"),
        (f'{field_col["adjudicated_label"]}2:{field_col["adjudicated_label"]}{n_review}', "DHF_yes,DHF_no,indeterminate"),
    ]

    mechanism_counts = Counter()
    for row in all_rows:
        for item in row.get("likely_false_positive_mechanism", "").split("；"):
            if item:
                mechanism_counts[item] += 1
    summary_sheet = [["指标", "数值", "解释"]]
    summary_sheet.extend(
        [
            ["290例总数", summary["n_total"], "分层校准样本，不是290例算法阳性"],
            ["来自算法阳性层", 120, "objective C 60例 + treatment-only C 60例"],
            ["未知/边界/阴性对照", 170, "用于发现漏诊与估计特异度"],
            ["已完成人工审核", summary["n_existing_physician_review"], "前30例均来自algorithmic_unknown层"],
            ["本轮医生精简审核集", summary["n_new_physician_subset"], "疑难/冲突 + 分层随机质控；不含已完成且一致病例"],
            ["同窗NT-proBNP全部<300", summary["strong_negative_np_count"], "强负证据；低值冲突病例仍需复核"],
            ["算法与AI预审不一致", summary["algorithm_ai_discordant_count"], "优先人工审核"],
        ]
    )
    summary_sheet.append(["", "", ""])
    summary_sheet.append(["AI预审标签", "例数", "说明"])
    for key, value in summary["ai_label_counts"].items():
        summary_sheet.append([key, value, "预审分诊标签，非临床金标准"])
    summary_sheet.append(["", "", ""])
    summary_sheet.append(["医生审核优先级", "例数", "说明"])
    for key, value in summary["human_review_priority_counts"].items():
        summary_sheet.append([key, value, "见抽样与统计说明"])
    summary_sheet.append(["", "", ""])
    summary_sheet.append(["医生审核顺序层级", "例数", "说明"])
    for key, value in summary["human_review_tier_counts"].items():
        summary_sheet.append([key, value, "按T1→T5顺序执行；completed/deferred无需当前填写"])
    summary_sheet.append(["", "", ""])
    summary_sheet.append(["疑似误入机制", "例数", "说明"])
    for key, value in mechanism_counts.most_common():
        summary_sheet.append([key, value, "一例可有多个机制"])

    guide_rows = [
        ["主题", "执行口径"],
        ["先看哪个表", "先填写“医生精简审核”。“AI全量预审”用于追溯，不要求逐行填写。"],
        ["290例是什么", "分层校准样本：仅120例来自算法阳性层；其余170例故意抽取未知、边界和阴性对照，以发现漏诊。"],
        ["A域", "本次episode当前心衰锚点。既往史、慢性心功能分级、风险告知、鉴别诊断和问号诊断不能单独满足。"],
        ["B域", "当前急性充血/失代偿证据。优先肺水肿/肺淤血、端坐呼吸、不能平卧、粉红泡沫痰、容量超负荷；单独湿啰音/水肿/胸闷不够。"],
        ["C域", "支持证据而非单独确诊。NT-proBNP需结合年龄/肾功能/房颤；心超需有与本次急性事件相关的结构功能或充盈压证据；静脉袢利尿医嘱目前仅为执行代理。"],
        ["低利钠肽", "NT-proBNP<300 pg/mL作为强负证据，可快速判为非DHF；若有明确心源性肺水肿、显著充盈压升高或可靠的急性心衰诊断，保留为矛盾病例复核。"],
        ["心超", "轻度二/三尖瓣反流、单纯左室肥厚、慢性心腔扩大或单纯EF降低不能单独证明当前DHF；正常EF也不能排除HFpEF。"],
        ["T0", "此次index ICU episode实际入科时间；优先护理转入/首次ICU在位证据，不用文书创建时间冒充。"],
        ["时间标签", "必须区分before_T0、T0_to_T12和after_T12。住院后才发生的急性心衰不进入T0/T12 DHF风险集，应另列hospital-onset AHF研究。"],
        ["为何仍有人工审核", "前30个unknown病例中医生判定6例阳性，说明AI阴性不能机械排除；本表已将剩余unknown全部保留，并对明确层作随机质控。"],
        ["统计使用", "若未完成全部290例审核，只能按已登记抽样概率做两阶段/逆概率加权估计，并报告验证偏倚；不可把AI标签当金标准。"],
        ["已审核病例", "已完成且AI/分域一致者不要求重复填写；冲突或indeterminate病例已自动进入adjudication_needed。"],
    ]

    low_np_fields = [
        "patient_id", "visit_id", "age", "t0_time", "max_pre12_ntprobnp",
        "c_echo_abnormal_flag", "c_iv_loop_order_proxy_flag", "a_evidence_excerpt",
        "b_evidence_excerpt", "ai_pre_review_label", "ai_reason", "review_priority",
        "reviewer_dhf_label", "reviewer_comments",
    ]
    low_np_sheet = [low_np_fields] + [
        [row.get(field, "") for field in low_np_fields] for row in low_np_rows
    ]
    low_np_label_col = column_name(low_np_fields.index("reviewer_dhf_label") + 1)
    low_np_validations = [
        (
            f"{low_np_label_col}2:{low_np_label_col}{len(low_np_sheet)}",
            "DHF_yes,DHF_no,indeterminate",
        )
    ]

    sheets = [
        ("AI全量预审", sheet_xml(all_sheet, all_widths, wrap_body=True)),
        ("医生精简审核", sheet_xml(review_sheet, review_widths, wrap_body=True, data_validations=validations)),
        (
            "773队列低NP冲突5例",
            sheet_xml(
                low_np_sheet,
                [12, 18, 8, 20, 20, 18, 20, 55, 55, 18, 55, 25, 18, 60],
                wrap_body=True,
                data_validations=low_np_validations,
            ),
        ),
        ("误入机制汇总", sheet_xml(summary_sheet, [32, 16, 70], wrap_body=True)),
        ("抽样与填写说明", sheet_xml(guide_rows, [28, 110], wrap_body=True)),
    ]
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", root_rels_xml())
        archive.writestr("xl/workbook.xml", workbook_xml([name for name, _ in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", styles_xml())
        for idx, (_, content) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{idx}.xml", content)
        archive.writestr(
            "docProps/core.xml",
            f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>DHF phenotype AI triage and physician subset</dc:title><dc:creator>Codex</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created></cp:coreProperties>''',
        )
        archive.writestr(
            "docProps/app.xml",
            '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Python stdlib</Application></Properties>''',
        )
    print(OUTPUT)
    print(f"all={len(all_rows)} physician_subset={len(subset_rows)}")


if __name__ == "__main__":
    main()
