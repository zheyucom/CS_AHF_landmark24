-- SUPERSEDED 2026-09-17: discovery-oriented historical template only.
-- Do not use this file to freeze laboratory features. Use:
--   MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql for dictionary-only discovery;
--   MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql for exact-contract patient-level audit.
--
-- MIMIC-IV 3.1 / BigQuery audit template
-- execution_status: not_run (no patient-level MIMIC connection was available in this workspace)
-- Replace the project/dataset prefix only after confirming the local snapshot.
-- This query audits raw value strings; it does not create a clinical cohort.

ASSERT FALSE AS 'SUPERSEDED: run MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql instead.';

WITH item_scope AS (
  SELECT itemid, label, fluid, category
  FROM `physionet-data.mimiciv_3_1_hosp.d_labitems`
  WHERE REGEXP_CONTAINS(
    LOWER(label),
    r'(lactate|lactic acid|bnp|nt[- ]?pro[- ]?bnp|pro[- ]?bnp|troponin|creatinine|^ph$)'
  )
), raw AS (
  SELECT
    le.labevent_id, le.subject_id, le.hadm_id, le.specimen_id, le.itemid,
    i.label, i.fluid, i.category, le.charttime, le.value, le.valuenum,
    le.valueuom, le.ref_range_lower, le.ref_range_upper, le.flag, le.comments
  FROM `physionet-data.mimiciv_3_1_hosp.labevents` le
  JOIN item_scope i USING (itemid)
), classified AS (
  SELECT *,
    CASE
      WHEN REGEXP_CONTAINS(TRIM(value), r'^>\s*[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?$') THEN 'right_censored'
      WHEN REGEXP_CONTAINS(TRIM(value), r'^<\s*[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?$') THEN 'left_censored'
      WHEN REGEXP_CONTAINS(TRIM(value), r'^[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)\s*[-/]\s*[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$') THEN 'interval'
      WHEN valuenum IS NOT NULL THEN 'exact_numeric'
      ELSE 'unparseable_or_text'
    END AS result_class,
    SAFE_CAST(REGEXP_EXTRACT(TRIM(value), r'([-+]?[0-9]+(?:\.[0-9]*)?|[-+]?\.[0-9]+)') AS FLOAT64) AS extracted_bound
  FROM raw
)
SELECT
  itemid, label, valueuom,
  COUNT(*) AS total_records,
  COUNTIF(result_class = 'exact_numeric') AS exact_numeric_records,
  COUNTIF(result_class = 'right_censored') AS right_censored_records,
  COUNTIF(result_class = 'left_censored') AS left_censored_records,
  COUNTIF(result_class = 'interval') AS interval_records,
  COUNTIF(result_class = 'unparseable_or_text') AS unparseable_or_text_records,
  COUNTIF(valuenum IS NULL) AS missing_valuenum_records,
  COUNTIF(valueuom IS NULL OR TRIM(valueuom) = '') AS missing_unit_records,
  SAFE_DIVIDE(COUNTIF(result_class IN ('right_censored','left_censored','interval')), COUNT(*)) AS censored_or_interval_fraction,
  MIN(charttime) AS earliest_charttime,
  MAX(charttime) AS latest_charttime
FROM classified
GROUP BY itemid, label, valueuom
ORDER BY label, itemid, valueuom;

-- Historical follow-up checklist retained for provenance only.
