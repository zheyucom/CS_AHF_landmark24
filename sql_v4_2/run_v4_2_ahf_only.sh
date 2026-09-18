#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SQL_DIR="$ROOT/sql_v4_2/executable"
RUN_DIR="$ROOT/project_control/runs/20260825_v4_2_ahf_only/sql_logs"
RAW_DIR="$ROOT/CS_AHF_hemodynamic_deterioration_ml_project/data/raw_v4_2"
PSQL=${PSQL:-/Library/PostgreSQL/12/bin/psql}
PGHOST=${PGHOST:-localhost}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-mimiciv31}

mkdir -p "$RUN_DIR" "$RAW_DIR"

for file in \
    001_create_schema_and_manifest.sql \
    093A_create_strict_pre_t0_ahf_only_cohort.sql \
    093B_create_ahf_only_modeling_base_index.sql \
    070C_create_static_clinical_features.sql \
    070D2_create_vitals_0_12h_clean_features.sql \
    070E_create_labs_0_12h_features.sql \
    070F_create_support_0_12h_features.sql \
    070G_create_modeling_dataset_v1.sql \
    080A_create_vital_burden_0_12h_features.sql \
    080G_create_modeling_dataset_v2.sql
do
    echo "Running $file"
    "$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
        -f "$SQL_DIR/$file" > "$RUN_DIR/$file.log" 2>&1
done

"$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -c "\\copy (select * from study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1) to '$RAW_DIR/cohort_093A_strict_pre_t0_ahf_only_v1.csv' with (format csv, header true)" \
    -c "\\copy (select * from study_ahf_v4_2.model_080g_modeling_dataset_v2) to '$RAW_DIR/model_080G_modeling_dataset_ahf_only_v4_2.csv' with (format csv, header true)" \
    -c "\\copy (select count(*) as n_total, sum(primary_outcome_flag) as n_events, round(sum(primary_outcome_flag)*100.0/nullif(count(*),0),2) as event_rate_pct, sum(complete60_icu_flag) as n_complete60, sum(death_12_60_flag) as n_death_12_60, sum(secondary_hd_deterioration_nee010_flag) as n_nee010, sum(secondary_hd_deterioration_no_nee_flag) as n_no_nee from study_ahf_v4_2.model_070a_base_index_ahf_only_v1) to '$ROOT/project_control/runs/20260825_v4_2_ahf_only/ahf_only_outcome_summary.csv' with (format csv, header true)"

echo "[OK] AHF-only strict pre-T0 dataset exported to $RAW_DIR"
