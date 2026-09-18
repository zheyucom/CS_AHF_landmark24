-- ============================================================
-- Project: CS_AHF_landmark12 v3.2
-- File: sql_v3_2/audits/095_export_followup_censoring_audit.sql
-- Purpose: Export follow-up / competing-discharge audit reports.
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/095_QC1_followup_status.csv
select
    followup_status_group,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct_total,
    sum(current_primary_outcome_flag) as current_events,
    sum(current_event_observed_before_icu_exit_flag) as events_before_icu_exit,
    sum(strict_30min_outcome_flag) as strict_30min_events,
    round(avg(followup_hours_12_60)::numeric, 2) as mean_observed_followup_hours
from study_ahf_v3_2.audit_095_followup_censoring_v1
group by followup_status_group
order by followup_status_group;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/095_QC2_early_exit_timing.csv
select
    count(*) filter (where complete60_icu_flag = 0) as n_early_icu_exit,
    percentile_cont(0.25) within group (order by followup_hours_12_60)
        filter (where complete60_icu_flag = 0) as early_exit_followup_p25_hours,
    percentile_cont(0.50) within group (order by followup_hours_12_60)
        filter (where complete60_icu_flag = 0) as early_exit_followup_p50_hours,
    percentile_cont(0.75) within group (order by followup_hours_12_60)
        filter (where complete60_icu_flag = 0) as early_exit_followup_p75_hours,
    sum(potential_competing_hospital_discharge_flag) as n_hospital_discharge_before60,
    sum(icu_readmission_before60_flag) as n_icu_readmission_before60,
    sum(death_after_icu_discharge_flag) as n_death_after_icu_exit
from study_ahf_v3_2.audit_095_followup_censoring_v1;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/reports/095_QC3_event_before_exit.csv
select
    complete60_icu_flag,
    current_primary_outcome_flag,
    current_event_observed_before_icu_exit_flag,
    count(*) as n
from study_ahf_v3_2.audit_095_followup_censoring_v1
group by
    complete60_icu_flag,
    current_primary_outcome_flag,
    current_event_observed_before_icu_exit_flag
order by
    complete60_icu_flag,
    current_primary_outcome_flag,
    current_event_observed_before_icu_exit_flag;
\o

\o project_control/runs/20260827_v3_2_outcome_label_audit/data/095_patient_level_followup_censoring_audit.csv
select *
from study_ahf_v3_2.audit_095_followup_censoring_v1
order by stay_id;
\o

\pset format aligned
\pset footer on
