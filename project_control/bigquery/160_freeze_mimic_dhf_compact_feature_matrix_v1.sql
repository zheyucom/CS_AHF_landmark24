-- Stage 5G: freeze an explicit, cross-database compact feature matrix.
--
-- The previous 10-domain manifest was not sufficient because several domains
-- still had multiple unweighted components. This matrix deliberately uses
-- one pre-specified representative per domain, keeps raw states alongside
-- values, and leaves admission_type, derived lactate, treatment proxies and
-- support states for sensitivity work rather than hiding them in a score.

DECLARE run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP();

CREATE OR REPLACE TABLE
  `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924` AS
WITH c AS (
  SELECT *
  FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_predictor_candidate_union_v1_20260922`
), f AS (
  SELECT
    cohort_version, subject_id, hadm_id, stay_id, t0, t12, t60,
    final_outcome_status, target_event_component, target_event_time,
    competing_event_time, observation_end,
    age,
    admission_type,
    CASE WHEN age IS NOT NULL THEN age END AS age_years,
    CASE WHEN ntprobnp_state = 'measured_exact'
              AND ntprobnp_last_value >= 0
         THEN LN(1 + ntprobnp_last_value) END AS ntprobnp_log1p,
    CASE WHEN lactate_state = 'measured_exact'
              AND lactate_last_value >= 0
         THEN LN(1 + lactate_last_value) END AS lactate_log1p_raw,
    CASE WHEN bun_state = 'measured_exact'
              AND bun_last_value >= 0
         THEN LN(1 + bun_last_value) END AS bun_log1p_blood_only,
    CASE WHEN creatinine_state = 'measured_exact'
              AND creatinine_last_value >= 0
         THEN LN(1 + creatinine_last_value) END AS creatinine_log1p,
    CASE WHEN ph_state = 'measured_exact'
              AND ph_last_value BETWEEN 6.5 AND 8.0
         THEN ph_last_value END AS ph_raw,
    CASE WHEN sodium_state = 'measured_exact'
              AND sodium_last_value BETWEEN 80 AND 250
         THEN sodium_last_value END AS sodium_raw,
    CASE WHEN hemoglobin_state = 'measured_exact'
              AND hemoglobin_last_value BETWEEN 0 AND 30
         THEN hemoglobin_last_value END AS hemoglobin_raw,
    CASE WHEN wbc_state = 'measured_exact'
              AND wbc_last_value >= 0
         THEN LN(1 + wbc_last_value) END AS wbc_log1p,
    CASE WHEN mbp_valid_n > 0 THEN mbp_last_value END AS mbp_raw,
    ntprobnp_state, lactate_state, bun_state, creatinine_state, ph_state,
    sodium_state, hemoglobin_state, wbc_state,
    mbp_valid_n, vital_out_of_range_cell_n,
    'age_years|ntprobnp_log1p|lactate_log1p_raw|bun_log1p_blood_only|creatinine_log1p|ph_raw|sodium_raw|hemoglobin_raw|wbc_log1p|mbp_raw' AS feature_set,
    run_timestamp AS feature_build_timestamp,
    'compact_feature_matrix_v1_explicit_representatives_20260924' AS feature_contract
  FROM c
)
SELECT * FROM f;

CREATE OR REPLACE TABLE
  `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_formula_audit_v1_20260924` AS
WITH m AS (
  SELECT * FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
), a AS (
  SELECT cohort_version, stay_id, 'age_years' AS feature_name, 'age' AS source_column, age_years AS value FROM m
  UNION ALL SELECT cohort_version, stay_id, 'ntprobnp_log1p', 'ntprobnp_last_value[blood exact]', ntprobnp_log1p FROM m
  UNION ALL SELECT cohort_version, stay_id, 'lactate_log1p_raw', 'lactate_last_value[raw exact]', lactate_log1p_raw FROM m
  UNION ALL SELECT cohort_version, stay_id, 'bun_log1p_blood_only', 'bun_last_value[itemid 51006 blood]', bun_log1p_blood_only FROM m
  UNION ALL SELECT cohort_version, stay_id, 'creatinine_log1p', 'creatinine_last_value', creatinine_log1p FROM m
  UNION ALL SELECT cohort_version, stay_id, 'ph_raw', 'ph_last_value', ph_raw FROM m
  UNION ALL SELECT cohort_version, stay_id, 'sodium_raw', 'sodium_last_value', sodium_raw FROM m
  UNION ALL SELECT cohort_version, stay_id, 'hemoglobin_raw', 'hemoglobin_last_value', hemoglobin_raw FROM m
  UNION ALL SELECT cohort_version, stay_id, 'wbc_log1p', 'wbc_last_value', wbc_log1p FROM m
  UNION ALL SELECT cohort_version, stay_id, 'mbp_raw', 'mbp_last_value[within plausible range]', mbp_raw FROM m
)
SELECT cohort_version, feature_name, ANY_VALUE(source_column) AS source_column,
       COUNT(*) AS cohort_n, COUNTIF(value IS NOT NULL) AS observed_n,
       COUNTIF(value IS NULL) AS missing_n,
       SAFE_DIVIDE(COUNTIF(value IS NOT NULL), COUNT(*)) AS observed_fraction
FROM a
GROUP BY cohort_version, feature_name
ORDER BY cohort_version, feature_name;

ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`) = 1844
  AS 'Compact feature matrix row count changed';
ASSERT (SELECT COUNT(*) FROM (
  SELECT cohort_version, stay_id, COUNT(*) AS n
  FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
  GROUP BY cohort_version, stay_id HAVING COUNT(*) != 1
)) = 0 AS 'Compact feature matrix duplicate stay rows';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
        WHERE t12 <= t0 OR feature_contract != 'compact_feature_matrix_v1_explicit_representatives_20260924') = 0
  AS 'Compact feature matrix time or contract gate failed';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
        WHERE bun_log1p_blood_only IS NOT NULL AND bun_state != 'measured_exact') = 0
  AS 'BUN value does not have measured_exact blood state';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_formula_audit_v1_20260924`
        WHERE cohort_n NOT IN (1083, 761) OR observed_n + missing_n != cohort_n) = 0
  AS 'Feature formula audit count failed';

SELECT cohort_version, feature_name, source_column, cohort_n, observed_n, missing_n,
       observed_fraction, 10 AS declared_parameter_ceiling
FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_formula_audit_v1_20260924`
ORDER BY cohort_version, feature_name;
