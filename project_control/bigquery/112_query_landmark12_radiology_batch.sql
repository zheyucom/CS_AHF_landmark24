-- Browser-safe batch export for the 109 raw report table.
-- Replace the OFFSET value with 0, 2000, 4000, or 6000 and run each batch.
-- Keep the ORDER BY fields unchanged so batches are deterministic.
-- This query intentionally keeps text for the 2,000-row batches; do not use
-- the browser's one-shot export for all 7,828 rows.

SELECT *
FROM `YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_landmark12_v1`
ORDER BY stay_id, charttime, note_id
LIMIT 2000 OFFSET BATCH_OFFSET;
