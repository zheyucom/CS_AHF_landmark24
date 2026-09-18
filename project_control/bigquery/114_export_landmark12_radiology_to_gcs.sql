-- Export the complete report table, including the text field, to GCS.
-- Run only after confirming that the bucket exists and is in the same
-- location as the BigQuery dataset (the current tables are in US).
-- Replace the bucket and prefix with a new, private path for this export.

EXPORT DATA OPTIONS (
  uri = 'gs://ahf_bigquery_export/dhf_landmark12/radiology_raw_v1_*.parquet',
  format = 'PARQUET',
  overwrite = false
) AS
SELECT *
FROM `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_raw_landmark12_v1`
ORDER BY stay_id, charttime, note_id;
