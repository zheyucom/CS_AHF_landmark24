#!/usr/bin/env python3
"""Create a transparent Codex pre-review layer for the 300 radiology rows.

This does not overwrite the blinded draft or claim clinician adjudication.
It fills ``final_*`` fields in a separate copy and leaves the English report
text untouched.  Ambiguous language remains ``indeterminate`` or
``possible_congestion``.
"""
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2"
INFILE = BASE / "dhf_radiology_annotation_round1_codex_draft.csv"
OUTFILE = BASE / "dhf_radiology_annotation_round1_codex_prereviewed_20260914.csv"
CHECK = BASE / "dhf_radiology_annotation_round1_codex_prereview_user_check_20260914.csv"

def modality(text, scope):
    t = text.lower()
    if scope == "non_chest_radiology": return "non_chest"
    if scope == "mixed_or_unclear": return "mixed_or_unclear"
    if re.search(r"\b(ct|cta|computed tomography|tomographic)\b", t): return "chest_ct"
    if re.search(r"chest|lung|portable ap|frontal chest|pa and lat|radiograph|x-ray", t): return "cxr"
    return "other_chest"

def congestion(text, scope):
    if scope == "non_chest_radiology": return "indeterminate"
    t = re.sub(r"\s+", " ", text.lower())
    neg = re.search(r"\b(?:no|without|negative for|not seen|not identified|absent|free of)\b.{0,80}(?:pulmonary edema|vascular congestion|interstitial edema|airspace edema|pulmonary congestion)", t)
    pos = re.search(r"(?:pulmonary edema|vascular congestion|interstitial edema|airspace edema|pulmonary congestion|vascular engorgement|cephalization|alveolar edema)", t)
    uncertain = re.search(r"(?:may|might|could|cannot exclude|question of|possible|suggests? but|suspicious for).{0,80}(?:edema|congestion|fluid overload)", t)
    if pos and uncertain: return "possible_congestion"
    if pos and not neg: return "definite_congestion"
    if neg and not pos: return "no_congestion"
    return "indeterminate"

def alternative(text):
    t = text.lower()
    if re.search(r"pneumonia|aspiration|ards|consolidation|infectious", t): return "pneumonia_ards"
    if re.search(r"pulmonary embol|\bpe\b|right heart strain", t): return "pulmonary_embolism_or_rv_strain"
    if re.search(r"post[- ]?operative|postoperative|surgery|intubat|line placement|low lung volumes|technique", t): return "postoperative_or_technical"
    if re.search(r"pleural effusion|atelectasis|pneumothorax|mass|nodule|fibrosis|emphysema", t): return "other"
    return "none_apparent"

def main():
    d = pd.read_csv(INFILE, dtype=str, encoding="utf-8-sig").fillna("")
    rows=[]
    for _, r in d.iterrows():
        scope = r.report_scope if r.report_scope in {"chest_radiology", "non_chest_radiology", "mixed_or_unclear", "chest_radiology_inferred"} else "mixed_or_unclear"
        if scope == "chest_radiology_inferred": scope = "chest_radiology"
        text = str(r.report_text)
        # The prior rule screen already preserves sentence-level evidence and
        # is used as the label proposal; this pass only normalizes scope and
        # keeps non-chest studies indeterminate.
        lab = "indeterminate" if scope == "non_chest_radiology" else r.get("codex_draft_congestion_label", "indeterminate")
        alt = r.get("codex_draft_alternative_explanation_label", "unclear") or alternative(text)
        mm = modality(text, scope)
        comments = (
            f"Codex预审核：scope={scope}; modality={mm}; congestion={lab}; alternative={alt}。"
            "仅依据英文原文和规则草标，中文辅助翻译不替代原文；本行仍需临床人工确认。"
        )
        rr = r.to_dict()
        rr.update({
            "reviewer_id": "codex_pre_review_20260914",
            "final_report_scope": scope,
            "final_modality": mm,
            "final_congestion_label": lab,
            "final_alternative_explanation_label": alt,
            "final_report_available_pre_t0_label": r.get("codex_draft_report_available_pre_t0_label", "unknown"),
            "final_report_available_by_t12_label": r.get("codex_draft_report_available_by_t12_label", "unknown"),
            "final_comments": comments,
            "review_status": "codex_pre_review",
        })
        rows.append(rr)
    o=pd.DataFrame(rows); o.to_csv(OUTFILE,index=False,encoding="utf-8-sig")
    # Escalate only reports whose scope/modality is unclear or whose language
    # combines a positive and a negated/uncertain congestion statement.
    mask=(o.final_report_scope=="mixed_or_unclear") | (o.report_scope=="chest_radiology_inferred") | (o.final_congestion_label=="possible_congestion")
    o.loc[mask, ["annotation_id","stay_id","charttime","report_text","final_report_scope","final_modality","final_congestion_label","final_alternative_explanation_label","final_comments"]].to_csv(CHECK,index=False,encoding="utf-8-sig")
    print('rows',len(o),'scope',o.final_report_scope.value_counts().to_dict(),'modality',o.final_modality.value_counts().to_dict(),'congestion',o.final_congestion_label.value_counts().to_dict(),'user_check',int(mask.sum()))

if __name__=='__main__': main()
