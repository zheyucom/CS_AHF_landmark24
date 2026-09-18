-- 112: T12-window echocardiography result audit template.
--
-- This is intentionally source-agnostic. Replace the SOURCE_* fields and the
-- table name only after `bq show` confirms the local schema. Do not run this
-- template unchanged. It must not infer an abnormal echo from a procedure
-- code, an order, or an isolated normal/unknown result.
--
-- Required source mapping:
--   stay_id, subject_id, hadm_id
--   echo_type (TTE/TEE/POCUS/bedside cardiac ultrasound)
--   exam_time
--   result_available_time
--   result_status
--   lvef_value (nullable), report_text or structured result fields
--
-- Strict inclusion requires all three states to be true:
--   performed, result available before T12, and abnormality support.
-- A draft abnormality flag below is for QC only and requires clinical review.

DECLARE source_table STRING DEFAULT 'YOUR_PROJECT.YOUR_DATASET.YOUR_ECHO_RESULT_TABLE';

-- BigQuery cannot parameterize a table identifier in a static query. Replace
-- the placeholder in the next statement after confirming the schema.
CREATE OR REPLACE TABLE `YOUR_BILLING_PROJECT.ahf_work.echo_result_audit_v1` AS
WITH candidate AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    TIMESTAMP(intime) AS t0,
    TIMESTAMP_ADD(TIMESTAMP(intime), INTERVAL 12 HOUR) AS t12
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates`
  WHERE TIMESTAMP(admittime) <= TIMESTAMP(intime)
),
source_mapped AS (
  SELECT
    CAST(SOURCE_STAY_ID AS INT64) AS stay_id,
    CAST(SOURCE_SUBJECT_ID AS INT64) AS subject_id,
    CAST(SOURCE_HADM_ID AS INT64) AS hadm_id,
    UPPER(TRIM(CAST(SOURCE_ECHO_TYPE AS STRING))) AS echo_type,
    TIMESTAMP(SOURCE_EXAM_TIME) AS exam_time,
    TIMESTAMP(SOURCE_RESULT_AVAILABLE_TIME) AS result_available_time,
    LOWER(CAST(SOURCE_RESULT_STATUS AS STRING)) AS result_status,
    SAFE_CAST(SOURCE_LVEF_VALUE AS FLOAT64) AS lvef_value,
    LOWER(CAST(SOURCE_REPORT_TEXT AS STRING)) AS report_text
  FROM `YOUR_PROJECT.YOUR_DATASET.YOUR_ECHO_RESULT_TABLE`
),
screened AS (
  SELECT
    c.subject_id,
    c.hadm_id,
    c.stay_id,
    c.t0,
    c.t12,
    s.echo_type,
    s.exam_time,
    s.result_available_time,
    s.result_status,
    s.lvef_value,
    s.report_text,
    1 AS echo_performed_flag,
    IF(
      s.result_available_time IS NOT NULL
      AND s.result_available_time < c.t12
      AND COALESCE(s.result_status, '') NOT IN ('cancelled', 'canceled', 'void', 'not performed'),
      1, 0
    ) AS echo_result_available_flag,
    -- Screening only: confirm this flag against the source report and a
    -- blinded clinical sample before using it for cohort inclusion.
    IF(
      (s.lvef_value IS NOT NULL AND s.lvef_value < 50)
      OR REGEXP_CONTAINS(
        s.report_text,
        r'(reduced|mildly reduced|moderately reduced|severely reduced|dysfunction|hypokinesis|akinesis|elevated filling pressure|diastolic dysfunction|severe .*valvular|elevated pulmonary artery pressure|right ventricular enlargement|right ventricular dysfunction)'
      ),
      1, 0
    ) AS echo_abnormal_support_draft_flag
  FROM candidate c
  JOIN source_mapped s
    ON s.stay_id = c.stay_id
   AND s.echo_type IN ('TTE', 'TEE', 'POCUS', 'BEDSIDE POCUS', 'BEDSIDE CARDIAC ULTRASOUND')
   AND s.exam_time >= TIMESTAMP_SUB(c.t0, INTERVAL 24 HOUR)
   AND s.exam_time < c.t12
),
patient_level AS (
  SELECT
    subject_id,
    hadm_id,
    stay_id,
    COUNT(*) AS echo_exam_n,
    MAX(echo_performed_flag) AS echo_performed_pre12_flag,
    MAX(echo_result_available_flag) AS echo_result_available_pre12_flag,
    MAX(echo_abnormal_support_draft_flag) AS echo_abnormal_support_draft_pre12_flag,
    MIN(exam_time) AS first_echo_exam_time,
    MIN(result_available_time) AS first_result_available_time,
    ARRAY_AGG(STRUCT(
      echo_type,
      exam_time,
      result_available_time,
      result_status,
      lvef_value,
      echo_result_available_flag,
      echo_abnormal_support_draft_flag
    ) ORDER BY exam_time LIMIT 1)[OFFSET(0)] AS first_echo_record
  FROM screened
  GROUP BY subject_id, hadm_id, stay_id
)
SELECT
  p.*,
  IF(
    echo_performed_pre12_flag = 1
    AND echo_result_available_pre12_flag = 1
    AND echo_abnormal_support_draft_pre12_flag = 1,
    1, 0
  ) AS strict_echo_supported_draft_flag,
  '112_template; draft abnormality screen; clinical adjudication required' AS rule_version
FROM patient_level p;

-- Required QC checks after replacing the source mapping:
-- 1. one row per stay_id;
-- 2. exam_time in [T0-24 h, T12);
-- 3. result_available_time < T12;
-- 4. procedure-only, result-unavailable, normal/negative, indeterminate and
--    abnormal-support states reported separately;
-- 5. at least 20-50 blinded clinical records reviewed before freezing the
--    abnormality rule.
