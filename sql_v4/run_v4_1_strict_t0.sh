#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SQL_DIR="$ROOT/sql_v4"
RUN_DIR="$ROOT/project_control/runs/20260825_v4_1_strict_t0/sql_logs"
REPORT_DIR="$ROOT/project_control/runs/20260825_v4_1_strict_t0/reports"
RAW_DIR="$ROOT/CS_AHF_hemodynamic_deterioration_ml_project/data/raw_v4_1"
PSQL=${PSQL:-/Library/PostgreSQL/12/bin/psql}
PGHOST=${PGHOST:-localhost}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-mimiciv31}

mkdir -p "$RUN_DIR" "$REPORT_DIR" "$RAW_DIR"

"$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$SQL_DIR/audits/092_audit_final_t0_cohort_definition.sql" \
    > "$RUN_DIR/092_audit_final_t0_cohort_definition.sql.log" 2>&1

"$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$SQL_DIR/executable/092_create_final_t0_modeling_dataset.sql" \
    > "$RUN_DIR/092_create_final_t0_modeling_dataset.sql.log" 2>&1

"$PSQL" -X -v ON_ERROR_STOP=1 -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    -c "\\copy (select * from study_ahf_v4.audit_092_final_t0_definition_v1) to '$RAW_DIR/audit_092_final_t0_definition_v1.csv' with (format csv, header true)" \
    -c "\\copy (select * from study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1) to '$RAW_DIR/model_092_t0_ahf_sepsis_strict_v1.csv' with (format csv, header true)" \
    -c "\\copy (select 'broad' as definition, count(*) as n, sum(primary_outcome_flag) as events, round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2) as event_rate_pct, sum(death_12_60_flag) as deaths_12_60, sum(secondary_hd_deterioration_nee010_flag) as nee010_events, sum(secondary_hd_deterioration_no_nee_flag) as no_nee_events, sum(secondary_mixed_shock_proxy_flag) as mixed_shock_events from study_ahf_v4.audit_092_final_t0_definition_v1 where final_t0_ahf_sepsis_broad_flag = 1 union all select 'high_specificity', count(*), sum(primary_outcome_flag), round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2), sum(death_12_60_flag), sum(secondary_hd_deterioration_nee010_flag), sum(secondary_hd_deterioration_no_nee_flag), sum(secondary_mixed_shock_proxy_flag) from study_ahf_v4.audit_092_final_t0_definition_v1 where final_t0_ahf_sepsis_high_specificity_flag = 1) to '$REPORT_DIR/092_final_t0_outcome_summary.csv' with (format csv, header true)" \
    -c "\\copy (select cohort_rule, count(*) as n_stays, sum(primary_outcome_flag) as n_primary_events, round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2) as primary_event_rate_pct from (select 'current_v4_admission_present' as cohort_rule, primary_outcome_flag from study_ahf_v4.audit_092_final_t0_definition_v1 where early_sepsis_admission_present_flag = 1 union all select 'final_t0_broad' as cohort_rule, primary_outcome_flag from study_ahf_v4.audit_092_final_t0_definition_v1 where final_t0_ahf_sepsis_broad_flag = 1 union all select 'final_t0_high_specificity' as cohort_rule, primary_outcome_flag from study_ahf_v4.audit_092_final_t0_definition_v1 where final_t0_ahf_sepsis_high_specificity_flag = 1) x group by cohort_rule order by cohort_rule) to '$REPORT_DIR/092_cohort_feasibility.csv' with (format csv, header true)"

echo "[OK] strict T0 audit and modeling dataset exported to $RAW_DIR"
