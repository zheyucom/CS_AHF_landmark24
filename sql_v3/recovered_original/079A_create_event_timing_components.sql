-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/04_audit/079A_create_event_timing_components.sql
-- Purpose:
--   Create patient-level event timing table for 12-60 h
--   hemodynamic deterioration outcome components.
--
-- Main uses:
--   1. Audit primary event timing.
--   2. Build 12-36 h / 12-48 h / 12-60 h window outcomes.
--   3. Quantify post12 NEE escalation duration.
--   4. Distinguish support escalation vs NEE escalation vs death.
--
-- Important:
--   This is an audit / outcome table.
--   Do NOT use post12 variables as predictors.
-- ============================================================

create schema if not exists study_ahf;

drop table if exists study_ahf.audit_079_event_timing_components_v1 cascade;

create table study_ahf.audit_079_event_timing_components_v1 as
with base as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        b.intime,
        b.landmark12_time,
        b.window60_time,

        b.primary_outcome_flag,
        b.label_support_escalation_flag,
        b.label_nee_escalation_flag,
        b.label_death_12_60_flag,
        b.label_hd_nee010_flag,
        b.label_hd_no_nee_flag

    from study_ahf.model_070G_modeling_dataset_v1 b
),

-- ------------------------------------------------------------
-- Pre12 vasoactive / inotrope exposure baseline
-- ------------------------------------------------------------
pre12_vaso_rows as (
    select
        b.stay_id,
        va.starttime,
        coalesce(va.endtime, va.starttime + interval '1 minute') as endtime,

        case when coalesce(va.norepinephrine, 0) > 0 then 1 else 0 end as norepinephrine_flag,
        case when coalesce(va.epinephrine, 0) > 0 then 1 else 0 end as epinephrine_flag,
        case when coalesce(va.dopamine, 0) > 0 then 1 else 0 end as dopamine_flag,
        case when coalesce(va.phenylephrine, 0) > 0 then 1 else 0 end as phenylephrine_flag,
        case when coalesce(va.vasopressin, 0) > 0 then 1 else 0 end as vasopressin_flag,
        case when coalesce(va.dobutamine, 0) > 0 then 1 else 0 end as dobutamine_flag,
        case when coalesce(va.milrinone, 0) > 0 then 1 else 0 end as milrinone_flag

    from base b
    join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
       and va.starttime < b.landmark12_time
       and coalesce(va.endtime, va.starttime + interval '1 minute') > b.intime
),

pre12_vaso_summary as (
    select
        stay_id,

        max(norepinephrine_flag) as pre12_norepinephrine_flag,
        max(epinephrine_flag) as pre12_epinephrine_flag,
        max(dopamine_flag) as pre12_dopamine_flag,
        max(phenylephrine_flag) as pre12_phenylephrine_flag,
        max(vasopressin_flag) as pre12_vasopressin_flag,
        max(dobutamine_flag) as pre12_dobutamine_flag,
        max(milrinone_flag) as pre12_milrinone_flag,

        max(
            norepinephrine_flag
          + epinephrine_flag
          + dopamine_flag
          + phenylephrine_flag
          + vasopressin_flag
          + dobutamine_flag
          + milrinone_flag
        ) as pre12_max_agent_count

    from pre12_vaso_rows
    group by stay_id
),

-- ------------------------------------------------------------
-- Post12 vasoactive / inotrope rows and first support escalation
-- ------------------------------------------------------------
post12_vaso_rows as (
    select
        b.stay_id,

        greatest(va.starttime, b.landmark12_time) as effective_starttime,
        least(
            coalesce(va.endtime, va.starttime + interval '1 minute'),
            b.window60_time
        ) as effective_endtime,

        case when coalesce(va.norepinephrine, 0) > 0 then 1 else 0 end as norepinephrine_flag,
        case when coalesce(va.epinephrine, 0) > 0 then 1 else 0 end as epinephrine_flag,
        case when coalesce(va.dopamine, 0) > 0 then 1 else 0 end as dopamine_flag,
        case when coalesce(va.phenylephrine, 0) > 0 then 1 else 0 end as phenylephrine_flag,
        case when coalesce(va.vasopressin, 0) > 0 then 1 else 0 end as vasopressin_flag,
        case when coalesce(va.dobutamine, 0) > 0 then 1 else 0 end as dobutamine_flag,
        case when coalesce(va.milrinone, 0) > 0 then 1 else 0 end as milrinone_flag

    from base b
    join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
       and va.starttime < b.window60_time
       and coalesce(va.endtime, va.starttime + interval '1 minute') > b.landmark12_time
),

