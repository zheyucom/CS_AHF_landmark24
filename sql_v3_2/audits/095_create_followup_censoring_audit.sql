-- ============================================================
-- Project: CS_AHF_landmark12 v3.2
-- File: sql_v3_2/audits/095_create_followup_censoring_audit.sql
-- Purpose:
--   Characterize 12-60h ICU follow-up completeness and the status
--   of patients who leave the index ICU before the 60h boundary.
--
-- This audit does not alter the outcome. It distinguishes potential
-- competing discharge from simple incomplete observation and detects
-- ICU readmission during the intended prediction horizon.
-- ============================================================

drop table if exists study_ahf_v3_2.audit_095_followup_censoring_v1 cascade;

create table study_ahf_v3_2.audit_095_followup_censoring_v1 as
with base as (
    select *
    from study_ahf_v3_2.audit_094_outcome_label_v1
),

next_icu as (
    select
        b.stay_id,
        min(i.intime) as next_icu_intime
    from base b
    inner join mimiciv_icu.icustays i
        on b.hadm_id = i.hadm_id
       and i.stay_id <> b.stay_id
       and i.intime >= b.outtime
       and i.intime < b.window60_time
    where b.complete60_icu_flag = 0
    group by b.stay_id
),

admission_times as (
    select
        b.stay_id,
        a.dischtime
    from base b
    inner join mimiciv_hosp.admissions a
        on b.hadm_id = a.hadm_id
)

select
    b.stay_id,
    b.subject_id,
    b.hadm_id,
    b.landmark12_time,
    b.window60_time,
    b.outtime as index_icu_outtime,
    b.observed_until_time,
    b.followup_hours_12_60,
    b.complete60_icu_flag,
    a.dischtime as hospital_dischtime,
    n.next_icu_intime,
    b.death_time_12_60,
    b.death_after_icu_discharge_flag,
    b.current_primary_outcome_flag,
    b.current_primary_event_time,
    b.strict_30min_outcome_flag,

    case
        when b.current_primary_event_time is not null
         and b.current_primary_event_time <= b.outtime
        then 1 else 0
    end as current_event_observed_before_icu_exit_flag,

    case
        when b.complete60_icu_flag = 1 then '01_complete60_index_icu'
        when b.death_after_icu_discharge_flag = 1 then '02_death_after_icu_exit'
        when a.dischtime < b.window60_time then '03_hospital_discharge_before60'
        when n.next_icu_intime is not null then '04_icu_readmission_before60'
        else '05_still_hospitalized_non_icu_at60'
    end as followup_status_group,

    case
        when b.complete60_icu_flag = 0
         and a.dischtime < b.window60_time
         and b.death_after_icu_discharge_flag = 0
        then 1 else 0
    end as potential_competing_hospital_discharge_flag,

    case
        when b.complete60_icu_flag = 0
         and n.next_icu_intime is not null
        then 1 else 0
    end as icu_readmission_before60_flag

from base b
left join next_icu n on b.stay_id = n.stay_id
left join admission_times a on b.stay_id = a.stay_id;

