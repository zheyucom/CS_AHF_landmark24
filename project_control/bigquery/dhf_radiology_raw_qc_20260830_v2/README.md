# DHF Radiology Import QC and Annotation Package

This package contains protected clinical text for blinded phenotype validation only. 
Do not merge it with outcome, T0-T12 predictor, or model-prediction data.

## Inputs

- Raw query 106 CSV: `project_control/bigquery/dhf_radiology_raw_v2.csv`
- Candidate-time-boundary CSV: `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/dhf_radiology_candidates.csv`
- Random seed: `20260829`

## Integrity QC

- Candidate stays with valid admission/ICU boundary: 5549
- Candidate stays excluded for invalid boundary (`admittime > intime`): 6
- Raw report rows: 4303
- Stays with at least one pre-T0 report: 1637
- `charttime` within `admittime <= charttime < intime`: 4303
- `storetime < intime`: 3593
- Missing `storetime`: 0
- `storetime >= intime`: 710

## Screen and Sampling

- definite_positive_rule_screen: 1259 eligible reports; 100 sampled
- negated_or_uncertain_screen: 864 eligible reports; 100 sampled
- no_hit_screen: 2180 eligible reports; 100 sampled
- Round 1 blinded reviews: 300 reports
- Independent round 2 blinded reviews: 60 reports (20%)

## Interpretation Boundary

The screen strata are weak labels.  `definite_positive_rule_screen` is not a final DHF diagnosis;
the clinical annotation guide defines the report-level label and the later patient-level multidomain phenotype.
