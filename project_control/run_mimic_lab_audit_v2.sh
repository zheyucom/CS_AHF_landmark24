#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-9386bb9f-de39-47eb-886}"
SCRATCH_DATASET="${SCRATCH_DATASET:-ahf_work}"
LOCATION="${LOCATION:-US}"
SQL="${SQL:-project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql}"
STAMP="${STAMP:-$(date -u +%Y%m%d)}"
OUT="${OUT:-project_control/task_reports/MIMIC_LAB_AUDIT_V2_RESULT_${STAMP}.csv}"
LOG="${LOG:-project_control/task_reports/MIMIC_LAB_AUDIT_V2_RUN_${STAMP}.log}"
MAX_BYTES="${MAX_BYTES:-20000000000}"

scratch_tables=(
  lab_contracts known_quarantine dictionary_contract cohort scoped_items
  raw_preclassified classified audited raw_eligible
  bun_raw_keys bun_derived_keys bun_coverage
  lactate_raw_keys lactate_derived_keys lactate_coverage
)

command -v bq >/dev/null || { echo "bq not found" >&2; exit 127; }
mkdir -p "$(dirname "$OUT")" "$(dirname "$LOG")"
tmp_sql="$(mktemp)"
cleanup() {
  local drops=""
  for table in "${scratch_tables[@]}"; do
    drops+="DROP TABLE IF EXISTS \`${table}\`; "
  done
  bq query --project_id="$PROJECT_ID" --dataset_id="${PROJECT_ID}:${SCRATCH_DATASET}" \
    --location="$LOCATION" --use_legacy_sql=false --quiet "$drops" >/dev/null 2>&1 || true
  rm -f "$tmp_sql"
}
trap cleanup EXIT

# This project blocks BigQuery _script temporary datasets. Use controlled
# scratch tables in ahf_work, then remove them in cleanup().
perl -pe 's/CREATE TEMP TABLE /CREATE OR REPLACE TABLE /g' "$SQL" > "$tmp_sql"
: > "$OUT"
: > "$LOG"
{
  printf 'started_at='
  date -u +%Y-%m-%dT%H:%M:%SZ
  sha256sum "$SQL"
  echo "execution_mode=controlled_permanent_scratch"
  echo "project=$PROJECT_ID"
  echo "scratch_dataset=$SCRATCH_DATASET"
  echo "location=$LOCATION"
  echo "maximum_bytes_billed=$MAX_BYTES"
} >> "$LOG"

bq query --project_id="$PROJECT_ID" --dataset_id="${PROJECT_ID}:${SCRATCH_DATASET}" \
  --location="$LOCATION" --use_legacy_sql=false \
  --maximum_bytes_billed="$MAX_BYTES" --format=csv < "$tmp_sql" 2>> "$LOG" | awk 'BEGIN{keep=0} /^audit_section,/{keep=1} keep{print}' > "$OUT"

{
  printf 'finished_at='
  date -u +%Y-%m-%dT%H:%M:%SZ
  echo "output=$OUT"
} >> "$LOG"
