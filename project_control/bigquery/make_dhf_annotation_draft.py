#!/usr/bin/env python3
"""Create an AI-assisted review copy without changing the blinded source sheets.

The draft labels are conservative rule-assisted suggestions for human review,
not adjudicated clinical labels. The Chinese column is a terminology-assisted
translation and must not be treated as a certified translation.
"""

from __future__ import annotations

import csv
import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANNOTATION_DIR = ROOT / "project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2"
DEFAULT_RAW = ROOT / "project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv"


TRANSLATIONS = {
    "EXAMINATION": "检查",
    "INDICATION": "检查目的",
    "HISTORY": "病史",
    "COMPARISON": "对比检查",
    "FINDINGS": "所见",
    "IMPRESSION": "影像印象",
    "TECHNIQUE": "检查技术",
    "portable AP": "床旁前后位",
    "chest radiograph": "胸片",
    "chest radiographs": "胸片",
    "pulmonary edema": "肺水肿",
    "interstitial edema": "间质性水肿",
    "alveolar edema": "肺泡性水肿",
    "vascular congestion": "肺血管充血",
    "pulmonary vascular congestion": "肺血管充血",
    "pulmonary vascular engorgement": "肺血管扩张/充血",
    "pulmonary vascular plethora": "肺血管充血",
    "pleural effusion": "胸腔积液",
    "cardiomegaly": "心脏扩大",
    "pneumonia": "肺炎",
    "aspiration pneumonia": "吸入性肺炎",
    "atelectasis": "肺不张",
    "consolidation": "实变",
    "infiltrate": "浸润影",
    "opacity": "阴影/密度增高影",
    "no pneumothorax": "未见气胸",
    "no focal pulmonary abnormality": "未见局灶性肺部异常",
    "no definite pleural effusion": "未见明确胸腔积液",
    "no evidence of": "未见证据支持",
    "no evidence for": "未见证据支持",
    "mild pulmonary edema": "轻度肺水肿",
    "moderate pulmonary edema": "中度肺水肿",
    "severe pulmonary edema": "重度肺水肿",
    "low lung volumes": "肺容量低",
    "limited exam": "检查受限",
    "patient is slightly rotated": "患者体位略有旋转",
    "pneumothorax": "气胸",
    "pulmonary embolism": "肺栓塞",
    "right heart strain": "右心负荷/右心应变",
    "ARDS": "ARDS（急性呼吸窘迫综合征）",
    "fever": "发热",
    "tachypnea": "呼吸急促",
    "oxygen requirement": "氧需求",
    "status post": "曾接受/术后",
    "postoperative": "术后",
}

