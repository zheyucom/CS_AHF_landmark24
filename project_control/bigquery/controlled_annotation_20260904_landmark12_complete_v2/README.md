# DHF Radiology Import QC and Annotation Package

## 你要打开的文件

临床复核请打开：`dhf_radiology_annotation_round1_codex_draft.csv`。

完整路径：

`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_draft.csv`

该文件包含 300 条报告。只填写 `reviewer_id`、`final_report_scope`、`final_modality`、`final_congestion_label`、`final_alternative_explanation_label` 和 `final_comments`；`codex_draft_*` 列只作参考。不要打开旧的 `controlled_annotation_20260830_v2` 文件夹，也不要把 `dhf_radiology_annotation_round1.csv` 当作最终复核副本。

This package contains protected clinical text for blinded phenotype validation only. 
Do not merge it with outcome, T0-T12 predictor, or model-prediction data.

## Inputs

- Complete landmark batch CSV: `project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`
- Candidate-time-boundary CSV: `project_control/bigquery/dhf_radiology_candidates.csv`
- Random seed: `20260904`

## Integrity QC

- Stays represented in the complete export with valid landmark boundaries: 3886
- Candidate stays excluded for invalid boundary (`admittime > intime`): 0
- Raw report rows: 7828
- Stays with at least one pre-T0 report: 3886
- `charttime` within `admittime <= charttime < intime`: 7828
- `storetime < intime`: 3352
- Missing `storetime`: 0
- `storetime >= intime`: 4476
- `storetime < landmark12_time`: 6415

## Screen and Sampling

- definite_positive_rule_screen: 3020 eligible reports; 100 sampled
- negated_or_uncertain_screen: 1564 eligible reports; 100 sampled
- no_hit_screen: 3244 eligible reports; 100 sampled
- Round 1 blinded reviews: 300 reports
- Independent round 2 blinded reviews: 60 reports (20%)

## Interpretation Boundary

The screen strata are weak labels.  `definite_positive_rule_screen` is not a final DHF diagnosis;
the clinical annotation guide defines the report-level label and the later patient-level multidomain phenotype.

## Scope-first Annotation Update

Before assigning a congestion label, the reviewer must complete `final_report_scope` and
`final_modality` in `dhf_radiology_annotation_round1_codex_draft.csv`. Chest radiographs and
chest CT/CTA are both eligible for pulmonary-congestion review. Non-chest reports are not negative
lung-congestion evidence: label them `non_chest_radiology` / `non_chest` / `indeterminate` and
exclude them from the report-level pulmonary-congestion PPV denominator. CT non-performance is not
CT-negative; concurrent CXR and CT positivity is a sensitivity analysis only.
