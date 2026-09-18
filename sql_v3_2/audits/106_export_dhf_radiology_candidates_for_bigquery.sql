-- Export every v3.3 landmark-eligible HF-anchored stay for pre-T0
-- radiology validation in BigQuery. This expands the old 650-stay
-- strict AHF candidate export to all 5,555 HF ICD anchors.
-- No label or predictor fields are exported.

\copy (select stay_id, subject_id, hadm_id, admittime, intime, hf_icd_acute_or_acute_on_chronic as acute_hf_icd_anchor_flag, actual_iv_loop_emar_pre_t0_flag as pre_t0_iv_loop_emar_flag, ntprobnp_ge300_pre_t0_flag as pre_t0_ntprobnp_ge300_flag from study_ahf_v3_2.audit_099_ahf_phenotype_v1 where hf_icd_any = 1 order by stay_id) to 'project_control/bigquery/dhf_radiology_candidates.csv' with (format csv, header true)
