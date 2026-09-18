-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/modeling/097_create_person_period_v33_reconciled.sql
-- Purpose:
--   Build the reconciled one-hour person-period table after the
--   explicit T12 landmark eligibility audit (098).
--
--   This is the reproducible v2 replacement for the historical
--   097 v1 table. The historical SQL/table are retained unchanged.
-- ============================================================

drop table if exists study_ahf_v3_2.model_097_person_period_v33_v2 cascade;

create table study_ahf_v3_2.model_097_person_period_v33_v2 as
with source as (
    select
        l.*,
        l.landmark12_time as t12,
        l.window60_time as t60
    from study_ahf_v3_2.model_098_strict_label_v33_v1 l
    where l.landmark_ineligible_flag = 0
),

period_grid as (
    select
        s.stay_id,
        g.period_index,
        s.subject_id,
        s.hadm_id,
        s.intime,
        s.outtime,
        s.t12,
        s.t60,
        s.final_state,
        s.final_time,
        s.event_type,
        s.early_sepsis12_main_flag,
        s.death_after_exit_flag,
        s.pre12_max_agent_count,
        s.pre12_nee_max,
        s.pre12_nee_last,
        s.pre12_nee_historic,
        s.esc_confirm_time,
        s.in_icu_death_time,
        s.esc_confirm_time_bridge5,
        (s.final_state = 'event' and s.event_type = 'escalation')
            as final_escalation_event_flag,
        (s.final_state = 'event' and s.event_type = 'in_icu_death')
            as final_in_icu_death_flag,
        (s.final_state = 'compete') as final_compete_flag,
        (s.final_state = 'censor') as final_admin_censor_flag,
        s.t12 + (g.period_index * interval '1 hour') as period_start,
        least(
            s.t12 + ((g.period_index + 1) * interval '1 hour'),
            s.final_time
        ) as period_end
    from source s
    cross join lateral generate_series(0, 47) as g(period_index)
    where s.t12 + (g.period_index * interval '1 hour') < s.final_time
),

classified as (
    select
        p.*,
        extract(epoch from (p.period_end - p.period_start)) / 3600.0
            as period_duration_hours,
        case
            when p.final_state = 'event'
             and p.final_time > p.period_start
             and p.final_time <= p.period_end
            then 1 else 0
        end as event_period_flag,
        case
            when p.final_state = 'compete'
             and p.final_time > p.period_start
             and p.final_time <= p.period_end
            then 1 else 0
        end as compete_period_flag,
        case
            when p.final_state = 'censor'
             and p.final_time > p.period_start
             and p.final_time <= p.period_end
            then 1 else 0
        end as censor_period_flag
    from period_grid p
)

select
    stay_id,
    subject_id,
    hadm_id,
    intime,
    outtime,
    t12 as landmark12_time,
    t60 as window60_time,
    period_index,
    period_start,
    period_end,
    period_duration_hours,
    extract(epoch from (period_start - t12)) / 3600.0
        as hours_from_landmark_start,
    extract(epoch from (period_end - t12)) / 3600.0
        as hours_from_landmark_end,
    final_state,
    final_time,
    event_type,
    early_sepsis12_main_flag,
    death_after_exit_flag,
    pre12_max_agent_count,
    pre12_nee_max,
    pre12_nee_last,
    pre12_nee_historic,
    esc_confirm_time,
    in_icu_death_time,
    esc_confirm_time_bridge5,
    final_escalation_event_flag,
    final_in_icu_death_flag,
    final_compete_flag,
    final_admin_censor_flag,
    event_period_flag,
    compete_period_flag,
    censor_period_flag,
    case
        when event_period_flag = 1 then 1
        when compete_period_flag = 1 then 2
        when censor_period_flag = 1 then 0
        else 0
    end as period_status_code,
    case
        when event_period_flag = 1 then 'event'
        when compete_period_flag = 1 then 'compete'
        when censor_period_flag = 1 then 'censor'
        else 'at_risk'
    end as period_status
from classified
where period_duration_hours > 0;

create index if not exists idx_097_person_period_v33_v2_stay_period
    on study_ahf_v3_2.model_097_person_period_v33_v2 (stay_id, period_index);

create index if not exists idx_097_person_period_v33_v2_status
    on study_ahf_v3_2.model_097_person_period_v33_v2 (period_status);

analyze study_ahf_v3_2.model_097_person_period_v33_v2;

