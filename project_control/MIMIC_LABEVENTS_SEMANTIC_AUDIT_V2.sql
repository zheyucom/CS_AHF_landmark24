-- MIMIC-IV 3.1 / BigQuery laboratory semantic and availability audit v2
-- execution_status: not_run until this script is executed successfully
-- Scope: current project audit frame, [ICU T0, T12), aggregate output only.
-- Candidate discovery is intentionally isolated in MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql.
-- No label regex is allowed to create a formal laboratory feature in this script.

DECLARE audit_rule_version STRING DEFAULT
  'mimic_lab_semantic_audit_v2_20260917';

CREATE TEMP TABLE lab_contracts AS
SELECT *
FROM UNNEST([
  STRUCT(
    'bun' AS concept, 51006 AS itemid, 'Urea Nitrogen' AS expected_label,
    'Blood' AS expected_fluid, 'Chemistry' AS expected_category,
    ['mg/dL'] AS allowed_units, 'lab-bun-blood-v1' AS rule_id
  ),
  STRUCT(
    'lactate' AS concept, 50813 AS itemid, 'Lactate' AS expected_label,
    'Blood' AS expected_fluid, 'Blood Gas' AS expected_category,
    ['mmol/L'] AS allowed_units, 'lab-lactate-blood-gas-v1' AS rule_id
  ),
  STRUCT(
    'creatinine' AS concept, 50912 AS itemid, 'Creatinine' AS expected_label,
    'Blood' AS expected_fluid, 'Chemistry' AS expected_category,
    ['mg/dL'] AS allowed_units, 'project-creatinine-blood-v1' AS rule_id
  ),
  STRUCT(
    'ph' AS concept, 50820 AS itemid, 'pH' AS expected_label,
    'Blood' AS expected_fluid, 'Blood Gas' AS expected_category,
    ['units'] AS allowed_units, 'project-ph-blood-v1' AS rule_id
  ),
  STRUCT(
    'ntprobnp' AS concept, 50963 AS itemid, 'NTproBNP' AS expected_label,
    'Blood' AS expected_fluid, 'Chemistry' AS expected_category,
    ['pg/mL'] AS allowed_units, 'project-ntprobnp-blood-v1' AS rule_id
  ),
  STRUCT(
    'troponin_t' AS concept, 51003 AS itemid, 'Troponin T' AS expected_label,
    'Blood' AS expected_fluid, 'Chemistry' AS expected_category,
    ['ng/mL'] AS allowed_units, 'project-troponin-t-blood-v1' AS rule_id
  )
]);

-- These are semantically wrong for blood BUN even when the label contains
-- “Urea Nitrogen” or “Bun”. They are retained only to quantify contamination.
CREATE TEMP TABLE known_quarantine AS
SELECT *
FROM UNNEST([
  STRUCT('bun' AS concept, 51104 AS itemid, 'wrong_fluid_urine' AS reason_code),
  STRUCT('bun' AS concept, 51045 AS itemid, 'wrong_fluid_other_body_fluid' AS reason_code),
  STRUCT('bun' AS concept, 50851 AS itemid, 'wrong_fluid_ascites' AS reason_code),
  STRUCT('bun' AS concept, 51804 AS itemid, 'wrong_fluid_csf' AS reason_code),
  STRUCT('bun' AS concept, 51825 AS itemid, 'wrong_fluid_joint_fluid' AS reason_code),
  STRUCT('bun' AS concept, 51842 AS itemid, 'wrong_fluid_other_body_fluid' AS reason_code),
  STRUCT('bun' AS concept, 51922 AS itemid, 'wrong_fluid_pleural' AS reason_code),
  STRUCT('bun' AS concept, 51951 AS itemid, 'wrong_fluid_stool' AS reason_code)
]);

