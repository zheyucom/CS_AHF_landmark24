-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/03_features/080A_export_qc.sql
-- Purpose:
--   Export QC tables for 080A vital burden 0-12h features.
--
-- Usage:
--   Run from the CS_AHF_landmark24 root with psql after
--   sql/03_features/080A_create_vital_burden_0_12h_features.sql has completed.
--
-- Notes:
--   This file uses psql meta-commands. It is not pure SQL.
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o sql_results/080A_QC1_overall.csv
select
    count(*) as n_total,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate,
    sum(vital_burden_available_flag) as n_vital_burden_available,
    round(sum(vital_burden_available_flag) * 100.0 / count(*), 2) as pct_vital_burden_available
from study_ahf.model_080A_vital_burden_0_12h_v1;
\o

\o sql_results/080A_QC2_missingness_ranges.csv
select
    count(*) as n_total,

    round(sum(case when shock_index_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_shock_index_max,
    min(shock_index_max) as shock_index_max_min,
    percentile_cont(0.5) within group (order by shock_index_max) as shock_index_max_p50,
    max(shock_index_max) as shock_index_max_max,

    round(sum(case when map_lt65_record_prop is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_map_lt65_prop,
    min(map_lt65_record_prop) as map_lt65_prop_min,
    percentile_cont(0.5) within group (order by map_lt65_record_prop) as map_lt65_prop_p50,
    max(map_lt65_record_prop) as map_lt65_prop_max,

    round(sum(case when sbp_slope_per_hour is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_sbp_slope,
    percentile_cont(0.5) within group (order by sbp_slope_per_hour) as sbp_slope_p50,
    percentile_cont(0.05) within group (order by sbp_slope_per_hour) as sbp_slope_p05,
    percentile_cont(0.95) within group (order by sbp_slope_per_hour) as sbp_slope_p95

from study_ahf.model_080A_vital_burden_0_12h_v1;
\o

\o sql_results/080A_QC3_event_rate_by_map_burden.csv
select
    case
        when map_lt65_record_prop is null then '00_missing'
        when map_lt65_record_prop = 0 then '01_none'
        when map_lt65_record_prop > 0 and map_lt65_record_prop <= 0.25 then '02_gt0_to_25pct'
        when map_lt65_record_prop > 0.25 and map_lt65_record_prop <= 0.50 then '03_25_to_50pct'
        when map_lt65_record_prop > 0.50 then '04_gt50pct'
        else '99_other'
    end as map_lt65_burden_group,
    count(*) as n,
    sum(primary_outcome_flag) as events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.model_080A_vital_burden_0_12h_v1
group by
    case
        when map_lt65_record_prop is null then '00_missing'
        when map_lt65_record_prop = 0 then '01_none'
        when map_lt65_record_prop > 0 and map_lt65_record_prop <= 0.25 then '02_gt0_to_25pct'
        when map_lt65_record_prop > 0.25 and map_lt65_record_prop <= 0.50 then '03_25_to_50pct'
        when map_lt65_record_prop > 0.50 then '04_gt50pct'
        else '99_other'
    end
order by map_lt65_burden_group;
\o

\pset format aligned
\pset footer on
