# DHF Radiology Import QC and Annotation Package

This package contains protected clinical text for blinded phenotype validation only. 
Do not merge it with outcome, T0-T12 predictor, or model-prediction data.

## Inputs

- Raw query 106 CSV: `project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`
- Candidate-time-boundary CSV: `project_control/bigquery/dhf_radiology_candidates.csv`
- Random seed: `20260904`

## Integrity QC

- Candidate stays with valid admission/ICU boundary: 3886
- Candidate stays excluded for invalid boundary (`admittime > intime`): 0
- Raw report rows: 7828
- Stays with at least one pre-T0 report: 3886
- `charttime` within `admittime <= charttime < intime`: 7828
- `storetime < intime`: 3352
- Missing `storetime`: 0
- `storetime >= intime`: 4476

## Screen and Sampling

- definite_positive_rule_screen: 3020 eligible reports; 100 sampled
- negated_or_uncertain_screen: 1564 eligible reports; 100 sampled
- no_hit_screen: 3244 eligible reports; 100 sampled
- Round 1 blinded reviews: 300 reports
- Independent round 2 blinded reviews: 60 reports (20%)

## Interpretation Boundary

The screen strata are weak labels.  `definite_positive_rule_screen` is not a final DHF diagnosis;
the clinical annotation guide defines the report-level label and the later patient-level multidomain phenotype.
