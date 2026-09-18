-- MIMIC-IV laboratory dictionary candidate discovery only.
-- This query reads d_labitems, never labevents or patient-level identifiers.
-- A proposed_candidate is not permitted to create a feature until it completes
-- the sourced -> fixture_added -> regression_tested -> human-approved lifecycle.

WITH active_contracts AS (
  SELECT *
  FROM UNNEST([
    STRUCT('bun' AS concept, 51006 AS itemid, 'Blood' AS fluid, 'Chemistry' AS category),
    STRUCT('lactate' AS concept, 50813 AS itemid, 'Blood' AS fluid, 'Blood Gas' AS category),
    STRUCT('creatinine' AS concept, 50912 AS itemid, 'Blood' AS fluid, 'Chemistry' AS category),
    STRUCT('ph' AS concept, 50820 AS itemid, 'Blood' AS fluid, 'Blood Gas' AS category),
    STRUCT('ntprobnp' AS concept, 50963 AS itemid, 'Blood' AS fluid, 'Chemistry' AS category),
    STRUCT('troponin_t' AS concept, 51003 AS itemid, 'Blood' AS fluid, 'Chemistry' AS category)
  ])
), known_quarantine AS (
  SELECT itemid
  FROM UNNEST([51104, 51045, 50851, 51804, 51825, 51842, 51922, 51951]) itemid
), discovered AS (
  SELECT
    di.itemid,
    di.label,
    di.fluid,
    di.category,
    ac.concept AS active_concept,
    CASE
      WHEN ac.itemid IS NOT NULL
        AND LOWER(TRIM(di.fluid)) = LOWER(TRIM(ac.fluid))
        AND LOWER(TRIM(di.category)) = LOWER(TRIM(ac.category))
        THEN 'active_exact_contract'
      WHEN ac.itemid IS NOT NULL THEN 'contract_dictionary_mismatch'
      WHEN kq.itemid IS NOT NULL THEN 'known_quarantine'
      ELSE 'proposed_candidate'
    END AS evidence_status
  FROM `physionet-data.mimiciv_3_1_hosp.d_labitems` di
  LEFT JOIN active_contracts ac USING (itemid)
  LEFT JOIN known_quarantine kq USING (itemid)
  WHERE ac.itemid IS NOT NULL
     OR kq.itemid IS NOT NULL
     OR REGEXP_CONTAINS(
       LOWER(TRIM(di.label)),
       r'(urea nitrogen|^bun$|^lactate$|lactic acid|bnp|natriuretic|troponin|creatinine|^ph$)'
     )
)
SELECT
  itemid,
  label,
  fluid,
  category,
  active_concept,
  evidence_status,
  evidence_status = 'active_exact_contract' AS currently_enforced,
  evidence_status = 'proposed_candidate' AS requires_source_fixture_and_approval
FROM discovered
ORDER BY evidence_status, active_concept, label, fluid, itemid;
