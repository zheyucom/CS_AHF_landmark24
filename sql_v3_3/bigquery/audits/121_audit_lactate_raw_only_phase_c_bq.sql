-- BigQuery Standard SQL: aggregate-only decomposition of lactate raw-only stays.
-- Rebuild only the official bg specimen fields needed for lactate inclusion and
-- MAX(charttime) window placement. No patient-level output.

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
      'Ascites' AS expected_fluid, 'Chemistry' AS expected_category, 'mg/dL' AS expected_unit),
    STRUCT('bun', 51045, 'Urea Nitrogen, Body Fluid', 'Other Body Fluid', 'Chemistry', 'mg/dL'),
    STRUCT('bun', 51104, 'Urea Nitrogen, Urine', 'Urine', 'Chemistry', 'mg/dL'),
    STRUCT('bun', 51804, 'Urea Nitrogen, CSF', 'Cerebrospinal Fluid', 'Chemistry', 'mg/dL'),
    STRUCT('bun', 51825, 'Urea Nitrogen, Joint Fluid', 'Joint Fluid', 'Chemistry', 'mg/dL'),
    STRUCT('bun', 51842, 'Bun', 'Other Body Fluid', 'Chemistry', 'mg/dL'),
    STRUCT('bun', 51922, 'Urea Nitrogen, Pleural', 'Pleural', 'Chemistry', 'mg/dL'),
    STRUCT('bun', 51951, 'Urea Nitrogen, Stool', 'Stool', 'Chemistry', 'mg/dL')
  ])
),
bg_itemids AS (
  SELECT itemid FROM UNNEST([
    52033, 50801, 50802, 50803, 50804, 50805, 50806, 50807, 50808,
    50809, 50810, 50811, 50813, 50814, 50815, 50816, 50817, 50818,
    50819, 50820, 50821, 50822, 50823, 50824, 50825
  ]) AS itemid
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
    kq.itemid IS NOT NULL AS is_known_quarantine,
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
  LEFT JOIN lab_contracts lc ON lc.itemid = le.itemid
  LEFT JOIN known_quarantine kq ON kq.itemid = le.itemid
  LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di ON di.itemid = le.itemid
),
classified AS (
  SELECT
    *,
    CASE
      WHEN is_known_quarantine THEN 'wrong_contract'
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
raw_lactate_stay AS (
  SELECT stay_id, MAX(valuenum) AS raw_max
  FROM flagged
  WHERE concept = 'lactate' AND is_eligible_raw
  GROUP BY stay_id
),
derived_lactate_stay AS (
  SELECT c.stay_id, MAX(d.lactate) AS derived_max
  FROM cohort c
  JOIN `physionet-data.mimiciv_3_1_derived.bg` d
    ON d.subject_id = c.subject_id
   AND d.hadm_id = c.hadm_id
   AND d.charttime >= c.t0
   AND d.charttime < c.t12
  WHERE d.lactate IS NOT NULL
  GROUP BY c.stay_id
),
raw_only AS (
  SELECT
    c.stay_id,
    c.subject_id,
    c.hadm_id,
    c.t0,
    c.t12,
    r.raw_max
  FROM raw_lactate_stay r
  JOIN cohort c USING (stay_id)
  LEFT JOIN derived_lactate_stay d USING (stay_id)
  WHERE d.stay_id IS NULL
),
raw_only_lactate_specimens AS (
  SELECT DISTINCT
    r.stay_id,
    r.subject_id,
    r.hadm_id,
    r.t0,
    r.t12,
    r.raw_max,
    f.specimen_id
  FROM raw_only r
  JOIN flagged f USING (stay_id)
  WHERE f.concept = 'lactate'
    AND f.specimen_id IS NOT NULL
    AND f.valuenum IS NOT NULL
),
raw_max_specimens AS (
  SELECT DISTINCT r.stay_id, f.specimen_id
  FROM raw_only r
  JOIN flagged f USING (stay_id)
  WHERE f.concept = 'lactate'
    AND f.is_eligible_raw
    AND ABS(f.valuenum - r.raw_max) <= 1e-9
),
bg_specimen_rebuild AS (
  SELECT
    k.stay_id,
    k.subject_id,
    k.hadm_id,
    k.t0,
    k.t12,
    k.raw_max,
    k.specimen_id,
    MAX(le.charttime) AS bg_charttime,
    MAX(le.storetime) AS bg_storetime,
    MAX(IF(le.itemid = 50813 AND le.valuenum <= 10000, le.valuenum, NULL))
      AS official_lactate,
    MAX(IF(le.itemid = 50821, le.valuenum, NULL)) AS po2
  FROM raw_only_lactate_specimens k
  JOIN `physionet-data.mimiciv_3_1_hosp.labevents` le
    ON le.subject_id = k.subject_id
   AND le.hadm_id = k.hadm_id
   AND le.specimen_id = k.specimen_id
  JOIN bg_itemids bi ON bi.itemid = le.itemid
  GROUP BY
    k.stay_id, k.subject_id, k.hadm_id, k.t0, k.t12, k.raw_max, k.specimen_id
),
specimen_evidence AS (
  SELECT
    b.stay_id,
    b.t0,
    b.t12,
    b.raw_max,
    b.specimen_id,
    b.bg_charttime,
    b.official_lactate,
    b.po2,
    COUNTIF(d.lactate IS NOT NULL) > 0 AS matches_public_bg_any_time
  FROM bg_specimen_rebuild b
  LEFT JOIN `physionet-data.mimiciv_3_1_derived.bg` d
    ON d.subject_id = b.subject_id
   AND d.hadm_id = b.hadm_id
   AND d.charttime = b.bg_charttime
   AND ABS(d.lactate - b.official_lactate) <= 1e-9
  GROUP BY
    b.stay_id, b.t0, b.t12, b.raw_max, b.specimen_id,
    b.bg_charttime, b.official_lactate, b.po2
),
stay_features AS (
  SELECT
    r.stay_id,
    r.raw_max,
    COUNTIF(m.specimen_id IS NOT NULL AND s.po2 IS NOT NULL) > 0 AS raw_max_specimen_has_po2,
    COUNTIF(s.po2 IS NOT NULL) > 0 AS any_lactate_specimen_has_po2,
    COUNTIF(s.po2 IS NOT NULL AND s.official_lactate IS NOT NULL) > 0
      AS any_official_bg_candidate,
    COUNTIF(
      s.po2 IS NOT NULL AND s.official_lactate IS NOT NULL
      AND s.bg_charttime >= s.t0 AND s.bg_charttime < s.t12
    ) > 0 AS official_candidate_charttime_in_window,
    COUNTIF(
      s.po2 IS NOT NULL AND s.official_lactate IS NOT NULL
      AND s.bg_charttime >= s.t12
    ) > 0 AS official_candidate_charttime_after_t12,
    COUNTIF(
      s.po2 IS NOT NULL AND s.official_lactate IS NOT NULL
      AND s.matches_public_bg_any_time
    ) > 0 AS official_candidate_matches_public_bg_any_time,
    COUNTIF(
      s.po2 IS NOT NULL AND s.official_lactate IS NOT NULL
      AND s.bg_charttime >= s.t0 AND s.bg_charttime < s.t12
      AND s.matches_public_bg_any_time
    ) AS public_bg_in_window_match_count
  FROM raw_only r
  JOIN specimen_evidence s USING (stay_id)
  LEFT JOIN raw_max_specimens m
    ON m.stay_id = s.stay_id AND m.specimen_id = s.specimen_id
  GROUP BY r.stay_id, r.raw_max
),
classified_raw_only AS (
  SELECT
    *,
    CASE
      WHEN NOT any_lactate_specimen_has_po2
        THEN 'no_lactate_specimen_has_po2'
      WHEN NOT any_official_bg_candidate
        THEN 'po2_present_all_lactate_values_outside_official_range'
      WHEN official_candidate_charttime_in_window
        AND NOT official_candidate_matches_public_bg_any_time
        THEN 'official_candidate_in_window_absent_from_public_bg'
      WHEN NOT official_candidate_charttime_in_window
        AND official_candidate_charttime_after_t12
        THEN 'official_candidates_all_after_t12'
      ELSE 'raw_only_unresolved'
    END AS cause_code
  FROM stay_features
),
cause_catalog AS (
  SELECT cause_code FROM UNNEST([
    'no_lactate_specimen_has_po2',
    'po2_present_all_lactate_values_outside_official_range',
    'official_candidate_in_window_absent_from_public_bg',
    'official_candidates_all_after_t12',
    'raw_only_unresolved'
  ]) AS cause_code
),
membership_catalog AS (
  SELECT cause_code FROM UNNEST([
    'raw_max_specimen_has_po2',
    'any_lactate_specimen_has_po2',
    'any_official_bg_candidate',
    'official_candidate_charttime_in_window',
    'official_candidate_charttime_after_t12',
    'official_candidate_matches_public_bg_any_time'
  ]) AS cause_code
),
reference_output AS (
  SELECT
    'reference_total' AS check_group,
    'lactate' AS concept,
    'raw_only' AS cause_code,
    COUNT(*) AS stay_count,
    AVG(raw_max) AS mean_raw_max,
    MAX(raw_max) AS max_raw_max
  FROM stay_features
),
exclusive_output AS (
  SELECT
    'exclusive_cause' AS check_group,
    'lactate' AS concept,
    c.cause_code,
    COUNT(r.stay_id) AS stay_count,
    AVG(r.raw_max) AS mean_raw_max,
    MAX(r.raw_max) AS max_raw_max
  FROM cause_catalog c
  LEFT JOIN classified_raw_only r USING (cause_code)
  GROUP BY c.cause_code
),
membership_output AS (
  SELECT
    'membership' AS check_group,
    'lactate' AS concept,
    m.cause_code,
    COUNTIF(
      CASE m.cause_code
        WHEN 'raw_max_specimen_has_po2' THEN r.raw_max_specimen_has_po2
        WHEN 'any_lactate_specimen_has_po2' THEN r.any_lactate_specimen_has_po2
        WHEN 'any_official_bg_candidate' THEN r.any_official_bg_candidate
        WHEN 'official_candidate_charttime_in_window' THEN r.official_candidate_charttime_in_window
        WHEN 'official_candidate_charttime_after_t12' THEN r.official_candidate_charttime_after_t12
        WHEN 'official_candidate_matches_public_bg_any_time'
          THEN r.official_candidate_matches_public_bg_any_time
        ELSE FALSE
      END
    ) AS stay_count,
    AVG(IF(
      CASE m.cause_code
        WHEN 'raw_max_specimen_has_po2' THEN r.raw_max_specimen_has_po2
        WHEN 'any_lactate_specimen_has_po2' THEN r.any_lactate_specimen_has_po2
        WHEN 'any_official_bg_candidate' THEN r.any_official_bg_candidate
        WHEN 'official_candidate_charttime_in_window' THEN r.official_candidate_charttime_in_window
        WHEN 'official_candidate_charttime_after_t12' THEN r.official_candidate_charttime_after_t12
        WHEN 'official_candidate_matches_public_bg_any_time'
          THEN r.official_candidate_matches_public_bg_any_time
        ELSE FALSE
      END,
      r.raw_max,
      NULL
    )) AS mean_raw_max,
    MAX(IF(
      CASE m.cause_code
        WHEN 'raw_max_specimen_has_po2' THEN r.raw_max_specimen_has_po2
        WHEN 'any_lactate_specimen_has_po2' THEN r.any_lactate_specimen_has_po2
        WHEN 'any_official_bg_candidate' THEN r.any_official_bg_candidate
        WHEN 'official_candidate_charttime_in_window' THEN r.official_candidate_charttime_in_window
        WHEN 'official_candidate_charttime_after_t12' THEN r.official_candidate_charttime_after_t12
        WHEN 'official_candidate_matches_public_bg_any_time'
          THEN r.official_candidate_matches_public_bg_any_time
        ELSE FALSE
      END,
      r.raw_max,
      NULL
    )) AS max_raw_max
  FROM membership_catalog m
  CROSS JOIN stay_features r
  GROUP BY m.cause_code
),
hard_gate_output AS (
  SELECT 'hard_gate' AS check_group, 'all' AS concept,
    'active_dictionary_mismatch' AS cause_code,
    COUNTIF(dictionary_status != 'matched') AS stay_count,
    CAST(NULL AS FLOAT64) AS mean_raw_max, CAST(NULL AS FLOAT64) AS max_raw_max
  FROM dictionary_contract
  UNION ALL
  SELECT 'hard_gate', 'all', 'quarantine_dictionary_mismatch',
    COUNTIF(dictionary_status != 'matched'), NULL, NULL FROM quarantine_dictionary
  UNION ALL
  SELECT 'hard_gate', 'all', 'cohort_duplicate_stay_rows',
    row_count - distinct_stay_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'cohort_invalid_boundary', invalid_boundary_count, NULL, NULL
  FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'cohort_missing_key', missing_key_count, NULL, NULL
  FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'eligible_wrong_contract',
    COUNTIF(is_eligible_raw AND is_wrong_contract), NULL, NULL FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'all', 'eligible_time_violation',
    COUNTIF(is_eligible_raw AND (is_late_result OR is_storetime_inversion)), NULL, NULL
  FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'all', 'eligible_specimen_violation',
    COUNTIF(is_eligible_raw AND (is_missing_specimen OR is_duplicate_specimen)), NULL, NULL
  FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'bun', 'bun_eligible_nonblood_or_wrong_item',
    COUNTIF(concept = 'bun' AND is_eligible_raw
      AND (itemid != 51006 OR fluid != 'Blood' OR category != 'Chemistry' OR valueuom != 'mg/dL')),
    NULL, NULL
  FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'lactate', 'raw_only_public_bg_in_window_match',
    SUM(public_bg_in_window_match_count), NULL, NULL
  FROM stay_features
)

-- FINAL_AGGREGATE_OUTPUT
SELECT check_group, concept, cause_code, stay_count, mean_raw_max, max_raw_max
FROM reference_output
UNION ALL
SELECT check_group, concept, cause_code, stay_count, mean_raw_max, max_raw_max
FROM exclusive_output
UNION ALL
SELECT check_group, concept, cause_code, stay_count, mean_raw_max, max_raw_max
FROM membership_output
UNION ALL
SELECT check_group, concept, cause_code, stay_count, mean_raw_max, max_raw_max
FROM hard_gate_output
ORDER BY check_group, concept, cause_code;
