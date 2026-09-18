-- Create one row per HF anchor after saving the output of 106 as
-- `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_v2`.
--
-- This is a screening summary, not a final DHF label. It distinguishes
-- examination time from report availability time and leaves every rule result
-- available for clinical validation.

WITH cohort AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    CAST(acute_hf_icd_anchor_flag AS INT64) AS acute_hf_icd_anchor_flag,
    CAST(pre_t0_iv_loop_emar_flag AS INT64) AS pre_t0_iv_loop_emar_flag,
    CAST(pre_t0_ntprobnp_ge300_flag AS INT64) AS pre_t0_ntprobnp_ge300_flag
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates`
  WHERE CAST(admittime AS DATETIME) <= CAST(intime AS DATETIME)
),
raw AS (
  SELECT *
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_v2`
)
SELECT
  c.stay_id,
  c.subject_id,
  c.hadm_id,
  c.acute_hf_icd_anchor_flag,
  c.pre_t0_iv_loop_emar_flag,
  c.pre_t0_ntprobnp_ge300_flag,
  COUNT(r.note_id) AS n_charttime_pre_t0_reports,
  COUNTIF(r.report_available_pre_t0_flag = 1) AS n_reports_available_pre_t0,
  COUNTIF(r.storetime_missing_flag = 1) AS n_reports_storetime_missing,
  MAX(IF(r.note_id IS NOT NULL, 1, 0)) AS any_charttime_pre_t0_report_flag,
  MAX(IF(r.report_available_pre_t0_flag = 1, 1, 0)) AS any_report_available_pre_t0_flag,
  MAX(IF(r.positive_congestion_evidence_flag = 1, 1, 0)) AS any_positive_congestion_screen_flag,
  MAX(IF(r.positive_congestion_evidence_flag = 1 AND r.uncertainty_hit = 0, 1, 0))
    AS any_definite_congestion_screen_flag,
  MAX(IF(r.positive_congestion_evidence_flag = 1 AND r.report_available_pre_t0_flag = 1, 1, 0))
    AS any_available_positive_congestion_screen_flag,
  MIN(IF(r.positive_congestion_evidence_flag = 1, r.charttime, NULL))
    AS first_positive_congestion_charttime,
  MIN(IF(r.positive_congestion_evidence_flag = 1 AND r.report_available_pre_t0_flag = 1, r.storetime, NULL))
    AS first_available_positive_congestion_storetime,
  'patient_summary_v1; requires 106_raw_v2; screening_only; manual_validation_required' AS rule_version
FROM cohort c
LEFT JOIN raw r
  ON r.stay_id = c.stay_id
GROUP BY 1,2,3,4,5,6
ORDER BY stay_id;