CREATE TEMP TABLE dictionary_contract AS
SELECT
  c.*,
  di.itemid AS dictionary_itemid,
  di.label AS observed_label,
  di.fluid AS observed_fluid,
  di.category AS observed_category,
  CASE
    WHEN di.itemid IS NULL THEN 'missing_dictionary_itemid'
    WHEN LOWER(TRIM(di.label)) != LOWER(TRIM(c.expected_label))
      OR LOWER(TRIM(di.fluid)) != LOWER(TRIM(c.expected_fluid))
      OR LOWER(TRIM(di.category)) != LOWER(TRIM(c.expected_category))
      THEN 'dictionary_contract_mismatch'
    ELSE 'matched'
  END AS dictionary_status
FROM lab_contracts c
LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di
  USING (itemid);

ASSERT (
  SELECT COUNTIF(dictionary_status != 'matched')
  FROM dictionary_contract
) = 0 AS 'Active laboratory contract does not match MIMIC-IV d_labitems; stop and review.';

CREATE TEMP TABLE cohort AS
SELECT
  CAST(stay_id AS INT64) AS stay_id,
  CAST(subject_id AS INT64) AS subject_id,
  CAST(hadm_id AS INT64) AS hadm_id,
  CAST(intime AS DATETIME) AS t0,
  DATETIME_ADD(CAST(intime AS DATETIME), INTERVAL 12 HOUR) AS t12
FROM `project-9386bb9f-de39-47eb-886.ahf_work.dhf_lab_audit_cohort_snapshot_20260918`
WHERE CAST(admittime AS DATETIME) <= CAST(intime AS DATETIME);

ASSERT (
  SELECT COUNT(*) = COUNT(DISTINCT stay_id)
  FROM cohort
) AS 'Audit cohort must contain one row per stay_id.';

CREATE TEMP TABLE scoped_items AS
SELECT concept, itemid
FROM lab_contracts
UNION ALL
SELECT concept, itemid
FROM known_quarantine;

CREATE TEMP TABLE raw_preclassified AS
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
  le.ref_range_lower,
  le.ref_range_upper,
  le.flag,
  le.priority,
  le.comments,
  lc.rule_id,
  kq.reason_code AS known_quarantine_reason,
  COUNT(*) OVER (PARTITION BY le.labevent_id) AS episode_match_count,
  CASE
    WHEN kq.reason_code IS NOT NULL THEN kq.reason_code
    WHEN lc.itemid IS NULL THEN 'unregistered_itemid'
    WHEN LOWER(TRIM(di.fluid)) != LOWER(TRIM(lc.expected_fluid))
      THEN 'fluid_mismatch'
    WHEN LOWER(TRIM(di.category)) != LOWER(TRIM(lc.expected_category))
      THEN 'category_mismatch'
    WHEN le.valueuom IS NULL OR TRIM(le.valueuom) = ''
      THEN 'missing_unit'
    WHEN NOT EXISTS (
      SELECT 1
      FROM UNNEST(lc.allowed_units) allowed_unit
      WHERE LOWER(TRIM(le.valueuom)) = LOWER(TRIM(allowed_unit))
    ) THEN 'unknown_unit'
    ELSE 'approved_contract'
  END AS contract_status,
  CASE
    WHEN le.storetime IS NOT NULL AND le.storetime < le.charttime
      THEN 'storetime_before_charttime'
    WHEN GREATEST(le.charttime, COALESCE(le.storetime, le.charttime)) >= c.t12
      THEN 'available_after_landmark'
    ELSE 'available_before_landmark'
  END AS availability_status,
  CASE
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^>=?\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$'
    ) THEN 'right_censored'
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^<=?\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$'
    ) THEN 'left_censored'
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*[-/]\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$'
    ) THEN 'interval'
    WHEN le.valuenum IS NOT NULL THEN 'exact_numeric'
    ELSE 'unparseable_or_text'
  END AS result_class,
  CASE
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^>=?\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$'
    ) THEN SAFE_CAST(REGEXP_EXTRACT(
      TRIM(le.value),
      r'^>=?\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)$'
    ) AS FLOAT64)
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*[-/]\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$'
    ) THEN SAFE_CAST(REGEXP_EXTRACT(
      TRIM(le.value),
      r'^([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*[-/]'
    ) AS FLOAT64)
    ELSE NULL
  END AS lower_bound,
  CASE
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^<=?\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$'
    ) THEN SAFE_CAST(REGEXP_EXTRACT(
      TRIM(le.value),
      r'^<=?\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)$'
    ) AS FLOAT64)
    WHEN REGEXP_CONTAINS(
      TRIM(le.value),
      r'^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*[-/]\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$'
    ) THEN SAFE_CAST(REGEXP_EXTRACT(
      TRIM(le.value),
      r'[-/]\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))$'
    ) AS FLOAT64)
    ELSE NULL
  END AS upper_bound
