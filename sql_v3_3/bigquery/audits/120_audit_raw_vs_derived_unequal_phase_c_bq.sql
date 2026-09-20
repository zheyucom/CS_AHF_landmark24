-- BigQuery Standard SQL: aggregate-only second-layer decomposition of
-- raw-vs-derived stay-level max differences. No patient-level output.
-- Official selection logic is limited to mimic-code chemistry.sql and bg.sql
-- predicates needed for BUN, creatinine, lactate, and same-specimen PO2.

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
  LEFT JOIN lab_contracts lc ON lc.itemid = le.itemid
  LEFT JOIN known_quarantine kq ON kq.itemid = le.itemid
  LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di ON di.itemid = le.itemid
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
      AND range_status = 'in_analysis_range' AS is_eligible_raw,
    contract_status = 'contract_ok'
      AND availability_status = 'late_result'
      AND specimen_id IS NOT NULL
      AND specimen_itemid_count = 1
      AND result_class = 'exact_numeric'
      AND range_status = 'in_analysis_range' AS is_late_contract_raw
  FROM classified
),
raw_stay AS (
  SELECT
    stay_id,
    concept,
    MAX(IF(is_eligible_raw, valuenum, NULL)) AS raw_max
  FROM flagged
  GROUP BY stay_id, concept
  HAVING COUNTIF(is_eligible_raw) > 0
),
raw_max_events AS (
  SELECT f.*
  FROM flagged f
  JOIN raw_stay s USING (stay_id, concept)
  WHERE f.is_eligible_raw
    AND ABS(f.valuenum - s.raw_max) <= 1e-9
),
po2_by_specimen AS (
  SELECT
    c.stay_id,
    le.specimen_id,
    COUNTIF(le.valuenum IS NOT NULL) > 0 AS has_po2
  FROM cohort c
  JOIN `physionet-data.mimiciv_3_1_hosp.labevents` le
    ON le.subject_id = c.subject_id
   AND le.hadm_id = c.hadm_id
   AND le.charttime >= c.t0
   AND le.charttime < c.t12
   AND le.itemid = 50821
  WHERE le.specimen_id IS NOT NULL
  GROUP BY c.stay_id, le.specimen_id
),
official_itemid_raw_set AS (
  SELECT f.*
  FROM flagged f
  WHERE f.specimen_id IS NOT NULL
    AND f.valuenum IS NOT NULL
    AND (
      (f.itemid = 51006 AND f.valuenum > 0 AND f.valuenum <= 300)
      OR (f.itemid = 50912 AND f.valuenum > 0 AND f.valuenum <= 150)
      OR (f.itemid = 50813 AND f.valuenum <= 10000)
    )
),
reconstructed_lactate_derived_events AS (
  SELECT
    o.stay_id,
    o.specimen_id,
    MAX(o.valuenum) AS lactate
  FROM official_itemid_raw_set o
  JOIN po2_by_specimen p USING (stay_id, specimen_id)
  WHERE o.concept = 'lactate'
    AND p.has_po2
  GROUP BY o.stay_id, o.specimen_id
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
  SELECT stay_id, concept, MAX(derived_value) AS derived_max
  FROM derived_rows
  GROUP BY stay_id, concept
),
unequal_base AS (
  SELECT
    r.stay_id,
    r.concept,
    r.raw_max,
    d.derived_max,
    ABS(r.raw_max - d.derived_max) AS abs_diff,
    CASE WHEN r.raw_max > d.derived_max THEN 'raw_higher' ELSE 'derived_higher' END AS direction
  FROM raw_stay r
  JOIN derived_stay d USING (stay_id, concept)
  WHERE ABS(r.raw_max - d.derived_max) > 1e-9
),
raw_value_membership AS (
  SELECT
    u.stay_id,
    u.concept,
    COUNTIF(f.is_eligible_raw AND ABS(f.valuenum - u.derived_max) <= 1e-9) > 0
      AS derived_max_in_eligible_raw_set,
    COUNTIF(f.is_late_contract_raw AND ABS(f.valuenum - u.derived_max) <= 1e-9) > 0
      AS derived_max_in_late_raw_set,
    COUNTIF(
      f.valuenum IS NOT NULL
      AND NOT f.is_eligible_raw
      AND NOT f.is_late_contract_raw
      AND ABS(f.valuenum - u.derived_max) <= 1e-9
    ) > 0 AS derived_max_in_other_quarantine_raw_set,
    COUNTIF(f.valuenum IS NOT NULL AND ABS(f.valuenum - u.derived_max) <= 1e-9) > 0
      AS derived_max_in_any_raw_set
  FROM unequal_base u
  LEFT JOIN flagged f USING (stay_id, concept)
  GROUP BY u.stay_id, u.concept
),
derived_value_membership AS (
  SELECT
    u.stay_id,
    u.concept,
    COUNTIF(ABS(d.derived_value - u.raw_max) <= 1e-9) > 0 AS raw_max_in_derived_event_set
  FROM unequal_base u
  LEFT JOIN derived_rows d USING (stay_id, concept)
  GROUP BY u.stay_id, u.concept
),
derived_specimen_set AS (
  SELECT DISTINCT stay_id, concept, specimen_id
  FROM derived_rows
  WHERE concept IN ('bun', 'creatinine') AND specimen_id IS NOT NULL
  UNION DISTINCT
  SELECT stay_id, 'lactate' AS concept, specimen_id
  FROM reconstructed_lactate_derived_events
),
raw_max_context_membership AS (
  SELECT
    u.stay_id,
    u.concept,
    COUNTIF(u.concept = 'lactate' AND COALESCE(p.has_po2, FALSE)) > 0
      AS raw_max_lactate_has_po2,
    COUNTIF(ds.specimen_id IS NOT NULL) > 0 AS raw_max_specimen_in_derived
  FROM unequal_base u
  LEFT JOIN raw_max_events r USING (stay_id, concept)
  LEFT JOIN po2_by_specimen p USING (stay_id, specimen_id)
  LEFT JOIN derived_specimen_set ds USING (stay_id, concept, specimen_id)
  GROUP BY u.stay_id, u.concept
),
unequal_features AS (
  SELECT
    u.*,
    rv.derived_max_in_eligible_raw_set,
    rv.derived_max_in_late_raw_set,
    rv.derived_max_in_other_quarantine_raw_set,
    rv.derived_max_in_any_raw_set,
    dv.raw_max_in_derived_event_set,
    rc.raw_max_lactate_has_po2,
    rc.raw_max_specimen_in_derived
  FROM unequal_base u
  JOIN raw_value_membership rv USING (stay_id, concept)
  JOIN derived_value_membership dv USING (stay_id, concept)
  JOIN raw_max_context_membership rc USING (stay_id, concept)
),
classified_unequal AS (
  SELECT
    *,
    CASE
      WHEN abs_diff <= 1e-9 THEN 'precision_only'
      WHEN direction = 'derived_higher' AND derived_max_in_late_raw_set
        THEN 'derived_higher_matches_late_raw'
      WHEN direction = 'derived_higher' AND derived_max_in_other_quarantine_raw_set
        THEN 'derived_higher_matches_other_quarantine_raw'
      WHEN direction = 'derived_higher' AND NOT derived_max_in_any_raw_set
        THEN 'derived_higher_not_found_in_raw'
      WHEN direction = 'raw_higher' AND concept = 'lactate' AND NOT raw_max_lactate_has_po2
        THEN 'raw_higher_lactate_specimen_missing_po2'
      WHEN direction = 'raw_higher' AND NOT raw_max_specimen_in_derived
        THEN 'raw_higher_specimen_absent_from_derived'
      WHEN direction = 'raw_higher' AND derived_max_in_eligible_raw_set
        THEN 'raw_higher_derived_value_in_eligible_raw_set'
      WHEN direction = 'raw_higher' THEN 'raw_higher_unresolved'
      ELSE 'derived_higher_unresolved'
    END AS cause_code
  FROM unequal_features
),
cause_catalog AS (
  SELECT * FROM UNNEST([
    STRUCT('precision_only' AS direction, 'precision_only' AS cause_code),
    STRUCT('derived_higher', 'derived_higher_matches_late_raw'),
    STRUCT('derived_higher', 'derived_higher_matches_other_quarantine_raw'),
    STRUCT('derived_higher', 'derived_higher_not_found_in_raw'),
    STRUCT('raw_higher', 'raw_higher_lactate_specimen_missing_po2'),
    STRUCT('raw_higher', 'raw_higher_specimen_absent_from_derived'),
    STRUCT('raw_higher', 'raw_higher_derived_value_in_eligible_raw_set'),
    STRUCT('raw_higher', 'raw_higher_unresolved'),
    STRUCT('derived_higher', 'derived_higher_unresolved')
  ])
),
membership_catalog AS (
  SELECT cause_code FROM UNNEST([
    'derived_max_in_eligible_raw_set',
    'derived_max_in_late_raw_set',
    'derived_max_in_any_raw_set',
    'raw_max_in_derived_event_set'
  ]) AS cause_code
),
reference_output AS (
  SELECT
    'reference_total' AS check_group,
    c.concept,
    'all' AS direction,
    'both_unequal' AS cause_code,
    COUNT(u.stay_id) AS stay_count,
    AVG(u.abs_diff) AS mean_abs_diff,
    MAX(u.abs_diff) AS max_abs_diff
  FROM lab_contracts c
  LEFT JOIN unequal_features u USING (concept)
  GROUP BY c.concept
),
exclusive_output AS (
  SELECT
    'exclusive_cause' AS check_group,
    c.concept,
    cc.direction,
    cc.cause_code,
    COUNT(u.stay_id) AS stay_count,
    AVG(u.abs_diff) AS mean_abs_diff,
    MAX(u.abs_diff) AS max_abs_diff
  FROM lab_contracts c
  CROSS JOIN cause_catalog cc
  LEFT JOIN classified_unequal u
    ON u.concept = c.concept AND u.cause_code = cc.cause_code
  GROUP BY c.concept, cc.direction, cc.cause_code
),
membership_output AS (
  SELECT
    'membership' AS check_group,
    c.concept,
    'all' AS direction,
    mc.cause_code,
    COUNTIF(
      u.stay_id IS NOT NULL AND CASE mc.cause_code
        WHEN 'derived_max_in_eligible_raw_set' THEN u.derived_max_in_eligible_raw_set
        WHEN 'derived_max_in_late_raw_set' THEN u.derived_max_in_late_raw_set
        WHEN 'derived_max_in_any_raw_set' THEN u.derived_max_in_any_raw_set
        WHEN 'raw_max_in_derived_event_set' THEN u.raw_max_in_derived_event_set
        ELSE FALSE
      END
    ) AS stay_count,
    AVG(IF(
      CASE mc.cause_code
        WHEN 'derived_max_in_eligible_raw_set' THEN u.derived_max_in_eligible_raw_set
        WHEN 'derived_max_in_late_raw_set' THEN u.derived_max_in_late_raw_set
        WHEN 'derived_max_in_any_raw_set' THEN u.derived_max_in_any_raw_set
        WHEN 'raw_max_in_derived_event_set' THEN u.raw_max_in_derived_event_set
        ELSE FALSE
      END,
      u.abs_diff,
      NULL
    )) AS mean_abs_diff,
    MAX(IF(
      CASE mc.cause_code
        WHEN 'derived_max_in_eligible_raw_set' THEN u.derived_max_in_eligible_raw_set
        WHEN 'derived_max_in_late_raw_set' THEN u.derived_max_in_late_raw_set
        WHEN 'derived_max_in_any_raw_set' THEN u.derived_max_in_any_raw_set
        WHEN 'raw_max_in_derived_event_set' THEN u.raw_max_in_derived_event_set
        ELSE FALSE
      END,
      u.abs_diff,
      NULL
    )) AS max_abs_diff
  FROM lab_contracts c
  CROSS JOIN membership_catalog mc
  LEFT JOIN unequal_features u USING (concept)
  GROUP BY c.concept, mc.cause_code
),
hard_gate_output AS (
  SELECT 'hard_gate' AS check_group, 'all' AS concept, 'not_applicable' AS direction,
    'active_dictionary_mismatch' AS cause_code,
    COUNTIF(dictionary_status != 'matched') AS stay_count,
    CAST(NULL AS FLOAT64) AS mean_abs_diff, CAST(NULL AS FLOAT64) AS max_abs_diff
  FROM dictionary_contract
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'quarantine_dictionary_mismatch',
    COUNTIF(dictionary_status != 'matched'), NULL, NULL
  FROM quarantine_dictionary
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'cohort_duplicate_stay_rows',
    row_count - distinct_stay_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'cohort_invalid_boundary',
    invalid_boundary_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'cohort_missing_key',
    missing_key_count, NULL, NULL FROM cohort_counts
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'eligible_wrong_contract',
    COUNTIF(is_eligible_raw AND is_wrong_contract), NULL, NULL FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'eligible_time_violation',
    COUNTIF(is_eligible_raw AND (is_late_result OR is_storetime_inversion)), NULL, NULL FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'all', 'not_applicable', 'eligible_specimen_violation',
    COUNTIF(is_eligible_raw AND (is_missing_specimen OR is_duplicate_specimen)), NULL, NULL FROM flagged
  UNION ALL
  SELECT 'hard_gate', 'bun', 'not_applicable', 'bun_eligible_nonblood_or_wrong_item',
    COUNTIF(concept = 'bun' AND is_eligible_raw
      AND (itemid != 51006 OR fluid != 'Blood' OR category != 'Chemistry' OR valueuom != 'mg/dL')),
    NULL, NULL
  FROM flagged
)

-- FINAL_AGGREGATE_OUTPUT
SELECT check_group, concept, direction, cause_code, stay_count, mean_abs_diff, max_abs_diff
FROM reference_output
UNION ALL
SELECT check_group, concept, direction, cause_code, stay_count, mean_abs_diff, max_abs_diff
FROM exclusive_output
UNION ALL
SELECT check_group, concept, direction, cause_code, stay_count, mean_abs_diff, max_abs_diff
FROM membership_output
UNION ALL
SELECT check_group, concept, direction, cause_code, stay_count, mean_abs_diff, max_abs_diff
FROM hard_gate_output
ORDER BY check_group, concept, direction, cause_code;
