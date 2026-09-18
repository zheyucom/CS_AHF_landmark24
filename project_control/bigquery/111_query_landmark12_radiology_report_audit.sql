-- Compact, patient-report-level audit input for the primary DHF phenotype
-- window.  It deliberately excludes the free-text body so browser download is
-- complete and the local audit only uses precomputed, reproducible fields.
--
-- Source: dhf_radiology_raw_landmark12_v1 created by 109.
-- Window: [ICU intime - 24 h, ICU intime + 12 h).  This is phenotype evidence,
-- never a predictor in the [T0, T12) haemodynamic-deterioration model.

CREATE OR REPLACE TABLE
  `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_report_audit_landmark12_v1` AS
WITH source AS (
  SELECT
    stay_id,
    subject_id,
    hadm_id,
    note_id,
    note_type,
    note_seq,
    charttime,
    storetime,
    report_available_by_t12_flag,
    storetime_missing_flag,
    pulmonary_edema_hit,
    vascular_congestion_hit,
    pleural_effusion_hit,
    cardiomegaly_hit,
    pulmonary_edema_negation_hit,
    vascular_congestion_negation_hit,
    uncertainty_hit,
    positive_congestion_evidence_flag,
    -- Restrict modality detection to the report preamble.  This prevents a
    -- comparison sentence from turning a non-chest report into chest CT.
    LOWER(SUBSTR(COALESCE(text, ''), 1, 1500)) AS report_preamble
  FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_landmark12_v1`
)
SELECT
  * EXCEPT(report_preamble, rule_version),
  CASE
    WHEN REGEXP_CONTAINS(
      report_preamble,
      r'(?m)(?:^|\n)\s*(?:examination|exam|study|procedure|technique)\s*:\s*[^\n]{0,120}\b(?:ct|cta)\b[^\n]{0,120}\b(?:chest|thorax)\b'
    ) OR REGEXP_CONTAINS(
      report_preamble,
      r'(?m)(?:^|\n)\s*(?:examination|exam|study|procedure|technique)\s*:\s*[^\n]{0,120}\b(?:chest|thorax)\b[^\n]{0,120}\b(?:ct|cta)\b'
    ) OR REGEXP_CONTAINS(
      report_preamble,
      r'(?m)^\s*(?:ct|cta)\b[^\n]{0,100}\b(?:chest|thorax)\b|(?m)^\s*computed\s+tomograph(?:y|ic)\b[^\n]{0,100}\b(?:chest|thorax)\b'
    ) THEN 'chest_ct'
    WHEN REGEXP_CONTAINS(
      report_preamble,
      r'(?m)(?:^|\n)\s*(?:examination|exam|study|procedure|technique)\s*:\s*(?:[^\n]{0,80}\b(?:portable\s+)?(?:ap|pa)\s+(?:portable\s+)?chest\b|[^\n]{0,80}\bportable\s+chest\b|\s*chest\s*$|[^\n]{0,80}\bchest\s+(?:radiograph|x[- ]?ray)\b|[^\n]{0,80}\bchest\s+(?:pa\s+and\s+lat(?:eral)?|two\s+views|2\s+views|portable\s+ap)\b)'
    ) OR REGEXP_CONTAINS(
      report_preamble,
      r'(?m)^\s*(?:ap|pa)\s+(?:portable\s+)?chest\b|(?m)^\s*portable\s+chest\b|(?m)^\s*two\s+views\s+of\s+the\s+chest\b|(?m)^\s*chest\s*\(\s*(?:portable\s+)?(?:ap|pa)'
    ) THEN 'chest_xray'
    ELSE 'other_or_unclassified'
  END AS report_modality,
  '111_landmark12_compact_report_audit_v1; preamble_modality_rule; manual_validation_required' AS rule_version
FROM source
ORDER BY stay_id, charttime, note_id;
