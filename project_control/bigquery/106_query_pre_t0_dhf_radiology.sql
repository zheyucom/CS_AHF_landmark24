-- Pre-T0 radiology evidence extraction for all landmark-eligible HF ICD anchors.
-- This validates the DHF phenotype before any final cohort or model is frozen.
--
-- Before running:
-- 1) Run sql_v3_2/audits/106_export_dhf_radiology_candidates_for_bigquery.sql.
-- 2) Upload dhf_radiology_candidates.csv as
--    `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates`.
-- 3) Replace YOUR_BILLING_PROJECT below.
--
-- The local CSV supplies the audited admission and ICU time boundaries, so
-- only MIMIC-IV-Note radiology access is required. This output is for phenotype
-- validation. It is not a predictor, and regex output is not a gold standard.

WITH cohort AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    -- MIMIC-IV-Note radiology charttime/storetime are DATETIME.  Keep the
    -- candidate's local wall-clock boundaries in the same BigQuery type.
    CAST(admittime AS DATETIME) AS admittime,
    CAST(intime AS DATETIME) AS intime,
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
   AND r.charttime >= c.admittime
   AND r.charttime < c.intime
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
    WHEN storetime < intime THEN 1
    ELSE 0
  END AS report_available_pre_t0_flag,
  CAST(storetime IS NULL AS INT64) AS storetime_missing_flag,
  CAST(
    (pulmonary_edema_hit = 1 AND pulmonary_edema_negation_hit = 0)
    OR (vascular_congestion_hit = 1 AND vascular_congestion_negation_hit = 0)
    AS INT64
  ) AS positive_congestion_evidence_flag,
  'bigquery_dhf_radiology_regex_v2; charttime_pre_t0; storetime_availability_audited; manual_validation_required' AS rule_version
FROM flagged
ORDER BY stay_id, charttime, note_id;