post12_support_events as (
    select
        p.stay_id,
        p.effective_starttime,

        (
            p.norepinephrine_flag
          + p.epinephrine_flag
          + p.dopamine_flag
          + p.phenylephrine_flag
          + p.vasopressin_flag
          + p.dobutamine_flag
          + p.milrinone_flag
        ) as post_agent_count,

        case
            when p.norepinephrine_flag = 1
             and coalesce(pre.pre12_norepinephrine_flag, 0) = 0
            then 1 else 0
        end as new_norepinephrine_flag,

        case
            when p.epinephrine_flag = 1
             and coalesce(pre.pre12_epinephrine_flag, 0) = 0
            then 1 else 0
        end as new_epinephrine_flag,

        case
            when p.dopamine_flag = 1
             and coalesce(pre.pre12_dopamine_flag, 0) = 0
            then 1 else 0
        end as new_dopamine_flag,

        case
            when p.phenylephrine_flag = 1
             and coalesce(pre.pre12_phenylephrine_flag, 0) = 0
            then 1 else 0
        end as new_phenylephrine_flag,

        case
            when p.vasopressin_flag = 1
             and coalesce(pre.pre12_vasopressin_flag, 0) = 0
            then 1 else 0
        end as new_vasopressin_flag,

        case
            when p.dobutamine_flag = 1
             and coalesce(pre.pre12_dobutamine_flag, 0) = 0
            then 1 else 0
        end as new_dobutamine_flag,

        case
            when p.milrinone_flag = 1
             and coalesce(pre.pre12_milrinone_flag, 0) = 0
            then 1 else 0
        end as new_milrinone_flag,

        coalesce(pre.pre12_max_agent_count, 0) as pre12_max_agent_count

    from post12_vaso_rows p
    left join pre12_vaso_summary pre
        on p.stay_id = pre.stay_id
),

first_support_escalation as (
    select
        stay_id,
        min(effective_starttime) as first_support_escalation_time
    from post12_support_events
    where
        post_agent_count > pre12_max_agent_count
        or new_norepinephrine_flag = 1
        or new_epinephrine_flag = 1
        or new_dopamine_flag = 1
        or new_phenylephrine_flag = 1
        or new_vasopressin_flag = 1
        or new_dobutamine_flag = 1
        or new_milrinone_flag = 1
    group by stay_id
),

-- ------------------------------------------------------------
-- Pre12 NEE baseline
-- ------------------------------------------------------------
pre12_nee as (
    select
        b.stay_id,
        max(coalesce(ne.norepinephrine_equivalent_dose, 0)) as pre12_nee_max
    from base b
    join mimiciv_derived.norepinephrine_equivalent_dose ne
        on b.stay_id = ne.stay_id
       and ne.starttime < b.landmark12_time
       and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.intime
    group by b.stay_id
),

-- ------------------------------------------------------------
-- Post12 NEE rows
-- ------------------------------------------------------------
post12_nee_rows as (
    select
        b.stay_id,

        greatest(ne.starttime, b.landmark12_time) as effective_starttime,
        least(
            coalesce(ne.endtime, ne.starttime + interval '1 minute'),
            b.window60_time
        ) as effective_endtime,

        coalesce(ne.norepinephrine_equivalent_dose, 0) as norepinephrine_equivalent_dose,

        coalesce(pre.pre12_nee_max, 0) as pre12_nee_max

    from base b
    join mimiciv_derived.norepinephrine_equivalent_dose ne
        on b.stay_id = ne.stay_id
       and ne.starttime < b.window60_time
       and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.landmark12_time
    left join pre12_nee pre
        on b.stay_id = pre.stay_id
),

post12_nee_summary as (
    select
        stay_id,

        max(norepinephrine_equivalent_dose) as post12_nee_max,

        max(norepinephrine_equivalent_dose - pre12_nee_max) as post12_nee_delta,

        min(
            case
                when norepinephrine_equivalent_dose - pre12_nee_max >= 0.05
                then effective_starttime
                else null
            end
        ) as first_nee005_escalation_time,

        min(
            case
                when norepinephrine_equivalent_dose - pre12_nee_max >= 0.10
                then effective_starttime
                else null
            end
        ) as first_nee010_escalation_time,

        sum(
            case
                when norepinephrine_equivalent_dose - pre12_nee_max >= 0.05
                then greatest(extract(epoch from (effective_endtime - effective_starttime)) / 3600.0, 0)
                else 0
            end
        ) as nee005_escalation_duration_hours,

        sum(
            case
                when norepinephrine_equivalent_dose - pre12_nee_max >= 0.10
                then greatest(extract(epoch from (effective_endtime - effective_starttime)) / 3600.0, 0)
                else 0
            end
        ) as nee010_escalation_duration_hours

    from post12_nee_rows
    group by stay_id
),

-- ------------------------------------------------------------
-- Death time
-- ------------------------------------------------------------
death_12_60 as (
    select
        b.stay_id,
        a.deathtime as death_time_12_60
    from base b
    join mimiciv_hosp.admissions a
        on b.hadm_id = a.hadm_id
    where a.deathtime >= b.landmark12_time
      and a.deathtime <  b.window60_time
),

