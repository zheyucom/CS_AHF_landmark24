-- Export join keys and audited time boundaries for the strict pre-T0 cohort.
-- Including the time fields lets BigQuery read only MIMIC-IV-Note.
-- Upload the resulting CSV to a user-owned BigQuery dataset before
-- running project_control/bigquery/103_query_pre_t0_radiology.sql.

\copy (select stay_id, subject_id, hadm_id, admittime, intime from study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1 order by stay_id) to 'project_control/bigquery/strict_pre_t0_ahf_ids.csv' with (format csv, header true)
