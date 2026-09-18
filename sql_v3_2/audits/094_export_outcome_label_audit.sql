-- ============================================================
-- Project: CS_AHF_landmark12 v3.2
-- File: sql_v3_2/audits/094_export_outcome_label_audit.sql
-- Purpose: Export label-audit QC reports and stay-level audit data.
-- Usage: psql -f 094_export_outcome_label_audit.sql
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/094_QC1_outcome_component_overall.csv
select
    count(*) as n_total,
    sum(current_primary_outcome_flag) as n_current_primary_events,
    round(sum(current_primary_outcome_flag) * 100.0 / count(*), 2) as current_primary_event_rate,
    sum(current_support_component_flag) as n_current_support_component,
    sum(current_nee005_component_flag) as n_current_nee005_component,
    sum(death_12_60_flag) as n_death_12_60,
    sum(strict_30min_outcome_flag) as n_strict_30min_events,
    round(sum(strict_30min_outcome_flag) * 100.0 / count(*), 2) as strict_30min_event_rate,
    sum(strict_60min_outcome_flag) as n_strict_60min_events,
    round(sum(strict_60min_outcome_flag) * 100.0 / count(*), 2) as strict_60min_event_rate,
    sum(strict_nee010_30min_outcome_flag) as n_strict_nee010_30min_events,
    round(sum(strict_nee010_30min_outcome_flag) * 100.0 / count(*), 2) as strict_nee010_30min_event_rate
from study_ahf_v3_2.audit_094_outcome_label_v1;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/094_QC2_support_component_audit.csv
select
    support_event_type,
    support_concurrent_escalation_flag,
    support_durable_30min_flag,
    support_durable_60min_flag,
    support_concurrent_durable_30min_flag,
    support_phenylephrine_only_flag,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct_all,
    sum(current_primary_outcome_flag) as n_current_primary_events
from study_ahf_v3_2.audit_094_outcome_label_v1
group by
    support_event_type,
    support_concurrent_escalation_flag,
    support_durable_30min_flag,
    support_durable_60min_flag,
    support_concurrent_durable_30min_flag,
    support_phenylephrine_only_flag
order by n desc;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/094_QC3_nee_persistence.csv
select
    count(*) as n_total,
    sum(current_nee005_component_flag) as n_current_nee005,
    sum(nee005_persistent_30min_flag) as n_nee005_persistent_30min,
    sum(nee005_persistent_60min_flag) as n_nee005_persistent_60min,
    percentile_cont(0.25) within group (order by nee005_max_continuous_duration_hours)
        filter (where current_nee005_component_flag = 1) as nee005_duration_p25_hours,
    percentile_cont(0.50) within group (order by nee005_max_continuous_duration_hours)
        filter (where current_nee005_component_flag = 1) as nee005_duration_p50_hours,
    percentile_cont(0.75) within group (order by nee005_max_continuous_duration_hours)
        filter (where current_nee005_component_flag = 1) as nee005_duration_p75_hours,
    sum(current_nee010_component_flag) as n_current_nee010,
    sum(nee010_persistent_30min_flag) as n_nee010_persistent_30min,
    sum(nee010_persistent_60min_flag) as n_nee010_persistent_60min,
    percentile_cont(0.50) within group (order by nee010_max_continuous_duration_hours)
        filter (where current_nee010_component_flag = 1) as nee010_duration_p50_hours
from study_ahf_v3_2.audit_094_outcome_label_v1;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/094_QC4_phenylephrine_and_death.csv
select
    support_phenylephrine_only_flag,
    death_after_icu_discharge_flag,
    complete60_icu_flag,
    count(*) as n,
    sum(current_primary_outcome_flag) as current_events,
    sum(strict_30min_outcome_flag) as strict_30min_events,
    round(sum(current_primary_outcome_flag) * 100.0 / count(*), 2) as current_event_rate
from study_ahf_v3_2.audit_094_outcome_label_v1
group by support_phenylephrine_only_flag, death_after_icu_discharge_flag, complete60_icu_flag
order by support_phenylephrine_only_flag, death_after_icu_discharge_flag, complete60_icu_flag;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/094_QC5_event_timing.csv
select
    current_primary_event_component_first,
    count(*) as n_events,
    percentile_cont(0.25) within group (order by current_primary_event_hour_after_landmark) as p25_hour,
    percentile_cont(0.50) within group (order by current_primary_event_hour_after_landmark) as p50_hour,
    percentile_cont(0.75) within group (order by current_primary_event_hour_after_landmark) as p75_hour,
    min(current_primary_event_hour_after_landmark) as min_hour,
    max(current_primary_event_hour_after_landmark) as max_hour
from study_ahf_v3_2.audit_094_outcome_label_v1
where current_primary_event_time is not null
group by current_primary_event_component_first
order by n_events desc;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/094_QC6_censoring_sensitivity.csv
select
    complete60_icu_flag,
    count(*) as n,
    sum(current_primary_outcome_flag) as current_events,
    round(sum(current_primary_outcome_flag) * 100.0 / count(*), 2) as current_event_rate,
    sum(strict_30min_outcome_flag) as strict_30min_events,
    round(sum(strict_30min_outcome_flag) * 100.0 / count(*), 2) as strict_30min_event_rate,
    sum(case when current_primary_event_time is not null then 1 else 0 end) as n_timed_current_events,
    round(avg(followup_hours_12_60)::numeric, 2) as mean_followup_hours
from study_ahf_v3_2.audit_094_outcome_label_v1
group by complete60_icu_flag
order by complete60_icu_flag;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/data/094_patient_level_outcome_label_audit.csv
select *
from study_ahf_v3_2.audit_094_outcome_label_v1
order by stay_id;
\o

\pset format aligned
\pset footer on
