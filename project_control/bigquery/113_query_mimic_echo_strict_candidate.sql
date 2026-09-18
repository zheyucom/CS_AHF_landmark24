-- 113: MIMIC-IV-Echo structured-result audit for the T12 DHF candidate cohort.
--
-- Source verified against the official MIMIC-IV-Echo v1.0.1 description:
--   physionet-data.mimiciv_echo.structured_measurement
-- The source is long format and contains one row per measurement. The linked
-- echo_study_list adds study_datetime and the associated Echo-note charttime.
-- This permits a separate audit of examination timing and note availability,
-- although note_charttime is still not an independently audited sign-off time.
--
-- This query keeps every candidate stay in the output. A missing Echo row is
-- not a negative echo. The draft abnormality flag is for sampling/QC only;
-- it must not be used for final inclusion before clinical adjudication.

CREATE OR REPLACE TABLE `YOUR_BILLING_PROJECT.ahf_work.echo_result_audit_v1` AS
WITH candidate AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    CAST(admittime AS DATETIME) AS admittime,
    CAST(intime AS DATETIME) AS t0,
    DATETIME_ADD(CAST(intime AS DATETIME), INTERVAL 12 HOUR) AS t12
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates`
  WHERE CAST(admittime AS DATETIME) <= CAST(intime AS DATETIME)
),
study_links AS (
  SELECT DISTINCT
    CAST(subject_id AS INT64) AS subject_id,
    CAST(study_id AS INT64) AS study_id,
    CAST(measurement_id AS INT64) AS measurement_id,
    CAST(study_datetime AS DATETIME) AS study_datetime,
    CAST(note_id AS STRING) AS note_id,
    CAST(note_charttime AS DATETIME) AS note_charttime
  FROM `physionet-data.mimiciv_echo.echo_study_list`
),
echo_measurements AS (
  SELECT
    CAST(subject_id AS INT64) AS subject_id,
    CAST(measurement_id AS INT64) AS measurement_id,
    CAST(measurement_datetime AS DATETIME) AS measurement_datetime,
    UPPER(TRIM(CAST(test_type AS STRING))) AS test_type,
    LOWER(TRIM(CAST(measurement AS STRING))) AS measurement_name,
    LOWER(TRIM(CAST(measurement_description AS STRING))) AS measurement_description,
    TRIM(CAST(result AS STRING)) AS result_text,
    TRIM(CAST(unit AS STRING)) AS unit
  FROM `physionet-data.mimiciv_echo.structured_measurement`
  WHERE UPPER(TRIM(CAST(test_type AS STRING))) IN ('TTE', 'TEE')
),
time_compliant AS (
  SELECT
    c.stay_id,
    c.subject_id,
    c.hadm_id,
    c.t0,
    c.t12,
    s.study_id,
    s.study_datetime,
    s.note_id,
    s.note_charttime,
    e.measurement_id,
    e.measurement_datetime,
    e.test_type,
    e.measurement_name,
    e.measurement_description,
    e.result_text,
    e.unit,
    SAFE_CAST(
      REGEXP_EXTRACT(e.result_text, r'[-+]?[0-9]+(?:\.[0-9]+)?') AS FLOAT64
    ) AS first_numeric_result,
    1 AS echo_result_row_flag,
    IF(e.result_text IS NOT NULL AND TRIM(e.result_text) != '', 1, 0)
      AS echo_result_nonempty_row_flag,
    -- Screening domains only. This intentionally does not call the result
    -- clinically abnormal unless the result itself contains an abnormal
    -- descriptor or a target numeric threshold is crossed.
    IF(
      (
        REGEXP_CONTAINS(
          CONCAT(' ', e.measurement_name, ' ', e.measurement_description, ' '),
          r'(lvef|ejection fraction|lv systolic|left ventricular systolic|global systolic|systolic function)'
        )
        AND (
          SAFE_CAST(REGEXP_EXTRACT(e.result_text, r'[-+]?[0-9]+(?:\.[0-9]+)?') AS FLOAT64) < 50
          OR REGEXP_CONTAINS(
            e.result_text,
            r'(reduced|mildly reduced|moderately reduced|severely reduced|depressed|dysfunction|hypokinetic|hypokinesis|akinetic|akinesis)'
          )
        )
      )
      OR (
        REGEXP_CONTAINS(
          CONCAT(' ', e.measurement_name, ' ', e.measurement_description, ' '),
          r'(diastolic|filling pressure|e/e|left atrial|left atrium|lv hypertroph|left ventricular hypertroph|impaired relaxation)'
        )
        AND REGEXP_CONTAINS(
          e.result_text,
          r'(abnormal|elevated|increased|grade i|grade ii|grade iii|impaired|dysfunction|hypertroph|enlarg|dilated|reduced)'
        )
      )
      OR (
        REGEXP_CONTAINS(
          CONCAT(' ', e.measurement_name, ' ', e.measurement_description, ' '),
          r'(right ventricular|rv systolic|tricuspid annular|tapse|pulmonary artery|pulmonary pressure|rvsp|pasp|pulmonary hypertension|valvular|mitral|aortic|tricuspid|pulmonic)'
        )
        AND REGEXP_CONTAINS(
          e.result_text,
          r'(abnormal|elevated|increased|reduced|decreased|dysfunction|enlarg|dilated|regurg|stenos|moderate|severe|hypertension|hypokinetic|hypokinesis)'
        )
      ),
      1, 0
    ) AS echo_abnormal_support_draft_flag
  FROM candidate c
  JOIN study_links s
    ON s.subject_id = c.subject_id
   AND s.study_datetime >= DATETIME_SUB(c.t0, INTERVAL 24 HOUR)
   AND s.study_datetime < c.t12
  JOIN echo_measurements e
    ON e.subject_id = s.subject_id
   AND e.measurement_id = s.measurement_id
),
patient_level AS (
  SELECT
    c.stay_id,
    c.subject_id,
    c.hadm_id,
    c.t0,
    c.t12,
    COUNT(t.measurement_id) AS echo_measurement_row_n,
    COUNT(DISTINCT t.study_id) AS echo_study_n,
    MAX(IF(t.measurement_id IS NOT NULL, 1, 0)) AS echo_performed_structured_flag,
    MAX(COALESCE(t.echo_result_nonempty_row_flag, 0)) AS echo_result_recorded_flag,
    MAX(IF(t.note_charttime IS NOT NULL AND t.note_charttime < c.t12, 1, 0))
      AS echo_note_available_by_t12_proxy_flag,
    COUNTIF(t.echo_result_nonempty_row_flag = 0)
      AS echo_result_empty_row_n,
    MAX(COALESCE(t.echo_abnormal_support_draft_flag, 0))
      AS echo_abnormal_support_draft_flag,
    COUNTIF(t.echo_abnormal_support_draft_flag = 1)
      AS echo_abnormal_support_measurement_n,
    MIN(t.measurement_datetime) AS first_echo_measurement_time,
    MAX(t.measurement_datetime) AS last_echo_measurement_time,
    MIN(t.study_datetime) AS first_echo_study_time,
    MAX(t.study_datetime) AS last_echo_study_time,
    MIN(t.note_charttime) AS first_echo_note_charttime,
    MAX(t.note_charttime) AS last_echo_note_charttime,
    ARRAY_AGG(
      IF(
        t.measurement_id IS NULL,
        NULL,
        STRUCT(
          t.measurement_id AS measurement_id,
          t.study_id AS study_id,
          t.study_datetime AS study_datetime,
          t.measurement_datetime AS measurement_datetime,
          t.note_id AS note_id,
          t.note_charttime AS note_charttime,
          t.test_type AS test_type,
          t.measurement_name AS measurement,
          t.measurement_description AS measurement_description,
          t.result_text AS result,
          t.unit AS unit,
          t.first_numeric_result AS first_numeric_result,
          t.echo_abnormal_support_draft_flag AS abnormal_support_draft_flag
        )
      ) IGNORE NULLS
      ORDER BY t.measurement_datetime
      LIMIT 25
    ) AS echo_evidence_examples
  FROM candidate c
  LEFT JOIN time_compliant t
    ON t.stay_id = c.stay_id
  GROUP BY c.stay_id, c.subject_id, c.hadm_id, c.t0, c.t12
)
SELECT
  p.*,
  IF(
    p.echo_performed_structured_flag = 1
    AND p.echo_result_recorded_flag = 1
    AND p.echo_note_available_by_t12_proxy_flag = 1
    AND p.echo_abnormal_support_draft_flag = 1,
    1, 0
  ) AS strict_echo_supported_draft_flag,
  '113_mimiciv_echo_v1.0.1; TTE_TEE; study_datetime_exam; note_charttime_availability_proxy; draft_screen_only' AS rule_version,
  'note_charttime is a report-availability proxy, not an independently audited signing timestamp' AS result_time_limitation
FROM patient_level p;

-- Required post-query QC:
-- 1. one output row per stay_id;
-- 2. all study_datetime values satisfy [T0-24 h, T12);
-- 3. report TTE and TEE separately, and do not include stress echo;
-- 4. report no structured row, result-empty, normal/negative,
--    indeterminate and draft-abnormal-support states separately;
-- 5. review at least 20-50 candidate studies against source records before
--    freezing echo_abnormal_support_flag;
-- 6. link the resulting subject_id/time records to the same hospitalization
--    and ICU stay; subject_id alone is not an admission/stay link.
