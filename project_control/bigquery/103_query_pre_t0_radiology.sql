-- CS_AHF_landmark24: BigQuery-only pre-T0 radiology evidence extraction.
--
-- Before running:
--   1) Upload strict_pre_t0_ahf_ids.csv as
--      `YOUR_BILLING_PROJECT.ahf_work.strict_pre_t0_ahf_ids`.
--   2) Replace YOUR_BILLING_PROJECT below with that project id.
--   3) Ensure the account can read MIMIC-IV-Note. The uploaded table already
--      contains the locally audited admittime and ICU intime boundaries, so
--      core MIMIC-IV table access is not required for this query.
--
-- The query reads Note data from PhysioNet and returns only reports linked
-- to the existing local strict cohort. It is validation output, not a model
-- predictor or a replacement for clinical adjudication.

WITH cohort AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    CAST(admittime AS TIMESTAMP) AS admittime,
    CAST(intime AS TIMESTAMP) AS intime
  FROM `YOUR_BILLING_PROJECT.ahf_work.strict_pre_t0_ahf_ids`
),
source AS (
  SELECT
    c.stay_id,
    c.subject_id,
    c.hadm_id,
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
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'pulmonary edema|interstitial edema|interstitial pulmonary edema|alveolar edema'
    ) AS INT64) AS pulmonary_edema_hit,
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'vascular congestion|pulmonary vascular congestion|cephalization|vascular engorgement'
    ) AS INT64) AS vascular_congestion_hit,
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'pleural effusion|pleural fluid|bilateral effusions'
    ) AS INT64) AS pleural_effusion_hit,
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'cardiomegaly|enlarged cardiac silhouette|enlarged heart'
    ) AS INT64) AS cardiomegaly_hit,
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'no pulmonary edema|without pulmonary edema|no evidence of edema|no edema'
    ) AS INT64) AS pulmonary_edema_negation_hit,
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'no vascular congestion|without vascular congestion'
    ) AS INT64) AS vascular_congestion_negation_hit,
    CAST(REGEXP_CONTAINS(
      s.normalized_text,
      r'possible|probable|cannot exclude|may represent|suggestive of|question of'
    ) AS INT64) AS uncertainty_hit
  FROM source s
)
SELECT
  stay_id,
  subject_id,
  hadm_id,
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
  CAST(
    (pulmonary_edema_hit = 1 AND pulmonary_edema_negation_hit = 0)
    OR (vascular_congestion_hit = 1 AND vascular_congestion_negation_hit = 0)
    AS INT64
  ) AS positive_congestion_evidence_flag,
  'bigquery_radiology_regex_v1; local_times=admittime<=charttime<intime' AS rule_version
FROM flagged
ORDER BY stay_id, charttime, note_id;
