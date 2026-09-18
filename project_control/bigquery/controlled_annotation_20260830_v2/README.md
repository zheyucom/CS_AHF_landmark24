# DHF Radiology Import QC and Annotation Package

This package contains protected clinical text for blinded phenotype validation only. 
Do not merge it with outcome, T0-T12 predictor, or model-prediction data.

## Inputs

- Raw query 106 CSV: `project_control/bigquery/dhf_radiology_annotation_sample300_v2.csv`
- Candidate-time-boundary CSV: `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/dhf_radiology_candidates.csv`
- Random seed: `20260829`

## Integrity QC

- Candidate stays with valid admission/ICU boundary: 5549
- Candidate stays excluded for invalid boundary (`admittime > intime`): 6
- Raw report rows: 300
- Stays with at least one pre-T0 report: 259
- `charttime` within `admittime <= charttime < intime`: 300
- `storetime < intime`: 252
- Missing `storetime`: 0
- `storetime >= intime`: 48

## Screen and Sampling

- definite_positive_rule_screen: 100 eligible reports; 100 sampled
- negated_or_uncertain_screen: 100 eligible reports; 100 sampled
- no_hit_screen: 100 eligible reports; 100 sampled
- Round 1 blinded reviews: 300 reports
- Round 2 same-reviewer repeats: 60 reports (20%), copied from round 1 per user instruction; not independent inter-rater review

## Interpretation Boundary

The screen strata are weak labels.  `definite_positive_rule_screen` is not a final DHF diagnosis;
the clinical annotation guide defines the report-level label and the later patient-level multidomain phenotype.
