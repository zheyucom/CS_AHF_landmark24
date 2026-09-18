-- Radiology evidence extraction for the primary DHF window.
-- Window: ICU intime - 24 h <= charttime < ICU intime + 12 h.
-- This is phenotype evidence only. It must not be used as a 0-12 h predictor.
--
-- Before running:
-- 1) Upload dhf_radiology_candidates.csv as
--    YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates.
-- 2) Replace YOUR_BILLING_PROJECT below.
-- 3) Save the result as YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_landmark12_v1.

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
source AS (
  SELECT
    c.*,
    r.note_id,
    r.note_type,
    r.note_seq,
    r.charttime,
    r.storetime,
    r.text,
    REGEXP_REPLACE(LOWER(COALESCE(r.text, '')), r'[^a-z0-9]+', ' ') AS normalized_text
  FROM cohort c
  JOIN `physionet-data.mimiciv_note.radiology` r
    ON r.subject_id = c.subject_id
   AND r.hadm_id = c.hadm_id
   AND r.charttime >= c.window_start
   AND r.charttime < c.landmark12_time
),
flagged AS (
  SELECT
    s.*,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'pulmonary edema|interstitial edema|interstitial pulmonary edema|alveolar edema'
    ) AS INT64) AS pulmonary_edema_hit,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'vascular congestion|pulmonary vascular congestion|cephalization|vascular engorgement'
    ) AS INT64) AS vascular_congestion_hit,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'pleural effusion|pleural fluid|bilateral effusions'
    ) AS INT64) AS pleural_effusion_hit,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'cardiomegaly|enlarged cardiac silhouette|enlarged heart'
    ) AS INT64) AS cardiomegaly_hit,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'no pulmonary edema|without pulmonary edema|no evidence of edema|no edema'
    ) AS INT64) AS pulmonary_edema_negation_hit,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'no vascular congestion|without vascular congestion'
    ) AS INT64) AS vascular_congestion_negation_hit,
    CAST(REGEXP_CONTAINS(s.normalized_text,
      r'possible|probable|cannot exclude|may represent|suggestive of|question of'
    ) AS INT64) AS uncertainty_hit
  FROM source s
)
SELECT
  stay_id,
  subject_id,
  hadm_id,
  admittime,
  intime,
  window_start,
  landmark12_time,
  acute_hf_icd_anchor_flag,
  pre_t0_iv_loop_emar_flag,
  pre_t0_ntprobnp_ge300_flag,
  note_id,
  note_type,
  note_seq,
  charttime,
  storetime,
  text,
  pulmonary_edema_hit,
  vascular_congestion_hit,
  pleural_effusion_hit,
  cardiomegaly_hit,
  pulmonary_edema_negation_hit,
  vascular_congestion_negation_hit,
  uncertainty_hit,
  CASE
    WHEN storetime IS NULL THEN NULL
    WHEN storetime < landmark12_time THEN 1
    ELSE 0
  END AS report_available_by_t12_flag,
  CAST(storetime IS NULL AS INT64) AS storetime_missing_flag,
  CAST(
    (pulmonary_edema_hit = 1 AND pulmonary_edema_negation_hit = 0)
    OR (vascular_congestion_hit = 1 AND vascular_congestion_negation_hit = 0)
    AS INT64
  ) AS positive_congestion_evidence_flag,
  '109_landmark12_radiology_regex_v1; charttime_T0-24h_to_T12; report_availability_audited; manual_validation_required' AS rule_version
FROM flagged
ORDER BY stay_id, charttime, note_id;
