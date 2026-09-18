-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/audits/097_export_person_period_qc.sql
-- Purpose: QC and export the one-hour person-period table.
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o project_control/runs/20260827_v3_3_person_period/reports/097_QC1_overall.csv
select
    count(*) as n_person_period_rows,
    count(distinct stay_id) as n_stays,
    min(period_index) as min_period_index,
    max(period_index) as max_period_index,
    sum(event_period_flag) as n_event_terminal_rows,
    sum(compete_period_flag) as n_compete_terminal_rows,
    sum(censor_period_flag) as n_censor_terminal_rows,
    sum(case when period_status = 'at_risk' then 1 else 0 end) as n_at_risk_rows
from study_ahf_v3_2.model_097_person_period_v33_v1;
\o

\o project_control/runs/20260827_v3_3_person_period/reports/097_QC2_state_and_terminal_rows.csv
select
    final_state,
    count(distinct stay_id) as n_stays,
    count(*) as n_person_period_rows,
    sum(event_period_flag) as n_event_terminal_rows,
    sum(compete_period_flag) as n_compete_terminal_rows,
    sum(censor_period_flag) as n_censor_terminal_rows,
    round(avg(period_index)::numeric, 3) as mean_terminal_or_last_period_index,
    min(period_index) as min_period_index,
    max(period_index) as max_period_index
from study_ahf_v3_2.model_097_person_period_v33_v1
group by final_state
order by final_state;
\o

\o project_control/runs/20260827_v3_3_person_period/reports/097_QC3_event_type.csv
select
    event_type,
    count(distinct stay_id) as n_stays,
    sum(event_period_flag) as n_terminal_rows
from study_ahf_v3_2.model_097_person_period_v33_v1
where final_state = 'event'
group by event_type
order by event_type;
\o

\o project_control/runs/20260827_v3_3_person_period/reports/097_QC4_one_terminal_row_per_stay.csv
with terminal as (
    select
        stay_id,
        sum(event_period_flag + compete_period_flag + censor_period_flag) as n_terminal_rows,
        max(final_state) as final_state
    from study_ahf_v3_2.model_097_person_period_v33_v1
    group by stay_id
)
select
    n_terminal_rows,
    count(*) as n_stays
from terminal
group by n_terminal_rows
order by n_terminal_rows;
\o

\o project_control/runs/20260827_v3_3_person_period/reports/097_QC5_time_and_duration.csv
select
    count(*) as n_rows,
    sum(case when period_end <= period_start then 1 else 0 end) as n_nonpositive_intervals,
    sum(case when period_duration_hours > 1.000001 then 1 else 0 end) as n_intervals_over_1h,
    sum(case when hours_from_landmark_start < 0 then 1 else 0 end) as n_before_t12,
    sum(case when hours_from_landmark_end > 48.000001 then 1 else 0 end) as n_after_t60,
    min(period_duration_hours) as min_duration_hours,
    max(period_duration_hours) as max_duration_hours,
    sum(period_duration_hours) as total_person_time_hours
from study_ahf_v3_2.model_097_person_period_v33_v1;
\o

\o project_control/runs/20260827_v3_3_person_period/reports/097_QC6_sepsis_stratum.csv
select
    early_sepsis12_main_flag,
    count(distinct stay_id) as n_stays,
    sum(event_period_flag) as n_events,
    sum(compete_period_flag) as n_competes,
    sum(censor_period_flag) as n_censors,
    round(sum(event_period_flag) * 100.0 / count(distinct stay_id), 2) as events_per_stay_pct
from study_ahf_v3_2.model_097_person_period_v33_v1
group by early_sepsis12_main_flag
order by early_sepsis12_main_flag;
\o

\o project_control/runs/20260827_v3_3_person_period/data/097_person_period_v33.csv
select *
from study_ahf_v3_2.model_097_person_period_v33_v1
order by stay_id, period_index;
\o

\pset format aligned
\pset footer on
