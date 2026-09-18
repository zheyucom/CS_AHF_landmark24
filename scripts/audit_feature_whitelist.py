#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feature whitelist audit for CS_AHF_landmark24 (v3 -> v3.1).

Classifies every column of study_ahf_v3.model_080g_modeling_dataset_v2 into:
  A_remove       - eligibility/final-coding variables (leakage; never predictors)
  B_sensitivity  - eligibility-derived severity/time variables (report separately,
                   run sensitivity analyses; do NOT put in the primary feature set)
  C_keep         - safe predictor candidates (0-12h available)
  ID_LABEL       - identifiers / time anchors / outcome labels (never predictors)

Outputs feature_whitelist_v3_1.csv for downstream modeling.
"""
import csv
import re

COLS_FILE = "/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/20260826_ahf_qualify_audit/080G_columns_full.txt"
OUT_FILE = "/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/20260826_ahf_qualify_audit/feature_whitelist_v3_1.csv"

ID_LABEL = {
    "subject_id", "hadm_id", "stay_id",
    "intime", "landmark12_time", "window60_time",
    "primary_outcome_flag",
    "label_support_escalation_flag", "label_nee_escalation_flag",
    "label_death_12_60_flag", "label_hd_nee010_flag", "label_hd_no_nee_flag",
    "label_mixed_shock_proxy_flag", "label_hd_lactate_confirmed_flag",
}

# A: final ICD codes / eligibility flags / cohort markers
A_REMOVE = {
    # final discharge ICD sequence (retrospective, freq 1.00 in v3 selection)
    "hf_icd_primary_seq", "hf_icd_seq_eq1_flag", "hf_icd_seq_2_5_flag",
    "hf_icd_seq_le5", "acute_hf_icd_flag",
    # eligibility evidence flags (used only to qualify for the cohort)
    "iv_loop_rx_early12_flag", "ntprobnp_ge300_early12_flag",
    "ahf_evidence_score_primary_12h",
    "early_sepsis12_main_flag",
    # infection qualification timing bins (T_qualify-like; correlates with outcome)
    "suspected_infection_before_icu_flag",
    "suspected_infection_icu_0_6h_flag",
    "suspected_infection_icu_6_12h_flag",
}

# B: severity/time derived from eligibility evidence -> sensitivity only
B_PATTERNS = [
    re.compile(r"^early_sepsis12_max_sofa_score$"),
    re.compile(r"^early_sepsis12_suspected_infection_hour$"),
    re.compile(r"^early_sepsis12_sofa_hour$"),
    re.compile(r"^charlson_"),  # based on current-admission final ICD; not portable
]

# C excludes: keep everything else that is a 0-12h measurable predictor.

def classify(col):
    if col in ID_LABEL:
        return "ID_LABEL"
    if col in A_REMOVE:
        return "A_REMOVE"
    if any(p.match(col) for p in B_PATTERNS):
        return "B_SENSITIVITY"
    return "C_KEEP"

with open(COLS_FILE) as f:
    cols = [ln.strip() for ln in f if ln.strip()]

rows = []
for c in cols:
    rows.append({"column": c, "category": classify(c)})

with open(OUT_FILE, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "category"])
    w.writeheader()
    w.writerows(rows)

from collections import Counter
cnt = Counter(r["category"] for r in rows)
print("total columns:", len(rows))
for k in ["ID_LABEL", "A_REMOVE", "B_SENSITIVITY", "C_KEEP"]:
    print(f"  {k}: {cnt.get(k, 0)}")

print("\nA_REMOVE (must be dropped from modeling):")
for r in rows:
    if r["category"] == "A_REMOVE":
        print("  -", r["column"])

print("\nB_SENSITIVITY (report separately, not primary features):")
for r in rows:
    if r["category"] == "B_SENSITIVITY":
        print("  -", r["column"])
