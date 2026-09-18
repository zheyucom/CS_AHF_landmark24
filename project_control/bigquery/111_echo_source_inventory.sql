-- Echo source discovery helper.
-- BigQuery does not permit a static query against an unknown dataset name.
-- First run 111_discover_echo_sources.sh, then inspect only the candidate
-- dataset/table names that your account can actually see.
-- This file is intentionally row-free: it returns metadata only.

-- Replace DATASET_NAME and TABLE_NAME after the shell inventory succeeds.
SELECT
  table_catalog,
  table_schema,
  table_name,
  column_name,
  data_type,
  is_nullable,
  ordinal_position
FROM `physionet-data.DATASET_NAME.INFORMATION_SCHEMA.COLUMNS`
WHERE LOWER(table_name) LIKE '%echo%'
   OR LOWER(table_name) LIKE '%cardio%'
   OR LOWER(table_name) LIKE '%ultrasound%'
   OR LOWER(column_name) LIKE '%lvef%'
   OR LOWER(column_name) LIKE '%ejection%'
   OR LOWER(column_name) LIKE '%ventric%'
   OR LOWER(column_name) LIKE '%echo%'
ORDER BY table_name, ordinal_position;
