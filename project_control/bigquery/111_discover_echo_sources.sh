#!/usr/bin/env bash
set -euo pipefail

# Discover only datasets/tables visible to the user's BigQuery identity.
# This does not query clinical rows or export any patient data.
PROJECT="${1:-physionet-data}"

command -v bq >/dev/null 2>&1 || {
  echo "ERROR: bq is not on PATH" >&2
  exit 127
}

echo "# Official MIMIC-IV-Echo dataset (metadata only)"
for table in echo_record_list echo_study_list structured_measurement; do
  printf '## %s:%s\n' "${PROJECT}:mimiciv_echo" "${table}"
  if ! bq show --project_id="${PROJECT}" --format=prettyjson \
      "${PROJECT}:mimiciv_echo.${table}"; then
    echo "ACCESS_OR_NOT_FOUND"
  fi
done

echo "# Visible datasets containing echo-related names"
bq ls --project_id="${PROJECT}" --format=json --max_results=1000 \
  | jq -r '.[].datasetReference.datasetId' \
  | awk 'BEGIN{IGNORECASE=1} /echo|echocardi|cardio|ultrasound|note/ {print}' \
  | sort -u

echo
echo "# Candidate tables and fields"
while IFS= read -r dataset; do
  [ -z "${dataset}" ] && continue
  echo "## ${PROJECT}.${dataset}"
  if ! bq ls --project_id="${PROJECT}" --format=json --max_results=1000 \
      "${PROJECT}:${dataset}" 2>/dev/null \
      | jq -r '.[].tableReference.tableId' \
      | awk 'BEGIN{IGNORECASE=1} /echo|echocardi|cardio|ultrasound|lvef|ejection|ventric/ {print}' \
      | sort -u; then
    echo "ACCESS_OR_LIST_ERROR"
  fi
done < <(
  bq ls --project_id="${PROJECT}" --format=json --max_results=1000 \
    | jq -r '.[].datasetReference.datasetId' \
    | sort -u
)

echo
echo "# Next step"
echo "For each candidate table, run:"
echo "  bq show --format=prettyjson ${PROJECT}:DATASET.TABLE"
echo "Do not export rows until the table schema, subject/hadm/stay linkage, and result timestamp are confirmed."
