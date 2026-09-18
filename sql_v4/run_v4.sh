#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SQL_DIR="$ROOT/sql_v4/executable"
RUN_DIR="$ROOT/project_control/runs/20260825_v4_admission_present/sql_logs"
PSQL=${PSQL:-/Library/PostgreSQL/12/bin/psql}
PGHOST=${PGHOST:-localhost}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-mimiciv31}

mkdir -p "$RUN_DIR"

for file in \
    001_create_schema_and_manifest.sql \
    010_adult_first_icu.sql \
    020_hf_icd_candidate.sql \
    061A_create_ahf_evidence_table_12h.sql \
    061B_create_ahf_strict_12h.sql \
    061C_create_pre12_overt_cs_flags.sql \
    061D_create_landmark12_riskset.sql \
    061E_create_post12_overt_cs_future48h.sql \
    062A_create_early_sepsis12_flags.sql \
    062B_create_ahf_earlysepsis12_main_outcome.sql \
    063A_create_candidate_hd_outcomes_overall.sql \
    063C_create_hd_outcomes_with_nee.sql \
    064_create_primary_analysis_outcome.sql \
    070A_create_modeling_base_index.sql \
    070C_create_static_clinical_features.sql \
    070D2_create_vitals_0_12h_clean_features..sql \
    070E_create_labs_0_12h_features.sql \
    070F_create_support_0_12h_features.sql \
    070G_create_modeling_dataset_v1.sql \
    079A_create_event_timing_components.sql \
    080A_create_vital_burden_0_12h_features.sql \
    080G_create_modeling_dataset_v2.sql \
    081A_create_structured_echo_screen_0_12h_features.sql \
    900_audit_pipeline.sql
do
    echo "Running $file"
    "$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
        -f "$SQL_DIR/$file" > "$RUN_DIR/$file.log" 2>&1
done
