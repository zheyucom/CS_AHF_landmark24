-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/03_features/080G_export_qc_and_dataset.sql
-- Purpose:
--   Export QC tables and Python-ready raw CSV for
--   study_ahf.model_080G_modeling_dataset_v2.
--
-- Usage:
--   Run from the CS_AHF_landmark24 root with psql after
--   sql/03_features/080G_create_modeling_dataset_v2.sql has completed.
--
-- Notes:
--   This file uses psql meta-commands. It is not pure SQL.
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o sql_results/080G_QC1_overall.csv
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate,
    sum(vital_burden_available_flag) as n_vital_burden_available,
    round(sum(vital_burden_available_flag) * 100.0 / count(*), 2) as pct_vital_burden_available
from study_ahf.model_080G_modeling_dataset_v2;
\o

\o sql_results/080G_QC2_column_count.csv
select
    count(*) as n_columns
from information_schema.columns
where table_schema = 'study_ahf'
  and table_name = 'model_080g_modeling_dataset_v2';
\o

\o sql_results/080G_QC3_new_feature_missingness.csv
select
    count(*) as n_total,

    round(sum(case when map_lt65_record_prop is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_map_lt65_record_prop,
    round(sum(case when shock_index_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_shock_index_max,
    round(sum(case when modified_shock_index_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_modified_shock_index_max,
    round(sum(case when pulse_pressure_min is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_pulse_pressure_min,
    round(sum(case when sbp_slope_per_hour is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_sbp_slope,
    round(sum(case when mbp_slope_per_hour is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_mbp_slope,
    round(sum(case when hr_slope_per_hour is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_hr_slope,
    round(sum(case when rr_slope_per_hour is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_rr_slope
from study_ahf.model_080G_modeling_dataset_v2;
\o

\o sql_results/080G_QC4_potential_leakage_columns.csv
select
    column_name
from information_schema.columns
where table_schema = 'study_ahf'
  and table_name = 'model_080g_modeling_dataset_v2'
  and (
        lower(column_name) like '%post12%'
     or lower(column_name) like '%death_12_60%'
     or lower(column_name) like '%followup%'
     or lower(column_name) like '%observed_until%'
     or lower(column_name) like '%event_time%'
     or lower(column_name) like '%event_hour%'
  )
order by column_name;
\o

\o CS_AHF_hemodynamic_deterioration_ml_project/data/raw/model_080G_modeling_dataset_v2.csv
select *
from study_ahf.model_080G_modeling_dataset_v2
order by stay_id;
\o

\pset format aligned
\pset footer on
