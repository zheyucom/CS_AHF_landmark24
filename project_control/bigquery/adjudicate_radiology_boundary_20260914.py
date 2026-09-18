#!/usr/bin/env python3
"""Conservative, auditable adjudication of the 31 radiology boundary rows.

This is a draft clinical review aid.  It uses only report text and keeps
non-chest studies out of the pulmonary-congestion denominator.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2"
INFILE = BASE / "dhf_radiology_annotation_round1_codex_prereview_user_check_20260914.csv"
OUTFILE = BASE / "dhf_radiology_annotation_round1_codex_adjudicated_20260914.csv"
CHECK = BASE / "dhf_radiology_annotation_round1_codex_adjudication_user_check_20260914.csv"

# annotation_id: (scope, modality, congestion, alternative, comment)
LABELS = {
    "DHF-RAD-0003": ("chest_radiology", "cxr", "definite_congestion", "pneumonia_ards", "双侧肺门/肺血管扩张和大量肺实变，报告明确为肺水肿与肺炎混合。"),
    "DHF-RAD-0014": ("chest_radiology", "cxr", "indeterminate", "none_apparent", "仅记录插管后与早片相仿，未提供新的肺部充血描述。"),
    "DHF-RAD-0038": ("chest_radiology", "cxr", "no_congestion", "none_apparent", "胸片明确无血管充血及急性局灶性肺炎。"),
    "DHF-RAD-0052": ("chest_radiology", "cxr", "possible_congestion", "pneumonia_ards", "轻度间质性水肿，同时有左后基底片状影，倾向不张/误吸或感染。"),
    "DHF-RAD-0060": ("chest_radiology", "other_chest", "definite_congestion", "other", "报告明确持续肺水肿、心影增大和胸腔积液；检查标题不足以可靠细分模态。"),
    "DHF-RAD-0064": ("chest_radiology", "other_chest", "definite_congestion", "other", "报告明确 substantial pulmonary edema；检查标题不足以可靠细分模态。"),
    "DHF-RAD-0069": ("mixed_or_unclear", "chest_ct", "possible_congestion", "pneumonia_ards", "胸腹盆 CT；中央多发阴影在误吸/感染/非对称肺水肿之间鉴别。"),
    "DHF-RAD-0097": ("chest_radiology", "cxr", "possible_congestion", "pneumonia_ards", "胸片显示双侧阴影增多，肺炎与非典型肺水肿均可能。"),
    "DHF-RAD-0101": ("chest_radiology", "cxr", "possible_congestion", "none_apparent", "间质性水肿仅为 possible，且受便携技术影响。"),
    "DHF-RAD-0102": ("mixed_or_unclear", "chest_ct", "indeterminate", "none_apparent", "CTA 胸腹盆；仅小量单纯胸腔积液及不张，无肺水肿描述。"),
    "DHF-RAD-0104": ("mixed_or_unclear", "chest_ct", "no_congestion", "other", "胸腹盆 CT，肺部为肺气肿、瘢痕和不张，无充血/水肿。"),
    "DHF-RAD-0132": ("chest_radiology", "cxr", "definite_congestion", "pneumonia_ards", "新发轻度间质性肺水肿，右基底浸润/不张待鉴别。"),
    "DHF-RAD-0138": ("chest_radiology", "cxr", "definite_congestion", "other", "报告明确 moderate pulmonary edema 增加并伴双侧胸腔积液。"),
    "DHF-RAD-0144": ("chest_radiology", "cxr", "possible_congestion", "none_apparent", "仅 minimal pulmonary edema 可能。"),
    "DHF-RAD-0153": ("non_chest", "ct_other", "indeterminate", "none_apparent", "颈椎 CT，非胸部检查；不能用于肺充血判定。"),
    "DHF-RAD-0156": ("chest_radiology", "chest_ct", "possible_congestion", "pneumonia_ards", "胸部 CT 明确肺炎与肺泡水肿鉴别，并有双侧胸腔积液。"),
    "DHF-RAD-0168": ("chest_radiology", "cxr", "possible_congestion", "pneumonia_ards", "胸片有中央肺血管充血，但多发阴影仍在肺炎/肺水肿之间。"),
    "DHF-RAD-0174": ("chest_radiology", "cxr", "possible_congestion", "other", "心影增大和上肺血流再分布提示 CHF，但措辞为 suggesting/probable。"),
    "DHF-RAD-0181": ("chest_radiology", "chest_ct", "indeterminate", "pneumonia_ards", "无增强胸部 CT；右侧积液和不张，肺炎不能排除，无法确认水肿。"),
    "DHF-RAD-0183": ("chest_radiology", "cxr", "definite_congestion", "pneumonia_ards", "明确肺血管充血，右侧磨玻璃影更倾向非对称肺水肿。"),
    "DHF-RAD-0190": ("chest_radiology", "cxr", "definite_congestion", "pneumonia_ards", "报告明确 upper-zone redistribution/vascular plethora 一致于 CHF，同时积液和感染不能排除。"),
    "DHF-RAD-0220": ("mixed_or_unclear", "other", "indeterminate", "other", "腹部平片，虽见双侧胸腔积液但非胸部主检查，不能据此判肺充血。"),
    "DHF-RAD-0227": ("chest_radiology", "cxr", "no_congestion", "none_apparent", "胸片明确无急性心肺异常。"),
    "DHF-RAD-0229": ("chest_radiology", "chest_ct", "no_congestion", "pulmonary_embolism_or_rv_strain", "CTA 无 PE、无积液或水肿；仅轻度右室增大提示可能右心负荷。"),
    "DHF-RAD-0233": ("non_chest", "other", "indeterminate", "postoperative_or_technical", "术中胸椎透视，非肺部诊断影像。"),
    "DHF-RAD-0236": ("non_chest", "ct_other", "indeterminate", "none_apparent", "头颅 CT，非胸部检查。"),
    "DHF-RAD-0242": ("non_chest", "ultrasound", "indeterminate", "other", "肝胆超声，非胸部检查。"),
    "DHF-RAD-0256": ("non_chest", "ct_other", "indeterminate", "none_apparent", "头颈 CTA，非胸部检查。"),
    "DHF-RAD-0264": ("chest_radiology", "other_chest", "indeterminate", "postoperative_or_technical", "胸部单片仅为 Swan-Ganz 置管透视记录，无肺部评价且无放射科医师在场。"),
    "DHF-RAD-0280": ("mixed_or_unclear", "other", "indeterminate", "other", "腹部平片仅部分显示左肺底积液/不张，不能作为肺充血阳性或阴性。"),
    "DHF-RAD-0290": ("non_chest", "ct_other", "indeterminate", "other", "颈椎 CT；胸腔积液仅部分显示，肺部需另看同日胸部 CT。"),
}

def main():
    df = pd.read_csv(INFILE, dtype=str, encoding="utf-8-sig").fillna("")
    missing = sorted(set(df.annotation_id) - set(LABELS))
    if missing:
        raise ValueError(f"missing labels: {missing}")
    for i, r in df.iterrows():
        scope, modality, congestion, alt, comment = LABELS[r.annotation_id]
        df.loc[i, "final_report_scope"] = scope
        df.loc[i, "final_modality"] = modality
        df.loc[i, "final_congestion_label"] = congestion
        df.loc[i, "final_alternative_explanation_label"] = alt
        df.loc[i, "final_comments"] = "Codex adjudication draft: " + comment
    df["reviewer_id"] = "codex_radiology_adjudication_20260914"
    df["adjudication_status"] = "codex_adjudicated_draft"
    df.to_csv(OUTFILE, index=False, encoding="utf-8-sig")
    # Only rows whose scope/modality is intrinsically mixed or whose report is
    # technically limited are offered for optional human confirmation.
    check_ids = {"DHF-RAD-0003", "DHF-RAD-0060", "DHF-RAD-0064", "DHF-RAD-0069", "DHF-RAD-0220", "DHF-RAD-0264", "DHF-RAD-0280"}
    df[df.annotation_id.isin(check_ids)].to_csv(CHECK, index=False, encoding="utf-8-sig")
    print("rows", len(df), "congestion", df.final_congestion_label.value_counts().to_dict())
    print("scope", df.final_report_scope.value_counts().to_dict())
    print("optional_user_check", len(check_ids), CHECK)

if __name__ == "__main__":
    main()
