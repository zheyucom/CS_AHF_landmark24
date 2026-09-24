-- Independent verification for Stage 5G compact feature matrix.

ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`) = 1844
  AS 'Matrix row count changed';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924` WHERE cohort_version = 'V4_main') = 1083
  AS 'V4 row count changed';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924` WHERE cohort_version = 'V3_strict_sensitivity') = 761
  AS 'V3 row count changed';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
        WHERE bun_log1p_blood_only IS NOT NULL AND bun_state != 'measured_exact') = 0
  AS 'Non-blood or non-exact BUN reached matrix';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
        WHERE lactate_log1p_raw IS NOT NULL AND lactate_state != 'measured_exact') = 0
  AS 'Non-exact lactate reached primary matrix';
ASSERT (SELECT COUNT(DISTINCT feature_name) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_formula_audit_v1_20260924`) = 10
  AS 'Expected 10 features across two cohorts';
ASSERT (SELECT COUNT(*) FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_matrix_v1_20260924`
        WHERE feature_contract != 'compact_feature_matrix_v1_explicit_representatives_20260924') = 0
  AS 'Unexpected feature contract version';

SELECT cohort_version, feature_name, observed_n, missing_n, observed_fraction
FROM `project-9386bb9f-de39-47eb-886.ahf_work.mimic_dhf_compact_feature_formula_audit_v1_20260924`
ORDER BY cohort_version, feature_name;