FROM cohort c
JOIN `physionet-data.mimiciv_3_1_hosp.labevents` le
  ON le.subject_id = c.subject_id
 AND le.hadm_id = c.hadm_id
 AND le.charttime >= c.t0
 AND le.charttime < c.t12
JOIN scoped_items si
  USING (itemid)
JOIN `physionet-data.mimiciv_3_1_hosp.d_labitems` di
  USING (itemid)
LEFT JOIN lab_contracts lc
  USING (itemid)
LEFT JOIN known_quarantine kq
  USING (itemid);

CREATE TEMP TABLE classified AS
SELECT
  *,
  COUNT(*) OVER (
    PARTITION BY stay_id,
      COALESCE(CAST(specimen_id AS STRING), CONCAT('labevent:', CAST(labevent_id AS STRING))),
      itemid
  ) AS specimen_itemid_count
FROM raw_preclassified;

CREATE TEMP TABLE audited AS
SELECT
  *,
  CASE
    WHEN episode_match_count > 1 THEN 'ambiguous_episode_join'
    WHEN contract_status != 'approved_contract' THEN contract_status
    WHEN availability_status != 'available_before_landmark' THEN availability_status
    WHEN specimen_id IS NULL THEN 'missing_specimen_id'
    WHEN specimen_itemid_count > 1 THEN 'duplicate_specimen_itemid'
    ELSE NULL
  END AS quarantine_reason
FROM classified;

CREATE TEMP TABLE raw_eligible AS
SELECT *
FROM audited
WHERE quarantine_reason IS NULL;

CREATE TEMP TABLE bun_raw_keys AS
SELECT DISTINCT stay_id, specimen_id
FROM raw_eligible
WHERE concept = 'bun'
  AND valuenum IS NOT NULL
  AND valuenum > 0
  AND valuenum <= 300;

CREATE TEMP TABLE bun_derived_keys AS
SELECT DISTINCT c.stay_id, d.specimen_id
FROM cohort c
JOIN `physionet-data.mimiciv_3_1_derived.chemistry` d
  ON d.subject_id = c.subject_id
 AND d.hadm_id = c.hadm_id
 AND d.charttime >= c.t0
 AND d.charttime < c.t12
WHERE d.bun IS NOT NULL;

CREATE TEMP TABLE bun_coverage AS
SELECT
  'bun' AS concept,
  CASE
    WHEN r.specimen_id IS NOT NULL AND d.specimen_id IS NOT NULL THEN 'both'
    WHEN r.specimen_id IS NOT NULL THEN 'raw_only'
    ELSE 'derived_only'
  END AS coverage_status,
  COALESCE(r.stay_id, d.stay_id) AS stay_id,
  COALESCE(r.specimen_id, d.specimen_id) AS coverage_key
FROM bun_raw_keys r
FULL OUTER JOIN bun_derived_keys d
  USING (stay_id, specimen_id);

CREATE TEMP TABLE lactate_raw_keys AS
SELECT DISTINCT stay_id, charttime
FROM raw_eligible
WHERE concept = 'lactate'
  AND valuenum IS NOT NULL
  AND valuenum <= 10000;

CREATE TEMP TABLE lactate_derived_keys AS
SELECT DISTINCT c.stay_id, d.charttime
FROM cohort c
JOIN `physionet-data.mimiciv_3_1_derived.bg` d
  ON d.subject_id = c.subject_id
 AND d.hadm_id = c.hadm_id
 AND d.charttime >= c.t0
 AND d.charttime < c.t12
WHERE d.lactate IS NOT NULL;

