-- BigQuery Standard SQL: aggregate-only raw-vs-derived cause stratification.
-- Scope: immutable 5,549-stay audit cohort; no patient-level output.
-- BUN/creatinine use stay + specimen_id; lactate uses stay + charttime because
-- the public derived bg table does not expose specimen_id or storetime.

WITH
lab_contracts AS (
  SELECT * FROM UNNEST([
    STRUCT('lactate' AS concept, 50813 AS itemid, 'Lactate' AS expected_label,
      'Blood' AS expected_fluid, 'Blood Gas' AS expected_category, 'mmol/L' AS expected_unit,
      CAST(NULL AS FLOAT64) AS lower_bound, CAST(NULL AS FLOAT64) AS upper_bound),
    STRUCT('creatinine', 50912, 'Creatinine', 'Blood', 'Chemistry', 'mg/dL',
      CAST(0 AS FLOAT64), CAST(150 AS FLOAT64)),
    STRUCT('bun', 51006, 'Urea Nitrogen', 'Blood', 'Chemistry', 'mg/dL',
      CAST(0 AS FLOAT64), CAST(300 AS FLOAT64))
  ])
),
known_quarantine AS (
  SELECT * FROM UNNEST([
    STRUCT('bun' AS concept, 50851 AS itemid, 'Urea Nitrogen, Ascites' AS expected_label,
      'Ascites' AS expected_fluid, 'Chemistry' AS expected_category, 'mg/dL' AS expected_unit,
      'wrong_fluid_ascites' AS reason_code),
    STRUCT('bun', 51045, 'Urea Nitrogen, Body Fluid', 'Other Body Fluid', 'Chemistry', 'mg/dL',
      'wrong_fluid_other_body_fluid'),
    STRUCT('bun', 51104, 'Urea Nitrogen, Urine', 'Urine', 'Chemistry', 'mg/dL',
      'wrong_fluid_urine'),
    STRUCT('bun', 51804, 'Urea Nitrogen, CSF', 'Cerebrospinal Fluid', 'Chemistry', 'mg/dL',
      'wrong_fluid_csf'),
    STRUCT('bun', 51825, 'Urea Nitrogen, Joint Fluid', 'Joint Fluid', 'Chemistry', 'mg/dL',
      'wrong_fluid_joint_fluid'),
    STRUCT('bun', 51842, 'Bun', 'Other Body Fluid', 'Chemistry', 'mg/dL',
      'wrong_fluid_other_body_fluid'),
    STRUCT('bun', 51922, 'Urea Nitrogen, Pleural', 'Pleural', 'Chemistry', 'mg/dL',
      'wrong_fluid_pleural'),
    STRUCT('bun', 51951, 'Urea Nitrogen, Stool', 'Stool', 'Chemistry', 'mg/dL',
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
raw_rows AS (
  SELECT
    c.stay_id,
    c.subject_id,
    c.hadm_id,
    c.t0,
    c.t12,
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
    le.value,
    le.valuenum,
    le.valueuom,
    lc.expected_label,
    lc.expected_fluid,
    lc.expected_category,
    lc.expected_unit,
    lc.lower_bound,
    lc.upper_bound,
    kq.reason_code AS known_quarantine_reason,
    COUNT(*) OVER (PARTITION BY c.stay_id, le.specimen_id, le.itemid) AS specimen_itemid_count,
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
  LEFT JOIN lab_contracts lc USING (itemid)
  LEFT JOIN known_quarantine kq USING (itemid)
  LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di USING (itemid)
),
classified AS (
  SELECT
    *,
    CASE
      WHEN known_quarantine_reason IS NOT NULL THEN 'wrong_contract'
      WHEN expected_label IS NULL OR label IS NULL THEN 'wrong_contract'
      WHEN LOWER(TRIM(label)) != LOWER(TRIM(expected_label))
        OR LOWER(TRIM(fluid)) != LOWER(TRIM(expected_fluid))
        OR LOWER(TRIM(category)) != LOWER(TRIM(expected_category))
        OR LOWER(TRIM(valueuom)) != LOWER(TRIM(expected_unit))
        THEN 'wrong_contract'
      ELSE 'contract_ok'
    END AS contract_status,
    CASE
      WHEN storetime IS NOT NULL AND storetime < charttime THEN 'storetime_before_charttime'
      WHEN availability_time >= t12 THEN 'late_result'
      ELSE 'on_time'
    END AS availability_status,
    CASE
      WHEN result_class != 'exact_numeric' THEN 'not_applicable'
      WHEN lower_bound IS NOT NULL AND valuenum <= lower_bound THEN 'out_of_analysis_range'
      WHEN upper_bound IS NOT NULL AND valuenum > upper_bound THEN 'out_of_analysis_range'
      ELSE 'in_analysis_range'
    END AS range_status
  FROM raw_rows
),
flagged AS (
  SELECT
    *,
    contract_status = 'wrong_contract' AS is_wrong_contract,
    availability_status = 'late_result' AS is_late_result,
    availability_status = 'storetime_before_charttime' AS is_storetime_inversion,
    specimen_id IS NULL AS is_missing_specimen,
    specimen_id IS NOT NULL AND specimen_itemid_count > 1 AS is_duplicate_specimen,
    result_class != 'exact_numeric' AS is_censored_or_non_numeric,
    range_status = 'out_of_analysis_range' AS is_out_of_analysis_range,
    contract_status = 'contract_ok'
      AND availability_status = 'on_time'
      AND specimen_id IS NOT NULL
      AND specimen_itemid_count = 1
      AND result_class = 'exact_numeric'
      AND range_status = 'in_analysis_range' AS is_eligible_raw
  FROM classified
),
raw_stay AS (
  SELECT
    stay_id,
    concept,
    COUNTIF(is_eligible_raw) AS raw_eligible_event_n,
    COUNTIF(is_late_result) AS late_event_n,
    COUNTIF(contract_status = 'contract_ok' AND is_late_result) AS contract_late_event_n,
    COUNTIF(is_storetime_inversion) AS storetime_inversion_event_n,
    COUNTIF(is_censored_or_non_numeric) AS censored_or_non_numeric_event_n,
    COUNTIF(contract_status = 'contract_ok' AND is_censored_or_non_numeric)
      AS contract_censored_or_non_numeric_event_n,
    COUNTIF(is_out_of_analysis_range) AS out_of_range_event_n,
    COUNTIF(contract_status = 'contract_ok' AND is_out_of_analysis_range)
      AS contract_out_of_range_event_n,
    COUNTIF(is_wrong_contract) AS wrong_contract_event_n,
    COUNTIF(is_missing_specimen) AS missing_specimen_event_n,
    COUNTIF(is_duplicate_specimen) AS duplicate_specimen_event_n,
    MAX(IF(is_eligible_raw, valuenum, NULL)) AS raw_max,
    COUNTIF(is_eligible_raw) > 0 AS has_raw_eligible
  FROM flagged
  GROUP BY stay_id, concept
),
derived_rows AS (
  SELECT
    c.stay_id,
    'bun' AS concept,
    d.specimen_id,
    d.charttime,
    d.bun AS derived_value
  FROM cohort c
  JOIN `physionet-data.mimiciv_3_1_derived.chemistry` d
    ON d.subject_id = c.subject_id
   AND d.hadm_id = c.hadm_id
   AND d.charttime >= c.t0
   AND d.charttime < c.t12
  WHERE d.bun IS NOT NULL
  UNION ALL
  SELECT
    c.stay_id,
    'creatinine',
    d.specimen_id,
    d.charttime,
    d.creatinine
  FROM cohort c
  JOIN `physionet-data.mimiciv_3_1_derived.chemistry` d
    ON d.subject_id = c.subject_id
   AND d.hadm_id = c.hadm_id
   AND d.charttime >= c.t0
   AND d.charttime < c.t12
  WHERE d.creatinine IS NOT NULL
  UNION ALL
  SELECT
    c.stay_id,
    'lactate',
    CAST(NULL AS INT64),
    d.charttime,
    d.lactate
  FROM cohort c
  JOIN `physionet-data.mimiciv_3_1_derived.bg` d
    ON d.subject_id = c.subject_id
   AND d.hadm_id = c.hadm_id
   AND d.charttime >= c.t0
   AND d.charttime < c.t12
  WHERE d.lactate IS NOT NULL
),
derived_stay AS (
  SELECT
    stay_id,
    concept,
    COUNT(*) AS derived_event_n,
    MAX(derived_value) AS derived_max
  FROM derived_rows
  GROUP BY stay_id, concept
),
paired AS (
  SELECT
    COALESCE(r.stay_id, d.stay_id) AS stay_id,
    COALESCE(r.concept, d.concept) AS concept,
    r.raw_eligible_event_n,
    r.late_event_n,
    r.contract_late_event_n,
    r.storetime_inversion_event_n,
    r.censored_or_non_numeric_event_n,
    r.contract_censored_or_non_numeric_event_n,
    r.out_of_range_event_n,
    r.contract_out_of_range_event_n,
    r.wrong_contract_event_n,
    r.missing_specimen_event_n,
    r.duplicate_specimen_event_n,
    r.raw_max,
    d.derived_event_n,
    d.derived_max,
    CASE
      WHEN r.has_raw_eligible AND d.derived_max IS NOT NULL THEN 'both'
      WHEN r.has_raw_eligible THEN 'raw_only'
      WHEN d.derived_max IS NOT NULL THEN 'derived_only'
      ELSE 'neither'
    END AS coverage_status
  FROM raw_stay r
  FULL OUTER JOIN derived_stay d
    USING (stay_id, concept)
),
raw_event_cause_output AS (
  SELECT 'raw_event_cause' AS check_group, concept, 'event' AS metric,
    'wrong_contract' AS cause_code, COUNT(DISTINCT IF(is_wrong_contract, stay_id, NULL)) AS stay_count,
    COUNTIF(is_wrong_contract) AS event_count,
    CAST(NULL AS FLOAT64) AS mean_abs_diff, CAST(NULL AS FLOAT64) AS max_abs_diff
  FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'late_result', COUNT(DISTINCT IF(is_late_result, stay_id, NULL)),
    COUNTIF(is_late_result), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'late_result_contract_ok',
    COUNT(DISTINCT IF(contract_status = 'contract_ok' AND is_late_result, stay_id, NULL)),
    COUNTIF(contract_status = 'contract_ok' AND is_late_result), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'storetime_before_charttime',
    COUNT(DISTINCT IF(is_storetime_inversion, stay_id, NULL)),
    COUNTIF(is_storetime_inversion), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'missing_specimen_id',
    COUNT(DISTINCT IF(is_missing_specimen, stay_id, NULL)),
    COUNTIF(is_missing_specimen), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'duplicate_specimen_itemid',
    COUNT(DISTINCT IF(is_duplicate_specimen, stay_id, NULL)),
    COUNTIF(is_duplicate_specimen), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'censored_or_non_numeric',
    COUNT(DISTINCT IF(is_censored_or_non_numeric, stay_id, NULL)),
    COUNTIF(is_censored_or_non_numeric), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'censored_or_non_numeric_contract_ok',
    COUNT(DISTINCT IF(contract_status = 'contract_ok' AND is_censored_or_non_numeric, stay_id, NULL)),
    COUNTIF(contract_status = 'contract_ok' AND is_censored_or_non_numeric), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'out_of_analysis_range',
    COUNT(DISTINCT IF(is_out_of_analysis_range, stay_id, NULL)),
    COUNTIF(is_out_of_analysis_range), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'out_of_analysis_range_contract_ok',
    COUNT(DISTINCT IF(contract_status = 'contract_ok' AND is_out_of_analysis_range, stay_id, NULL)),
    COUNTIF(contract_status = 'contract_ok' AND is_out_of_analysis_range), NULL, NULL FROM flagged GROUP BY concept
  UNION ALL
  SELECT 'raw_event_cause', concept, 'event', 'eligible_raw',
    COUNT(DISTINCT IF(is_eligible_raw, stay_id, NULL)),
    COUNTIF(is_eligible_raw), NULL, NULL FROM flagged GROUP BY concept
),
coverage_output AS (
  SELECT
    'feature_coverage' AS check_group,
    concept,
    'max' AS metric,
    coverage_status AS cause_code,
    COUNT(*) AS stay_count,
    SUM(COALESCE(raw_eligible_event_n, 0) + COALESCE(derived_event_n, 0)) AS event_count,
    AVG(IF(coverage_status = 'both', ABS(raw_max - derived_max), NULL)) AS mean_abs_diff,
    MAX(IF(coverage_status = 'both', ABS(raw_max - derived_max), NULL)) AS max_abs_diff
  FROM paired
  WHERE coverage_status != 'neither'
  GROUP BY concept, coverage_status
),
difference_output AS (
  SELECT
    'difference_cause' AS check_group,
    concept,
    'max' AS metric,
    CASE
      WHEN coverage_status = 'raw_only' THEN 'raw_only_derived_missing'
      WHEN coverage_status = 'derived_only' AND COALESCE(contract_late_event_n, 0) > 0
        THEN 'derived_only_with_late_raw'
      WHEN coverage_status = 'derived_only' AND COALESCE(contract_censored_or_non_numeric_event_n, 0) > 0
        THEN 'derived_only_with_censored_or_non_numeric_raw'
      WHEN coverage_status = 'derived_only' AND COALESCE(contract_out_of_range_event_n, 0) > 0
        THEN 'derived_only_with_out_of_range_raw'
      WHEN coverage_status = 'derived_only' AND COALESCE(wrong_contract_event_n, 0) > 0
        THEN 'derived_only_with_wrong_contract_raw'
      WHEN coverage_status = 'derived_only' AND COALESCE(duplicate_specimen_event_n, 0) > 0
        THEN 'derived_only_with_duplicate_raw'
      WHEN coverage_status = 'derived_only' THEN 'derived_only_no_matching_raw_eligible'
      WHEN coverage_status = 'both' AND ABS(raw_max - derived_max) > 1e-9 THEN 'both_unequal'
      WHEN coverage_status = 'both' THEN 'both_equal'
      ELSE 'unclassified'
    END AS cause_code,
    COUNT(*) AS stay_count,
    SUM(COALESCE(raw_eligible_event_n, 0) + COALESCE(derived_event_n, 0)) AS event_count,
    AVG(IF(coverage_status = 'both', ABS(raw_max - derived_max), NULL)) AS mean_abs_diff,
    MAX(IF(coverage_status = 'both', ABS(raw_max - derived_max), NULL)) AS max_abs_diff
  FROM paired
  WHERE coverage_status != 'neither'
  GROUP BY concept, cause_code
),
dictionary_output AS (
  SELECT 'dictionary' AS check_group, concept, 'itemid' AS metric,
    CONCAT('allow:', dictionary_status) AS cause_code,
    0 AS stay_count, 1 AS event_count,
    CAST(NULL AS FLOAT64) AS mean_abs_diff, CAST(NULL AS FLOAT64) AS max_abs_diff
  FROM dictionary_contract
  UNION ALL
  SELECT 'dictionary', concept, 'itemid', CONCAT('quarantine:', dictionary_status), 0, 1, NULL, NULL
  FROM quarantine_dictionary
),
hard_gate_output AS (
  SELECT 'hard_gate' AS check_group, 'all' AS concept, 'contract' AS metric,
    'active_dictionary_mismatch' AS cause_code,
    COUNTIF(dictionary_status != 'matched') AS stay_count,
    COUNTIF(dictionary_status != 'matched') AS event_count,
    CAST(NULL AS FLOAT64) AS mean_abs_diff,
    CAST(NULL AS FLOAT64) AS max_abs_diff
  FROM dictionary_contract
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'quarantine_dictionary_mismatch',
    COUNTIF(dictionary_status != 'matched'), COUNTIF(dictionary_status != 'matched'), NULL, NULL
  FROM quarantine_dictionary
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'cohort_duplicate_stay_rows',
    row_count - distinct_stay_count, row_count - distinct_stay_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'cohort_invalid_boundary', invalid_boundary_count,
    invalid_boundary_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'cohort_missing_key', missing_key_count,
    missing_key_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'eligible_wrong_contract',
    COUNTIF(is_eligible_raw AND is_wrong_contract), COUNTIF(is_eligible_raw AND is_wrong_contract), NULL, NULL
  FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'eligible_time_violation',
    COUNTIF(is_eligible_raw AND (is_late_result OR is_storetime_inversion)),
    COUNTIF(is_eligible_raw AND (is_late_result OR is_storetime_inversion)), NULL, NULL
  FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'all', 'contract', 'eligible_specimen_violation',
    COUNTIF(is_eligible_raw AND (is_missing_specimen OR is_duplicate_specimen)),
    COUNTIF(is_eligible_raw AND (is_missing_specimen OR is_duplicate_specimen)), NULL, NULL
  FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'bun', 'contract', 'bun_eligible_nonblood_or_wrong_item',
    COUNTIF(concept = 'bun' AND is_eligible_raw AND (itemid != 51006 OR fluid != 'Blood' OR category != 'Chemistry' OR valueuom != 'mg/dL')),
    COUNTIF(concept = 'bun' AND is_eligible_raw AND (itemid != 51006 OR fluid != 'Blood' OR category != 'Chemistry' OR valueuom != 'mg/dL')),
    NULL, NULL
  FROM flagged
)

-- FINAL_AGGREGATE_OUTPUT
SELECT check_group, concept, metric, cause_code, stay_count, event_count, mean_abs_diff, max_abs_diff
FROM dictionary_output
UNION ALL
SELECT check_group, concept, metric, cause_code, stay_count, event_count, mean_abs_diff, max_abs_diff
FROM raw_event_cause_output
UNION ALL
SELECT check_group, concept, metric, cause_code, stay_count, event_count, mean_abs_diff, max_abs_diff
FROM coverage_output
UNION ALL
SELECT check_group, concept, metric, cause_code, stay_count, event_count, mean_abs_diff, max_abs_diff
FROM difference_output
UNION ALL
SELECT check_group, concept, metric, cause_code, stay_count, event_count, mean_abs_diff, max_abs_diff
FROM hard_gate_output
ORDER BY check_group, concept, metric, cause_code;
