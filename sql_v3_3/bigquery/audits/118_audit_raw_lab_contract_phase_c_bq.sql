-- MIMIC-IV 3.1 BigQuery Phase-C laboratory contract audit.
-- Scope: immutable 5,549-stay audit cohort; aggregate output only.
-- This query creates no table and returns no patient- or specimen-level identifier.

WITH
lab_contracts AS (
  SELECT *
  FROM UNNEST([
    STRUCT('base_excess' AS concept, 50802 AS itemid, 'Base Excess' AS expected_label,
      'Blood' AS expected_fluid, 'Blood Gas' AS expected_category,
      'exact_allowlist' AS unit_policy, ['mEq/L'] AS allowed_units),
    STRUCT('lactate', 50813, 'Lactate', 'Blood', 'Blood Gas',
      'exact_allowlist', ['mmol/L']),
    STRUCT('ph', 50820, 'pH', 'Blood', 'Blood Gas',
      'exact_allowlist', ['units']),
    STRUCT('bicarbonate', 50882, 'Bicarbonate', 'Blood', 'Chemistry',
      'exact_allowlist', ['mEq/L']),
    STRUCT('creatinine', 50912, 'Creatinine', 'Blood', 'Chemistry',
      'exact_allowlist', ['mg/dL']),
    STRUCT('ntprobnp', 50963, 'NTproBNP', 'Blood', 'Chemistry',
      'exact_allowlist', ['pg/mL']),
    STRUCT('potassium', 50971, 'Potassium', 'Blood', 'Chemistry',
      'exact_allowlist', ['mEq/L']),
    STRUCT('sodium', 50983, 'Sodium', 'Blood', 'Chemistry',
      'exact_allowlist', ['mEq/L']),
    STRUCT('troponin_t', 51003, 'Troponin T', 'Blood', 'Chemistry',
      'exact_allowlist', ['ng/mL']),
    STRUCT('bun', 51006, 'Urea Nitrogen', 'Blood', 'Chemistry',
      'exact_allowlist', ['mg/dL']),
    STRUCT('hemoglobin', 51222, 'Hemoglobin', 'Blood', 'Hematology',
      'exact_allowlist', ['g/dL']),
    STRUCT('inr', 51237, 'INR(PT)', 'Blood', 'Hematology',
      'dimensionless_null', ARRAY<STRING>[]),
    STRUCT('platelet', 51265, 'Platelet Count', 'Blood', 'Hematology',
      'exact_allowlist', ['K/uL']),
    STRUCT('wbc', 51301, 'White Blood Cells', 'Blood', 'Hematology',
      'exact_allowlist', ['K/uL'])
  ])
),
known_quarantine AS (
  SELECT *
  FROM UNNEST([
    STRUCT('bun' AS concept, 50851 AS itemid, 'Urea Nitrogen, Ascites' AS expected_label,
      'Ascites' AS expected_fluid, 'Chemistry' AS expected_category,
      'wrong_fluid_ascites' AS reason_code),
    STRUCT('bun', 51045, 'Urea Nitrogen, Body Fluid', 'Other Body Fluid', 'Chemistry',
      'wrong_fluid_other_body_fluid'),
    STRUCT('bun', 51104, 'Urea Nitrogen, Urine', 'Urine', 'Chemistry',
      'wrong_fluid_urine'),
    STRUCT('bun', 51804, 'Urea Nitrogen, CSF', 'Cerebrospinal Fluid', 'Chemistry',
      'wrong_fluid_csf'),
    STRUCT('bun', 51825, 'Urea Nitrogen, Joint Fluid', 'Joint Fluid', 'Chemistry',
      'wrong_fluid_joint_fluid'),
    STRUCT('bun', 51842, 'Bun', 'Other Body Fluid', 'Chemistry',
      'wrong_fluid_other_body_fluid'),
    STRUCT('bun', 51922, 'Urea Nitrogen, Pleural', 'Pleural', 'Chemistry',
      'wrong_fluid_pleural'),
    STRUCT('bun', 51951, 'Urea Nitrogen, Stool', 'Stool', 'Chemistry',
      'wrong_fluid_stool')
  ])
),
dictionary_contract AS (
  SELECT
    c.concept,
    c.itemid,
    CASE
      WHEN di.itemid IS NULL THEN 'missing_dictionary_itemid'
      WHEN LOWER(TRIM(di.label)) != LOWER(TRIM(c.expected_label))
        OR LOWER(TRIM(di.fluid)) != LOWER(TRIM(c.expected_fluid))
        OR LOWER(TRIM(di.category)) != LOWER(TRIM(c.expected_category))
        THEN 'dictionary_contract_mismatch'
      ELSE 'matched'
    END AS dictionary_status
  FROM lab_contracts c
  LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di USING (itemid)
),
quarantine_dictionary AS (
  SELECT
    q.concept,
    q.itemid,
    q.reason_code,
    CASE
      WHEN di.itemid IS NULL THEN 'missing_dictionary_itemid'
      WHEN LOWER(TRIM(di.label)) != LOWER(TRIM(q.expected_label))
        OR LOWER(TRIM(di.fluid)) != LOWER(TRIM(q.expected_fluid))
        OR LOWER(TRIM(di.category)) != LOWER(TRIM(q.expected_category))
        THEN 'dictionary_contract_mismatch'
      ELSE 'matched'
    END AS dictionary_status
  FROM known_quarantine q
  LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di USING (itemid)
),
cohort AS (
  SELECT
    CAST(stay_id AS INT64) AS stay_id,
    CAST(subject_id AS INT64) AS subject_id,
    CAST(hadm_id AS INT64) AS hadm_id,
    CAST(admittime AS DATETIME) AS admittime,
    CAST(intime AS DATETIME) AS t0,
    DATETIME_ADD(CAST(intime AS DATETIME), INTERVAL 12 HOUR) AS t12
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_lab_audit_cohort_snapshot_20260918`
),
cohort_counts AS (
  SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT stay_id) AS distinct_stay_count,
    COUNTIF(admittime > t0) AS invalid_boundary_count,
    COUNTIF(subject_id IS NULL OR hadm_id IS NULL OR stay_id IS NULL) AS missing_key_count
  FROM cohort
),
scoped_items AS (
  SELECT concept, itemid FROM lab_contracts
  UNION ALL
  SELECT concept, itemid FROM known_quarantine
),
raw_preclassified AS (
  SELECT
    c.stay_id,
    le.labevent_id,
    le.specimen_id,
    le.itemid,
    si.concept,
    di.label,
    di.fluid,
    di.category,
    le.charttime,
    le.storetime,
    GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) AS availability_time,
    c.t12,
    le.value,
    le.valuenum,
    le.valueuom,
    lc.expected_label,
    lc.expected_fluid,
    lc.expected_category,
    lc.unit_policy,
    lc.allowed_units,
    kq.reason_code AS known_quarantine_reason,
    COUNT(*) OVER (PARTITION BY le.labevent_id) AS episode_match_count,
    COUNTIF(le.specimen_id IS NOT NULL) OVER (
      PARTITION BY c.stay_id, le.specimen_id, le.itemid
    ) AS specimen_itemid_count,
    CASE
      WHEN REGEXP_CONTAINS(TRIM(le.value),
        r'^>=?\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$')
        THEN 'right_censored'
      WHEN REGEXP_CONTAINS(TRIM(le.value),
        r'^<=?\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$')
        THEN 'left_censored'
      WHEN REGEXP_CONTAINS(TRIM(le.value),
        r'^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*(?:-|to)\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$')
        THEN 'interval_censored'
      WHEN le.valuenum IS NOT NULL THEN 'exact_numeric'
      WHEN NULLIF(TRIM(le.value), '') IS NULL THEN 'missing_result'
      ELSE 'non_numeric_text'
    END AS result_class
  FROM cohort c
  JOIN `physionet-data.mimiciv_3_1_hosp.labevents` le
    ON le.subject_id = c.subject_id
   AND le.hadm_id = c.hadm_id
   AND le.charttime >= c.t0
   AND le.charttime < c.t12
  JOIN scoped_items si USING (itemid)
  JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di USING (itemid)
  LEFT JOIN lab_contracts lc USING (itemid)
  LEFT JOIN known_quarantine kq USING (itemid)
),
classified AS (
  SELECT
    *,
    CASE
      WHEN episode_match_count > 1 THEN 'ambiguous_episode_join'
      WHEN known_quarantine_reason IS NOT NULL THEN known_quarantine_reason
      WHEN expected_label IS NULL THEN 'unregistered_itemid'
      WHEN LOWER(TRIM(label)) != LOWER(TRIM(expected_label)) THEN 'label_mismatch'
      WHEN LOWER(TRIM(fluid)) != LOWER(TRIM(expected_fluid)) THEN 'fluid_mismatch'
      WHEN LOWER(TRIM(category)) != LOWER(TRIM(expected_category)) THEN 'category_mismatch'
      WHEN charttime IS NULL THEN 'missing_charttime'
      WHEN storetime IS NOT NULL AND storetime < charttime THEN 'storetime_before_charttime'
      WHEN availability_time >= t12 THEN 'available_after_landmark'
      WHEN specimen_id IS NULL THEN 'missing_specimen_id'
      WHEN specimen_itemid_count > 1 THEN 'duplicate_specimen_itemid'
      WHEN unit_policy = 'dimensionless_null'
        AND valueuom IS NOT NULL AND TRIM(valueuom) != '' THEN 'unknown_unit'
      WHEN unit_policy = 'exact_allowlist'
        AND (valueuom IS NULL OR TRIM(valueuom) = '') THEN 'unknown_unit'
      WHEN unit_policy = 'exact_allowlist' AND NOT EXISTS (
        SELECT 1
        FROM UNNEST(allowed_units) AS allowed_unit
        WHERE LOWER(TRIM(valueuom)) = LOWER(TRIM(allowed_unit))
      ) THEN 'unknown_unit'
      ELSE NULL
    END AS quarantine_reason
  FROM raw_preclassified
),
dictionary_output AS (
  SELECT
    'dictionary' AS check_group,
    concept,
    CONCAT('allow:', dictionary_status) AS reason_code,
    COUNT(*) AS row_count
  FROM dictionary_contract
  GROUP BY concept, dictionary_status
  UNION ALL
  SELECT
    'dictionary',
    concept,
    CONCAT('quarantine:', dictionary_status),
    COUNT(*)
  FROM quarantine_dictionary
  GROUP BY concept, dictionary_status
),
classification_output AS (
  SELECT
    'classification' AS check_group,
    concept,
    COALESCE(quarantine_reason, 'eligible') AS reason_code,
    COUNT(*) AS row_count
  FROM classified
  GROUP BY concept, reason_code
),
result_output AS (
  SELECT
    'result_class' AS check_group,
    concept,
    result_class AS reason_code,
    COUNT(*) AS row_count
  FROM classified
  GROUP BY concept, reason_code
),
hard_gate_output AS (
  SELECT 'hard_gate' AS check_group, 'all' AS concept,
    'active_dictionary_mismatch' AS reason_code,
    COUNTIF(dictionary_status != 'matched') AS row_count
  FROM dictionary_contract
  UNION ALL
  SELECT 'hard_gate', 'all', 'quarantine_dictionary_mismatch',
    COUNTIF(dictionary_status != 'matched')
  FROM quarantine_dictionary
  UNION ALL
  SELECT 'hard_gate', 'all', 'cohort_duplicate_stay_rows',
    row_count - distinct_stay_count
  FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'cohort_invalid_boundary', invalid_boundary_count
  FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'cohort_missing_key', missing_key_count
  FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'eligible_wrong_contract', COUNTIF(
    quarantine_reason IS NULL AND (
      expected_label IS NULL
      OR LOWER(TRIM(label)) != LOWER(TRIM(expected_label))
      OR LOWER(TRIM(fluid)) != LOWER(TRIM(expected_fluid))
      OR LOWER(TRIM(category)) != LOWER(TRIM(expected_category))
    )
  )
  FROM classified
  UNION ALL
  SELECT 'hard_gate', 'all', 'eligible_time_violation', COUNTIF(
    quarantine_reason IS NULL AND (
      charttime IS NULL OR (storetime IS NOT NULL AND storetime < charttime)
      OR availability_time >= t12
    )
  )
  FROM classified
  UNION ALL
  SELECT 'hard_gate', 'all', 'eligible_specimen_violation', COUNTIF(
    quarantine_reason IS NULL AND (specimen_id IS NULL OR specimen_itemid_count > 1)
  )
  FROM classified
  UNION ALL
  SELECT 'hard_gate', 'bun', 'bun_eligible_nonblood_or_wrong_item', COUNTIF(
    concept = 'bun' AND quarantine_reason IS NULL
    AND (itemid != 51006 OR fluid != 'Blood' OR category != 'Chemistry' OR valueuom != 'mg/dL')
  )
  FROM classified
)

-- FINAL_AGGREGATE_OUTPUT
SELECT check_group, concept, reason_code, row_count FROM dictionary_output
UNION ALL
SELECT check_group, concept, reason_code, row_count FROM classification_output
UNION ALL
SELECT check_group, concept, reason_code, row_count FROM result_output
UNION ALL
SELECT check_group, concept, reason_code, row_count FROM hard_gate_output
ORDER BY check_group, concept, reason_code;
