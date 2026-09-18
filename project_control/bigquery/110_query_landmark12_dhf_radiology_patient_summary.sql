-- Patient-level summary for 109_query_landmark12_dhf_radiology.sql.
-- Screening summary only; it is not a final DHF label.
-- Before running, save 109 output as
-- YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_landmark12_v1.

WITH cohort AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    CAST(admittime AS DATETIME) AS admittime,
    CAST(intime AS DATETIME) AS intime,
    DATETIME_SUB(CAST(intime AS DATETIME), INTERVAL 24 HOUR) AS window_start,
    DATETIME_ADD(CAST(intime AS DATETIME), INTERVAL 12 HOUR) AS landmark12_time,
    CAST(acute_hf_icd_anchor_flag AS INT64) AS acute_hf_icd_anchor_flag,
    CAST(pre_t0_iv_loop_emar_flag AS INT64) AS pre_t0_iv_loop_emar_flag,
    CAST(pre_t0_ntprobnp_ge300_flag AS INT64) AS pre_t0_ntprobnp_ge300_flag
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates`
  WHERE CAST(admittime AS DATETIME) <= CAST(intime AS DATETIME)
),
raw AS (
  SELECT *
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_landmark12_v1`
)
SELECT
  c.stay_id,
  c.subject_id,
  c.hadm_id,
  c.admittime,
  c.intime,
  c.window_start,
  c.landmark12_time,
  c.acute_hf_icd_anchor_flag,
  c.pre_t0_iv_loop_emar_flag,
  c.pre_t0_ntprobnp_ge300_flag,
  COUNT(r.note_id) AS n_reports_T0minus24_to_T12,
  COUNTIF(r.report_available_by_t12_flag = 1) AS n_reports_available_by_t12,
  COUNTIF(r.storetime_missing_flag = 1) AS n_reports_storetime_missing,
  MAX(IF(r.note_id IS NOT NULL, 1, 0)) AS any_report_T0minus24_to_T12_flag,
  MAX(IF(r.report_available_by_t12_flag = 1, 1, 0)) AS any_report_available_by_t12_flag,
  MAX(IF(r.positive_congestion_evidence_flag = 1, 1, 0)) AS any_positive_congestion_screen_flag,
  MAX(IF(r.positive_congestion_evidence_flag = 1 AND r.uncertainty_hit = 0, 1, 0))
    AS any_definite_congestion_screen_flag,
  MAX(IF(r.positive_congestion_evidence_flag = 1 AND r.report_available_by_t12_flag = 1, 1, 0))
    AS any_available_positive_congestion_screen_flag,
  MIN(IF(r.positive_congestion_evidence_flag = 1, r.charttime, NULL))
    AS first_positive_congestion_charttime,
  '110_landmark12_patient_summary_v1; screening_only; manual_validation_required' AS rule_version
FROM cohort c
LEFT JOIN raw r
  ON r.stay_id = c.stay_id
GROUP BY 1,2,3,4,5,6,7,8,9,10
ORDER BY stay_id;