CREATE TEMP TABLE lactate_coverage AS
SELECT
  'lactate' AS concept,
  CASE
    WHEN r.charttime IS NOT NULL AND d.charttime IS NOT NULL THEN 'both'
    WHEN r.charttime IS NOT NULL THEN 'raw_only'
    ELSE 'derived_only'
  END AS coverage_status,
  COALESCE(r.stay_id, d.stay_id) AS stay_id,
  FARM_FINGERPRINT(CAST(COALESCE(r.charttime, d.charttime) AS STRING)) AS coverage_key
FROM lactate_raw_keys r
FULL OUTER JOIN lactate_derived_keys d
  USING (stay_id, charttime);

WITH raw_summary AS (
  SELECT
    concept,
    itemid,
    label,
    fluid,
    category,
    valueuom AS unit,
    quarantine_reason,
    result_class,
    COUNT(*) AS n_rows,
    COUNT(DISTINCT specimen_id) AS n_specimens,
    COUNT(DISTINCT stay_id) AS n_stays,
    MIN(charttime) AS min_charttime,
    MAX(charttime) AS max_charttime
  FROM audited
  GROUP BY
    concept, itemid, label, fluid, category, unit,
    quarantine_reason, result_class
), coverage_summary AS (
  SELECT concept, coverage_status, COUNT(*) AS n_rows,
    COUNT(DISTINCT stay_id) AS n_stays
  FROM (
    SELECT concept, coverage_status, stay_id FROM bun_coverage
    UNION ALL
    SELECT concept, coverage_status, stay_id FROM lactate_coverage
  )
  GROUP BY concept, coverage_status
)
SELECT
  'dictionary_contract' AS audit_section,
  audit_rule_version AS rule_version,
  dictionary_status AS status,
  concept,
  itemid,
  observed_label AS label,
  observed_fluid AS fluid,
  observed_category AS category,
  CAST(NULL AS STRING) AS unit,
  CAST(NULL AS STRING) AS quarantine_reason,
  CAST(NULL AS STRING) AS result_class,
  CAST(NULL AS INT64) AS n_rows,
  CAST(NULL AS INT64) AS n_specimens,
  CAST(NULL AS INT64) AS n_stays,
  CAST(NULL AS DATETIME) AS min_charttime,
  CAST(NULL AS DATETIME) AS max_charttime,
  CONCAT('rule_id=', rule_id) AS notes
FROM dictionary_contract

UNION ALL

SELECT
  'raw_semantic_and_time' AS audit_section,
  audit_rule_version AS rule_version,
  IF(quarantine_reason IS NULL, 'eligible', 'quarantined') AS status,
  concept,
  itemid,
  label,
  fluid,
  category,
  unit,
  quarantine_reason,
  result_class,
  n_rows,
  n_specimens,
  n_stays,
  min_charttime,
  max_charttime,
  'Raw values are preserved; no silent zero-fill, truncation, conversion, or censor substitution.' AS notes
FROM raw_summary

UNION ALL

SELECT
  'raw_derived_coverage' AS audit_section,
  audit_rule_version AS rule_version,
  coverage_status AS status,
  concept,
  CAST(NULL AS INT64) AS itemid,
  CAST(NULL AS STRING) AS label,
  CAST(NULL AS STRING) AS fluid,
  CAST(NULL AS STRING) AS category,
  CAST(NULL AS STRING) AS unit,
  CAST(NULL AS STRING) AS quarantine_reason,
  CAST(NULL AS STRING) AS result_class,
  n_rows,
  CAST(NULL AS INT64) AS n_specimens,
  n_stays,
  CAST(NULL AS DATETIME) AS min_charttime,
  CAST(NULL AS DATETIME) AS max_charttime,
  CASE concept
    WHEN 'bun' THEN 'Coverage key: stay_id + specimen_id; derived chemistry lacks storetime.'
    WHEN 'lactate' THEN 'Coverage key: stay_id + charttime; derived bg does not expose specimen_id/storetime.'
  END AS notes
FROM coverage_summary

ORDER BY audit_section, concept, itemid, status, unit, result_class;