-- ------------------------------------------------------------
-- Merge component times
-- ------------------------------------------------------------
merged as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        b.intime,
        b.landmark12_time,
        b.window60_time,

        b.primary_outcome_flag,
        b.label_support_escalation_flag,
        b.label_nee_escalation_flag,
        b.label_death_12_60_flag,
        b.label_hd_nee010_flag,
        b.label_hd_no_nee_flag,

        coalesce(prev.pre12_max_agent_count, 0) as pre12_max_agent_count,
        coalesce(pre_nee.pre12_nee_max, 0) as pre12_nee_max,

        fs.first_support_escalation_time,
        ps.first_nee005_escalation_time,
        ps.first_nee010_escalation_time,
        d.death_time_12_60,

        ps.post12_nee_max,
        ps.post12_nee_delta,
        ps.nee005_escalation_duration_hours,
        ps.nee010_escalation_duration_hours

    from base b
    left join pre12_vaso_summary prev
        on b.stay_id = prev.stay_id
    left join pre12_nee pre_nee
        on b.stay_id = pre_nee.stay_id
    left join first_support_escalation fs
        on b.stay_id = fs.stay_id
    left join post12_nee_summary ps
        on b.stay_id = ps.stay_id
    left join death_12_60 d
        on b.stay_id = d.stay_id
),

first_event as (
    select
        m.*,

        least(
            coalesce(first_support_escalation_time, timestamp '9999-12-31'),
            coalesce(first_nee005_escalation_time, timestamp '9999-12-31'),
            coalesce(death_time_12_60, timestamp '9999-12-31')
        ) as primary_event_time_raw

    from merged m
)

select
    subject_id,
    hadm_id,
    stay_id,
    intime,
    landmark12_time,
    window60_time,

    primary_outcome_flag,
    label_support_escalation_flag,
    label_nee_escalation_flag,
    label_death_12_60_flag,
    label_hd_nee010_flag,
    label_hd_no_nee_flag,

    pre12_max_agent_count,
    pre12_nee_max,

    first_support_escalation_time,
    first_nee005_escalation_time,
    first_nee010_escalation_time,
    death_time_12_60,

    post12_nee_max,
    post12_nee_delta,
    coalesce(nee005_escalation_duration_hours, 0) as nee005_escalation_duration_hours,
    coalesce(nee010_escalation_duration_hours, 0) as nee010_escalation_duration_hours,

    case
        when primary_outcome_flag = 0
          or primary_event_time_raw = timestamp '9999-12-31'
        then null
        else primary_event_time_raw
    end as primary_event_time,

    case
        when primary_outcome_flag = 0
          or primary_event_time_raw = timestamp '9999-12-31'
        then null
        else extract(epoch from (primary_event_time_raw - landmark12_time)) / 3600.0
    end as primary_event_hour_after_landmark,

    case
        when primary_outcome_flag = 0
        then null
        when primary_event_time_raw = first_support_escalation_time
        then 'support_escalation'
        when primary_event_time_raw = first_nee005_escalation_time
        then 'nee005_escalation'
        when primary_event_time_raw = death_time_12_60
        then 'death'
        else null
    end as primary_event_component_first,

    case
        when primary_outcome_flag = 1
         and primary_event_time_raw <> timestamp '9999-12-31'
         and primary_event_time_raw < landmark12_time + interval '24 hour'
        then 1 else 0
    end as event_12_36_flag,

    case
        when primary_outcome_flag = 1
         and primary_event_time_raw <> timestamp '9999-12-31'
         and primary_event_time_raw < landmark12_time + interval '36 hour'
        then 1 else 0
    end as event_12_48_flag,

    case
        when primary_outcome_flag = 1
         and primary_event_time_raw <> timestamp '9999-12-31'
         and primary_event_time_raw < landmark12_time + interval '48 hour'
        then 1 else 0
    end as event_12_60_flag,

    case
        when primary_outcome_flag = 1
         and primary_event_time_raw <> timestamp '9999-12-31'
         and primary_event_time_raw < landmark12_time + interval '48 hour'
        then 1 else 0
    end as event_12_60_timing_flag

from first_event;

create index if not exists idx_audit_079_event_timing_stay
    on study_ahf.audit_079_event_timing_components_v1 (stay_id);

create index if not exists idx_audit_079_event_timing_event_hour
    on study_ahf.audit_079_event_timing_components_v1 (primary_event_hour_after_landmark);

analyze study_ahf.audit_079_event_timing_components_v1;

insert into study_ahf.run_manifest (
    table_name,
    sql_file,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    n_events,
    event_rate,
    time_window,
    version_tag,
    notes
)
select
    'study_ahf.audit_079_event_timing_components_v1' as table_name,
    'sql/04_audit/079A_create_event_timing_components.sql' as sql_file,
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(event_12_60_timing_flag) as n_events,
    sum(event_12_60_timing_flag)::numeric / nullif(count(*), 0) as event_rate,
    '12-60h after ICU admission; 0-48h after 12h landmark' as time_window,
    '079A_v1' as version_tag,
    'Audit-only patient-level event timing, post12 NEE, and component timing table. Do not use post12 fields as predictors.' as notes
from study_ahf.audit_079_event_timing_components_v1;