OUTPUT_COLUMNS = [
    "annotation_id",
    "stay_id",
    "note_id",
    "charttime",
    "storetime",
    "report_text",
    "report_text_zh_assist",
    "report_scope",
    "key_evidence_text_en",
    "key_evidence_text_zh_assist",
    "rule_positive_congestion",
    "rule_uncertainty",
    "rule_negation",
    "codex_draft_congestion_label",
    "codex_draft_alternative_explanation_label",
    "codex_draft_report_available_pre_t0_label",
    "codex_draft_report_available_by_t12_label",
    "codex_draft_comments",
    "reviewer_id",
    "final_report_scope",
    "final_modality",
    "final_congestion_label",
    "final_alternative_explanation_label",
    "final_report_available_pre_t0_label",
    "final_report_available_by_t12_label",
    "final_comments",
    "adjudication_label",
    "review_status",
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def assist_translate(text: str) -> str:
    out = text
    for source, target in sorted(TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        out = re.sub(re.escape(source), target, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def has_near(sentence: str, pattern: str) -> bool:
    return bool(re.search(pattern, sentence, flags=re.IGNORECASE))


def draft_congestion(text: str) -> tuple[str, str]:
    clean = normalize(text)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", clean) if part.strip()]
    positive = re.compile(
        r"\b(?:pulmonary|interstitial|alveolar)\s+(?:vascular\s+)?edema\b|"
        r"\b(?:pulmonary\s+)?vascular\s+(?:congestion|engorgement|plethora)\b",
        re.I,
    )
    uncertainty = re.compile(
        r"\b(?:possible|possibly|may represent|cannot exclude|question of|questionable|"
        r"suspicious for|concern for|versus|vs\.?|less likely)\b",
        re.I,
    )
    negation = re.compile(
        r"\b(?:no|without|not|negative for|free of)\b[^.]{0,80}\b(?:pulmonary|interstitial|"
        r"alveolar|vascular)\s+(?:edema|congestion|engorgement)\b|"
        r"\bno\s+(?:pulmonary\s+)?(?:edema|congestion)\b|"
        r"\b(?:lungs?|lung fields?)\s+(?:are\s+)?clear\b",
        re.I,
    )
    def unnegated_positive(sentence: str) -> bool:
        """Do not let negated edema erase an independently positive congestion term."""
        vascular_positive = bool(re.search(r"vascular\s+(?:congestion|engorgement|plethora)", sentence, re.I))
        vascular_negative = bool(re.search(r"\b(?:no|without|not|negative for)\b[^.]{0,60}vascular\s+(?:congestion|engorgement|plethora)", sentence, re.I))
        edema_positive = bool(re.search(r"\b(?:pulmonary|interstitial|alveolar)\s+edema\b", sentence, re.I))
        edema_negative = bool(re.search(r"\b(?:no|without|not|negative for)\b[^.]{0,60}(?:pulmonary|interstitial|alveolar)\s+edema\b", sentence, re.I))
        return (vascular_positive and not vascular_negative) or (edema_positive and not edema_negative)

    positive_sentences = [sentence for sentence in sentences if positive.search(sentence)]
    definite_sentences = [
        sentence for sentence in positive_sentences
        if not uncertainty.search(sentence) and unnegated_positive(sentence)
    ]
    uncertain_sentences = [sentence for sentence in positive_sentences if uncertainty.search(sentence)]
    explicit_negative = any(negation.search(sentence) for sentence in sentences) and not any(
        unnegated_positive(sentence) for sentence in positive_sentences
    )

    if definite_sentences:
        evidence = definite_sentences[-1]
        return "definite_congestion", f"草标：明确肯定性充血/水肿；依据：{evidence[:280]}"
    if uncertain_sentences:
        evidence = uncertain_sentences[-1]
        return "possible_congestion", f"草标：报告使用可能性/鉴别诊断语言；依据：{evidence[:280]}"
    if explicit_negative:
        return "no_congestion", "草标：报告存在明确否定肺水肿/肺充血的语句。"
    return "indeterminate", "草标：未检出明确肯定或明确否定的肺充血/肺水肿表述；请人工复核。"


def draft_alternative(text: str) -> tuple[str, str]:
    clean = normalize(text).lower()
    if re.search(r"pulmonary embol|\bpe\b|right heart strain|right ventricular strain", clean):
        return "pulmonary_embolism_or_rv_strain", "草标：报告提到肺栓塞或右心负荷/应变。"
    if re.search(r"pneumonia|aspiration|\bards\b", clean):
        return "pneumonia_ards", "草标：报告提到肺炎、吸入或 ARDS。"
    if re.search(r"postoperative|post-operative|status post|line placement|picc|rotated|rotation|limited exam", clean):
        return "postoperative_or_technical", "草标：报告包含术后背景或技术/体位因素。"
    if re.search(r"atelectasis|consolidation|infiltrate|opacity|pleural effusion", clean):
        return "other", "草标：报告存在其他肺部/胸膜异常，是否构成替代解释需人工判断。"
    return "none_apparent", "草标：未见明显替代解释；请人工确认。"


def key_evidence(text: str) -> str:
    clean = normalize(text)
    pattern = re.compile(
        r"pulmonary edema|vascular congestion|interstitial edema|alveolar edema|"
        r"pleural effusion|cardiomegaly|pneumonia|aspiration|atelectasis|"
        r"consolidation|infiltrate|pulmonary embol|right heart|\bARDS\b|"
        r"vascular engorgement|vascular plethora|"
        r"no pulmonary|without pulmonary|may represent|less likely|cannot exclude|"
        r"suspicious",
        re.I,
    )
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", clean) if part.strip()]
    selected = [sentence for sentence in sentences if pattern.search(sentence)]
    return " | ".join(selected[:4])


def load_raw_flags(raw_path: Path) -> dict[str, dict[str, str]]:
    with raw_path.open(newline="", encoding="utf-8") as handle:
        return {row["note_id"]: row for row in csv.DictReader(handle)}


def assessment_text(text: str) -> str:
    """Prefer radiologist findings/impression over indication and history."""
    clean = normalize(text)
    matches = list(re.finditer(r"\b(?:FINDINGS|IMPRESSION)\s*:", clean, flags=re.I))
    if matches:
        return clean[matches[-1].end():]
    return clean


def classify_scope(text: str) -> str:
    """Identify reports usable for pulmonary congestion review."""
    clean = normalize(text).lower()
    header = clean[:500]
    chest = re.search(
        r"\b(?:chest|thorax|portable\s+chest|ap\s+chest|pa\s+and\s+lat|"
        r"chest\s+radiograph|chest\s+x[- ]?ray|lung\s+fields?)\b",
        header,
    )
    non_chest = re.search(
        r"ct\s+head|mr\s+head|brain|carotid|renal\s+(?:u\.?s\.?|ultrasound)|"
        r"abdomen|pelvis|femur|hip|knee|lower\s+extremity|upper\s+extremity|"
        r"spine|sinus|mandible|breast|\bDVT\b|fluoroscop|angiograph|"
        r"liver|gallbladder|kidney|retroperitone",
        header,
    )
    pulmonary_finding = re.search(
        r"\b(?:pulmonary|interstitial|alveolar)\s+edema\b|"
        r"\b(?:pulmonary\s+)?vascular\s+(?:congestion|engorgement|plethora)\b|"
        r"\bpleural\s+effusion\b|\b(?:lungs?|lung fields?)\b|"
        r"\b(?:airspace|perihilar|basilar)\s+(?:opacity|opacities|consolidation)\b",
        assessment_text(text),
        flags=re.I,
    )
    if chest and not non_chest:
        return "chest_radiology"
    if chest and non_chest:
        return "mixed_or_unclear"
    if non_chest and not pulmonary_finding:
        return "non_chest_radiology"
    if pulmonary_finding:
        return "chest_radiology_inferred"
    return "non_chest_radiology"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation-dir", type=Path, default=DEFAULT_ANNOTATION_DIR)
    parser.add_argument("--raw-csv", type=Path, default=DEFAULT_RAW)
    args = parser.parse_args()
    round1 = args.annotation_dir / "dhf_radiology_annotation_round1.csv"
    output = args.annotation_dir / "dhf_radiology_annotation_round1_codex_draft.csv"

    raw_by_note = load_raw_flags(args.raw_csv)
    with round1.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))

    output_rows: list[dict[str, str]] = []
    for row in source_rows:
        raw = raw_by_note.get(row["note_id"], {})
        scope = classify_scope(row["report_text"])
        assessed_text = assessment_text(row["report_text"])
        if scope != "non_chest_radiology":
            congestion, congestion_comment = draft_congestion(assessed_text)
            alternative, alternative_comment = draft_alternative(assessed_text)
            evidence_en = key_evidence(assessed_text)
            if scope == "mixed_or_unclear":
                congestion_comment = "草标：报告范围含胸部线索但检查范围混杂，请优先人工确认检查类型。 " + congestion_comment
        else:
            congestion = "indeterminate"
            alternative = "unclear"
            evidence_en = ""
            congestion_comment = "草标：非明确胸部影像报告，不用于肺充血判断。"
            alternative_comment = "草标：请将该行作为检查范围不适用/需排除记录处理。"
        available = row.get("report_available_pre_t0_label", "")
        if available not in {"yes", "no", "unknown"}:
            available_flag = raw.get("report_available_pre_t0_flag", "")
            available = {"1": "yes", "0": "no"}.get(available_flag, "unknown")
        comments = f"{congestion_comment} {alternative_comment} 中文为辅助翻译，不能替代英文原文。"
        output_rows.append({
            "annotation_id": row["annotation_id"],
            "stay_id": row["stay_id"],
            "note_id": row["note_id"],
            "charttime": row["charttime"],
            "storetime": row["storetime"],
            "report_text": row["report_text"],
            "report_text_zh_assist": assist_translate(row["report_text"]),
            "report_scope": scope,
            "key_evidence_text_en": evidence_en,
            "key_evidence_text_zh_assist": assist_translate(evidence_en),
            "rule_positive_congestion": row["rule_positive_congestion"],
            "rule_uncertainty": row["rule_uncertainty"],
            "rule_negation": row["rule_negation"],
            "codex_draft_congestion_label": congestion,
            "codex_draft_alternative_explanation_label": alternative,
            "codex_draft_report_available_pre_t0_label": available,
            "codex_draft_report_available_by_t12_label": row.get("report_available_by_t12_label", "unknown"),
            "codex_draft_comments": comments,
            "reviewer_id": "",
            "final_report_scope": "",
            "final_modality": "",
            "final_congestion_label": "",
            "final_alternative_explanation_label": "",
            "final_report_available_pre_t0_label": available,
            "final_report_available_by_t12_label": row.get("report_available_by_t12_label", "unknown"),
            "final_comments": "",
            "adjudication_label": "",
            "review_status": "pending_human_review",
        })

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"wrote {len(output_rows)} rows to {output}")


if __name__ == "__main__":
    main()
