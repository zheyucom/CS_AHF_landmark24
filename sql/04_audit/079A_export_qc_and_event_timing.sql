-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/04_audit/079A_export_qc_and_event_timing.sql
-- Purpose:
--   Export 079A QC tables and Python-ready event timing CSV.
--
-- Usage:
--   Run from the CS_AHF_landmark24 root with psql after
--   sql/04_audit/079A_create_event_timing_components.sql has completed.
--
-- Notes:
--   This file uses psql meta-commands. It is not pure SQL.
--   Relative output paths assume the current working directory is
--   /Users/zheyu/Desktop/CS_AHF_landmark24 or equivalent project root.
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o sql_results/079_QC1_event_timing_overall.csv
select
    count(*) as n_total,
    sum(primary_outcome_flag) as n_primary_label_events,
    sum(case when primary_event_time is not null then 1 else 0 end) as n_timing_events,

    sum(event_12_36_flag) as n_event_12_36,
    round(sum(event_12_36_flag) * 100.0 / count(*), 2) as event_rate_12_36,

    sum(event_12_48_flag) as n_event_12_48,
    round(sum(event_12_48_flag) * 100.0 / count(*), 2) as event_rate_12_48,

    sum(event_12_60_timing_flag) as n_event_12_60_timing,
    round(sum(event_12_60_timing_flag) * 100.0 / count(*), 2) as event_rate_12_60_timing

from study_ahf.audit_079_event_timing_components_v1;
\o

\o sql_results/079_QC2_first_event_component.csv
select
    coalesce(primary_event_component_first, 'no_event') as first_component,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct
from study_ahf.audit_079_event_timing_components_v1
group by coalesce(primary_event_component_first, 'no_event')
order by n desc;
\o

\o sql_results/079_QC3_event_hour_distribution.csv
select
    count(*) as n_events,
    min(primary_event_hour_after_landmark) as min_hour,
    percentile_cont(0.25) within group (order by primary_event_hour_after_landmark) as p25_hour,
    percentile_cont(0.50) within group (order by primary_event_hour_after_landmark) as p50_hour,
    percentile_cont(0.75) within group (order by primary_event_hour_after_landmark) as p75_hour,
    max(primary_event_hour_after_landmark) as max_hour
from study_ahf.audit_079_event_timing_components_v1
where primary_event_time is not null;
\o

\o sql_results/079_QC4_nee_escalation_duration.csv
select
    count(*) as n_total,

    sum(case when first_nee005_escalation_time is not null then 1 else 0 end) as n_nee005_events,
    percentile_cont(0.50) within group (order by nee005_escalation_duration_hours)
        filter (where first_nee005_escalation_time is not null) as nee005_duration_p50,
    percentile_cont(0.25) within group (order by nee005_escalation_duration_hours)
        filter (where first_nee005_escalation_time is not null) as nee005_duration_p25,
    percentile_cont(0.75) within group (order by nee005_escalation_duration_hours)
        filter (where first_nee005_escalation_time is not null) as nee005_duration_p75,

    sum(case when first_nee010_escalation_time is not null then 1 else 0 end) as n_nee010_events,
    percentile_cont(0.50) within group (order by nee010_escalation_duration_hours)
        filter (where first_nee010_escalation_time is not null) as nee010_duration_p50,
    percentile_cont(0.25) within group (order by nee010_escalation_duration_hours)
        filter (where first_nee010_escalation_time is not null) as nee010_duration_p25,
    percentile_cont(0.75) within group (order by nee010_escalation_duration_hours)
        filter (where first_nee010_escalation_time is not null) as nee010_duration_p75

from study_ahf.audit_079_event_timing_components_v1;
\o

\o sql_results/079_QC5_label_timing_mismatch.csv
select
    primary_outcome_flag,
    case when primary_event_time is not null then 1 else 0 end as timing_event_flag,
    count(*) as n
from study_ahf.audit_079_event_timing_components_v1
group by
    primary_outcome_flag,
    case when primary_event_time is not null then 1 else 0 end
order by primary_outcome_flag, timing_event_flag;
\o

\o CS_AHF_hemodynamic_deterioration_ml_project/data/raw/audit_079_event_timing_components_v1.csv
select
    stay_id,
    primary_event_time,
    primary_event_hour_after_landmark,
    primary_event_component_first,
    event_12_36_flag,
    event_12_48_flag,
    event_12_60_flag,
    event_12_60_timing_flag,
    first_support_escalation_time,
    first_nee005_escalation_time,
    first_nee010_escalation_time,
    death_time_12_60,
    pre12_nee_max,
    post12_nee_max,
    post12_nee_delta,
    nee005_escalation_duration_hours,
    nee010_escalation_duration_hours
from study_ahf.audit_079_event_timing_components_v1;
\o

\pset format aligned
\pset footer on
