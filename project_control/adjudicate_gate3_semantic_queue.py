#!/usr/bin/env python3
"""Conservative adjudication pass for the 45-case Gate-3 semantic queue.

The output is an auditable pre-review aid.  It deliberately keeps borderline
cases as ``unknown`` and never treats generic risk-consent/template language
as a heart-failure anchor.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "project_control/internal_validation/20260912"
INFILE = BASE / "internal_gate3_semantic_evidence_20260914.csv"
OUTFILE = BASE / "internal_gate3_semantic_evidence_20260914_adjudicated.csv"
CHECK = BASE / "internal_gate3_semantic_user_check_20260914.csv"

# Cases with a direct disease anchor and temporally proximate support.
SUPPORTED = {
    "G3-006": "文书明确记录心衰/肺水肿风险，并有心功能不全、下肢水肿及袢利尿剂区间；保留为 echo-supported draft。",
    "G3-007": "急性心肌梗死、NT-proBNP 1997 和湿啰音/氧合异常构成心源性失代偿候选；需确认是否为本次HF而非单纯AMI。",
    "G3-018": "文书明确心力衰竭、扩张性心肌病、全心扩大、NYHA III级，NT-proBNP >4000；保留。",
    "G3-022": "风湿性联合瓣膜病、舒张期杂音、下肢水肿及呋塞米医嘱；保留。",
    "G3-029": "心肌炎、袢利尿剂和心超异常同窗；失代偿体征不完整，保留为需确认的候选。",
    "G3-034": "心肌病重、NT-proBNP >25000、袢利尿剂医嘱；保留。",
    "G3-036": "入院诊断明确心功能不全/NYHA II-III级，明显下肢水肿并使用袢利尿剂；保留。",
    "G3-046": "室速、NT-proBNP升高和袢利尿剂同窗；需确认是否存在急性充血而非单纯心律失常。",
}

# Strong alternative-diagnosis dominance with no direct HF anchor in the
# patient-specific assessment.  These are excluded from the strict cohort.
NOT_SUPPORTED = {
    "G3-002": "脑出血/脑疝术后主导；查体无水肿、肺部清；心衰仅来自模板或泛化风险语句。",
    "G3-004": "消化道静脉曲张出血、贫血和止血治疗主导；无患者特异性HF锚点。",
    "G3-005": "多发创伤、肺挫伤和蛛网膜下腔出血主导；无HF锚点。",
    "G3-003": "烟雾病/神经外科术后主导；肺部和下肢查体无充血，心衰仅来自通用风险模板。",
    "G3-008": "脊髓损伤术后，NT-proBNP 115且无充血体征；不支持DHF。",
    "G3-012": "脑梗死溶栓后主导；仅有下肢水肿，未见患者特异性HF锚点或利尿强化。",
    "G3-015": "糖尿病酮症酸中毒昏迷和急性肾损害主导；肺水肿仅为外院问号描述。",
    "G3-016": "胆囊穿孔/腹腔感染/脓毒症主导；心衰仅来自模板化风险列表。",
    "G3-017": "颅内出血/脑疝主导，NT-proBNP 253且无充血体征；不支持DHF。",
    "G3-019": "乙状结肠穿孔/憩室炎术后主导；无HF锚点。",
    "G3-021": "感染/透析相关问题主导，肺部和下肢查体阴性；不支持DHF。",
    "G3-020": "脑出血合并吸入性肺炎主导，NT-proBNP 270且无充血体征；不支持DHF。",
    "G3-023": "感染性休克/脓毒症及腹腔引流主导；无HF锚点。",
    "G3-025": "上消化道穿孔术后主导；心衰仅见泛化模板。",
    "G3-027": "肝恶性肿瘤、消化道出血/休克主导；无HF锚点。",
    "G3-028": "吸入性肺炎和脑梗死主导；轻度水肿不能单独确认DHF。",
    "G3-031": "胆管炎/脓毒症主导；无HF锚点。",
    "G3-033": "多发创伤、血气胸和失血性休克主导；无HF锚点。",
    "G3-037": "脑出血主导；肺部/循环查体缺乏充血证据。",
    "G3-038": "脑梗死主导；无患者特异性HF锚点。",
    "G3-039": "脑梗死主导；无患者特异性HF锚点。",
    "G3-041": "阑尾炎/腹膜炎/脓毒症主导；肺部和下肢查体阴性。",
    "G3-042": "急性胰腺炎主导，NT-proBNP 295且无水肿/影像充血；不支持DHF。",
    "G3-045": "气胸和肺气肿主导，影像未提供肺水肿；不支持DHF。",
    "G3-035": "脑血管病主导，NT-proBNP 246且无充血体征；不支持DHF。",
    "G3-044": "呼吸衰竭伴肺炎/肺栓塞待排和术后背景主导；无HF锚点。",
    "G3-048": "脑血管意外溶栓后主导；无HF锚点。",
    "G3-049": "肠梗阻术后，NT-proBNP 764但无充血体征；单独BNP不足。",
    "G3-050": "终末期肾病/透析和高钾主导，BNP缺失且查体无充血。",
    "G3-014": "腹腔感染、肺炎和肾功能不全主导；NT-proBNP升高可由肾功能不全解释，床旁心超EF 65%且未见结构/室壁运动异常，无患者特异性HF锚点或心源性利尿强化。",
    "G3-040": "脑出血、肺炎、气切和长期卧床背景主导；虽有下肢凹陷性水肿和湿啰音，但无患者特异性HF诊断、BNP/心超或心源性治疗证据，‘心衰可能’仅见风险告知模板。",
    "G3-009": "冠心病/多瓣膜病为既往结构性背景，但本次由创伤性脑出血、骨折和肺部感染主导；查体无湿啰音或水肿，呋塞米区间未注明心衰/充血适应证，缺少本次患者特异性HF锚点。",
    "G3-010": "脑梗死溶栓主导；心衰词仅出现在AIS-APS评分模板的既往史/风险条目，实际查体心肺无异常且无水肿，无本次HF或充血证据。",
    "G3-024": "右侧丘脑脑出血主导；NT-proBNP 98且无充血体征，心力衰竭/心功能不全仅出现在病危通知的可能风险列表，不构成患者特异性HF锚点。",
    "G3-026": "肠梗阻术后并肺炎/呼吸机支持主导；心肺听诊和下肢查体均无充血，心功能不全/水肿词来自通用病情恶化模板，无本次HF锚点。",
    "G3-030": "创伤性脾破裂及失血性休克主导；心衰/心功能不全仅出现在围术期风险告知，缺乏本次患者特异性充血或心源性管理证据。",
    "G3-047": "肾盂肿瘤术后及围术期风险主导；NT-proBNP 678–1138但查体无水肿/湿啰音，心功能不全仅见于病危通知的可能并发症列表，无本次HF锚点。",
}

def main():
    d = pd.read_csv(INFILE, dtype=str, encoding="utf-8-sig").fillna("")
    out = []
    for _, r in d.iterrows():
        rid = r.review_id
        rr = r.to_dict()
        if rid in SUPPORTED:
            tier = "echo_supported_draft"
            status = "retain_candidate"
            reason = SUPPORTED[rid]
        elif rid in NOT_SUPPORTED:
            tier = "not_supported"
            status = "exclude_draft"
            reason = NOT_SUPPORTED[rid]
        else:
            tier = "unknown"
            status = "manual_check"
            reason = "现有证据不足以在不依赖模板语句的情况下确认或排除DHF。"
        rr["codex_adjudication_status"] = status
        rr["codex_adjudication_reason"] = reason
        rr["dhf_tier_adjudicated"] = tier
        rr["reviewer_id_adjudication"] = "codex_conservative_pre_review_20260914"
        out.append(rr)
    o = pd.DataFrame(out)
    o.to_csv(OUTFILE, index=False, encoding="utf-8-sig")
    checks = o[o.codex_adjudication_status == "manual_check"].copy()
    cols = ["review_id", "patient_id", "visit_id", "t0_time_final", "pre_t12_diagnoses",
            "pre_t12_bnp", "pre_t12_loop_orders", "pre_t12_document_evidence",
            "alternative_explanation_evidence", "codex_adjudication_reason"]
    checks[cols].to_csv(CHECK, index=False, encoding="utf-8-sig")
    print("rows", len(o), "retain", (o.codex_adjudication_status == "retain_candidate").sum(),
          "exclude", (o.codex_adjudication_status == "exclude_draft").sum(),
          "manual_check", len(checks))
    print(checks[["review_id", "pre_t12_diagnoses", "pre_t12_bnp", "pre_t12_loop_orders"]].to_string(index=False))

if __name__ == "__main__":
    main()
