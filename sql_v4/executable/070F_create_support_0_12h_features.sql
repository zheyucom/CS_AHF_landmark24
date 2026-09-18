-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/070F_create_support_0_12h_features.sql
-- Purpose:
--   Create 0-12h organ support and severity features.
--
-- Source tables:
--   mimiciv_derived.urine_output
--   mimiciv_derived.gcs
--   mimiciv_derived.ventilation
--   mimiciv_derived.vasoactive_agent
--   mimiciv_derived.norepinephrine_equivalent_dose
--
-- Predictor window:
--   ICU intime <= time < ICU intime + 12h.
--
-- Leakage control:
--   No post-12h information is used as predictor.
-- ============================================================

drop table if exists study_ahf_v4.model_070F_support_0_12h_v1 cascade;

create table study_ahf_v4.model_070F_support_0_12h_v1 as
with base as (
    select *
    from study_ahf_v4.model_070A_base_index_v1
),

-- ------------------------------------------------------------
-- Urine output 0-12h
-- ------------------------------------------------------------
uo_raw as (
    select
        b.stay_id,
        uo.charttime,
        case
            when uo.urineoutput between 0 and 10000 then uo.urineoutput
            else null
        end as urineoutput
    from base b
    left join mimiciv_derived.urine_output uo
        on b.stay_id = uo.stay_id
       and uo.charttime >= b.intime
       and uo.charttime <  b.landmark12_time
),

uo_summary as (
    select
        stay_id,
        count(urineoutput) as urineoutput_0_12h_n,
        sum(urineoutput) as urineoutput_0_12h_total_ml,
        avg(urineoutput) as urineoutput_0_12h_mean_record_ml,
        min(urineoutput) as urineoutput_0_12h_min_record_ml,
        max(urineoutput) as urineoutput_0_12h_max_record_ml
    from uo_raw
    group by stay_id
),

-- ------------------------------------------------------------
-- GCS 0-12h
-- ------------------------------------------------------------
gcs_raw as (
    select
        b.stay_id,
        g.charttime,
        case when g.gcs between 3 and 15 then g.gcs else null end as gcs,
        case when g.gcs_motor between 1 and 6 then g.gcs_motor else null end as gcs_motor,
        case when g.gcs_verbal between 1 and 5 then g.gcs_verbal else null end as gcs_verbal,
        case when g.gcs_eyes between 1 and 4 then g.gcs_eyes else null end as gcs_eyes,
        g.gcs_unable
    from base b
    left join mimiciv_derived.gcs g
        on b.stay_id = g.stay_id
       and g.charttime >= b.intime
       and g.charttime <  b.landmark12_time
),

gcs_summary as (
    select
        stay_id,

        count(gcs) as gcs_n,
        min(gcs) as gcs_min,
        max(gcs) as gcs_max,
        avg(gcs) as gcs_mean,

        min(gcs_motor) as gcs_motor_min,
        max(gcs_motor) as gcs_motor_max,

        min(gcs_verbal) as gcs_verbal_min,
        max(gcs_verbal) as gcs_verbal_max,

        min(gcs_eyes) as gcs_eyes_min,
        max(gcs_eyes) as gcs_eyes_max,

        max(coalesce(gcs_unable, 0)) as gcs_unable_any_flag
    from gcs_raw
    group by stay_id
),

gcs_first as (
    select distinct on (stay_id)
        stay_id,
        gcs as gcs_first
    from gcs_raw
    where gcs is not null
    order by stay_id, charttime
),

gcs_last as (
    select distinct on (stay_id)
        stay_id,
        gcs as gcs_last
    from gcs_raw
    where gcs is not null
    order by stay_id, charttime desc
),

-- ------------------------------------------------------------
-- Ventilation / oxygen support 0-12h
-- ------------------------------------------------------------
vent_raw as (
    select
        b.stay_id,
        v.starttime,
        coalesce(v.endtime, v.starttime + interval '1 minute') as endtime,
        lower(coalesce(v.ventilation_status, '')) as ventilation_status
    from base b
    left join mimiciv_derived.ventilation v
        on b.stay_id = v.stay_id
       and v.starttime <  b.landmark12_time
       and coalesce(v.endtime, v.starttime + interval '1 minute') > b.intime
),

vent_summary as (
    select
        stay_id,

        count(starttime) as ventilation_records_0_12h_n,

        max(
            case
                when ventilation_status like '%invasive%'
                 and ventilation_status not like '%non%'
                then 1 else 0
            end
        ) as invasive_vent_0_12h_flag,

        max(
            case
                when ventilation_status like '%noninvasive%'
                  or ventilation_status like '%non-invasive%'
                  or ventilation_status like '%niv%'
                then 1 else 0
            end
        ) as noninvasive_vent_0_12h_flag,

        max(
            case
                when ventilation_status like '%high flow%'
                  or ventilation_status like '%highflow%'
                  or ventilation_status like '%hfnc%'
                then 1 else 0
            end
        ) as highflow_0_12h_flag,

        max(
            case
                when ventilation_status like '%oxygen%'
                then 1 else 0
            end
        ) as oxygen_0_12h_flag,

        min(starttime) as first_vent_starttime_0_12h

    from vent_raw
    group by stay_id
),

-- ------------------------------------------------------------
-- Vasoactive / inotrope support 0-12h
-- ------------------------------------------------------------
vaso_raw as (
    select
        b.stay_id,
        va.starttime,
        coalesce(va.endtime, va.starttime + interval '1 minute') as endtime,

        va.dopamine,
        va.epinephrine,
        va.norepinephrine,
        va.phenylephrine,
        va.vasopressin,
        va.dobutamine,
        va.milrinone

    from base b
    left join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
       and va.starttime <  b.landmark12_time
       and coalesce(va.endtime, va.starttime + interval '1 minute') > b.intime
),

vaso_summary as (
    select
        stay_id,

        count(starttime) as vaso_records_0_12h_n,

        max(case when coalesce(norepinephrine, 0) > 0 then 1 else 0 end) as norepinephrine_0_12h_flag,
        max(case when coalesce(epinephrine, 0) > 0 then 1 else 0 end) as epinephrine_0_12h_flag,
        max(case when coalesce(dopamine, 0) > 0 then 1 else 0 end) as dopamine_0_12h_flag,
        max(case when coalesce(phenylephrine, 0) > 0 then 1 else 0 end) as phenylephrine_0_12h_flag,
        max(case when coalesce(vasopressin, 0) > 0 then 1 else 0 end) as vasopressin_0_12h_flag,
        max(case when coalesce(dobutamine, 0) > 0 then 1 else 0 end) as dobutamine_0_12h_flag,
        max(case when coalesce(milrinone, 0) > 0 then 1 else 0 end) as milrinone_0_12h_flag,

        max(norepinephrine) as norepinephrine_0_12h_max,
        max(epinephrine) as epinephrine_0_12h_max,
        max(dopamine) as dopamine_0_12h_max,
        max(phenylephrine) as phenylephrine_0_12h_max,
        max(vasopressin) as vasopressin_0_12h_max,
        max(dobutamine) as dobutamine_0_12h_max,
        max(milrinone) as milrinone_0_12h_max,

        min(starttime) as first_vaso_starttime_0_12h

    from vaso_raw
    group by stay_id
),

-- ------------------------------------------------------------
-- Norepinephrine-equivalent dose 0-12h
-- ------------------------------------------------------------
nee_raw as (
    select
        b.stay_id,
        ne.starttime,
        least(
            coalesce(ne.endtime, b.landmark12_time),
            b.landmark12_time
        ) as effective_endtime_pre12,
        ne.norepinephrine_equivalent_dose
    from base b
    left join mimiciv_derived.norepinephrine_equivalent_dose ne
        on b.stay_id = ne.stay_id
       and ne.starttime <  b.landmark12_time
       and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.intime
),

nee_summary as (
    select
        stay_id,
        count(norepinephrine_equivalent_dose) as nee_0_12h_n,
        max(norepinephrine_equivalent_dose) as nee_0_12h_max,
        min(norepinephrine_equivalent_dose) as nee_0_12h_min,
        avg(norepinephrine_equivalent_dose) as nee_0_12h_mean
    from nee_raw
    group by stay_id
),

nee_last as (
    select distinct on (stay_id)
        stay_id,
        norepinephrine_equivalent_dose as nee_0_12h_last
    from nee_raw
    where norepinephrine_equivalent_dose is not null
    order by stay_id, effective_endtime_pre12 desc, starttime desc
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.primary_outcome_flag,

    -- urine output
    u.urineoutput_0_12h_n,
    u.urineoutput_0_12h_total_ml,
    u.urineoutput_0_12h_mean_record_ml,
    u.urineoutput_0_12h_min_record_ml,
    u.urineoutput_0_12h_max_record_ml,

    case
        when u.urineoutput_0_12h_total_ml is not null
         and u.urineoutput_0_12h_total_ml < 200
        then 1 else 0
    end as low_urineoutput_0_12h_crude_flag,

    case when u.urineoutput_0_12h_n > 0 then 1 else 0 end as urineoutput_available_flag,

    -- GCS
    g.gcs_n,
    gf.gcs_first,
    gl.gcs_last,
    g.gcs_min,
    g.gcs_max,
    g.gcs_mean,
    gl.gcs_last - gf.gcs_first as gcs_delta,

    g.gcs_motor_min,
    g.gcs_motor_max,
    g.gcs_verbal_min,
    g.gcs_verbal_max,
    g.gcs_eyes_min,
    g.gcs_eyes_max,
    coalesce(g.gcs_unable_any_flag, 0) as gcs_unable_any_flag,

    case when g.gcs_n > 0 then 1 else 0 end as gcs_available_flag,

    -- ventilation / respiratory support
    coalesce(v.ventilation_records_0_12h_n, 0) as ventilation_records_0_12h_n,
    coalesce(v.invasive_vent_0_12h_flag, 0) as invasive_vent_0_12h_flag,
    coalesce(v.noninvasive_vent_0_12h_flag, 0) as noninvasive_vent_0_12h_flag,
    coalesce(v.highflow_0_12h_flag, 0) as highflow_0_12h_flag,
    coalesce(v.oxygen_0_12h_flag, 0) as oxygen_0_12h_flag,

    case
        when coalesce(v.invasive_vent_0_12h_flag, 0) = 1
          or coalesce(v.noninvasive_vent_0_12h_flag, 0) = 1
          or coalesce(v.highflow_0_12h_flag, 0) = 1
        then 1 else 0
    end as advanced_respiratory_support_0_12h_flag,

    -- vasoactive / inotrope exposure
    coalesce(va.vaso_records_0_12h_n, 0) as vaso_records_0_12h_n,

    coalesce(va.norepinephrine_0_12h_flag, 0) as norepinephrine_0_12h_flag,
    coalesce(va.epinephrine_0_12h_flag, 0) as epinephrine_0_12h_flag,
    coalesce(va.dopamine_0_12h_flag, 0) as dopamine_0_12h_flag,
    coalesce(va.phenylephrine_0_12h_flag, 0) as phenylephrine_0_12h_flag,
    coalesce(va.vasopressin_0_12h_flag, 0) as vasopressin_0_12h_flag,
    coalesce(va.dobutamine_0_12h_flag, 0) as dobutamine_0_12h_flag,
    coalesce(va.milrinone_0_12h_flag, 0) as milrinone_0_12h_flag,

    (
        coalesce(va.norepinephrine_0_12h_flag, 0)
      + coalesce(va.epinephrine_0_12h_flag, 0)
      + coalesce(va.dopamine_0_12h_flag, 0)
      + coalesce(va.phenylephrine_0_12h_flag, 0)
      + coalesce(va.vasopressin_0_12h_flag, 0)
      + coalesce(va.dobutamine_0_12h_flag, 0)
      + coalesce(va.milrinone_0_12h_flag, 0)
    ) as vasoactive_agent_count_0_12h,

    case
        when coalesce(va.norepinephrine_0_12h_flag, 0) = 1
          or coalesce(va.epinephrine_0_12h_flag, 0) = 1
          or coalesce(va.dopamine_0_12h_flag, 0) = 1
          or coalesce(va.phenylephrine_0_12h_flag, 0) = 1
          or coalesce(va.vasopressin_0_12h_flag, 0) = 1
        then 1 else 0
    end as vasopressor_any_0_12h_flag,

    case
        when coalesce(va.dobutamine_0_12h_flag, 0) = 1
          or coalesce(va.milrinone_0_12h_flag, 0) = 1
          or coalesce(va.dopamine_0_12h_flag, 0) = 1
        then 1 else 0
    end as inotrope_any_0_12h_flag,

    va.norepinephrine_0_12h_max,
    va.epinephrine_0_12h_max,
    va.dopamine_0_12h_max,
    va.phenylephrine_0_12h_max,
    va.vasopressin_0_12h_max,
    va.dobutamine_0_12h_max,
    va.milrinone_0_12h_max,

    -- NEE baseline
    coalesce(ne.nee_0_12h_n, 0) as nee_0_12h_n,
    ne.nee_0_12h_max,
    ne.nee_0_12h_min,
    ne.nee_0_12h_mean,
    nl.nee_0_12h_last,

    case when ne.nee_0_12h_n > 0 then 1 else 0 end as nee_available_0_12h_flag

from base b
left join uo_summary u
    on b.stay_id = u.stay_id
left join gcs_summary g
    on b.stay_id = g.stay_id
left join gcs_first gf
    on b.stay_id = gf.stay_id
left join gcs_last gl
    on b.stay_id = gl.stay_id
left join vent_summary v
    on b.stay_id = v.stay_id
left join vaso_summary va
    on b.stay_id = va.stay_id
left join nee_summary ne
    on b.stay_id = ne.stay_id
left join nee_last nl
    on b.stay_id = nl.stay_id;
		
		
		
		
		
-- 		070F QC1：总体人数
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf_v4.model_070F_support_0_12h_v1;



-- 070F QC2：可用率 / 暴露率
select
    count(*) as n_total,

    sum(urineoutput_available_flag) as n_urineoutput_available,
    round(sum(urineoutput_available_flag) * 100.0 / count(*), 2) as pct_urineoutput_available,

    sum(gcs_available_flag) as n_gcs_available,
    round(sum(gcs_available_flag) * 100.0 / count(*), 2) as pct_gcs_available,

    sum(invasive_vent_0_12h_flag) as n_invasive_vent,
    round(sum(invasive_vent_0_12h_flag) * 100.0 / count(*), 2) as pct_invasive_vent,

    sum(advanced_respiratory_support_0_12h_flag) as n_advanced_respiratory_support,
    round(sum(advanced_respiratory_support_0_12h_flag) * 100.0 / count(*), 2) as pct_advanced_respiratory_support,

    sum(vasopressor_any_0_12h_flag) as n_vasopressor_any,
    round(sum(vasopressor_any_0_12h_flag) * 100.0 / count(*), 2) as pct_vasopressor_any,

    sum(inotrope_any_0_12h_flag) as n_inotrope_any,
    round(sum(inotrope_any_0_12h_flag) * 100.0 / count(*), 2) as pct_inotrope_any,

    sum(nee_available_0_12h_flag) as n_nee_available,
    round(sum(nee_available_0_12h_flag) * 100.0 / count(*), 2) as pct_nee_available

from study_ahf_v4.model_070F_support_0_12h_v1;




-- 070F QC3：主要数值范围
select
    count(*) as n_total,

    min(urineoutput_0_12h_total_ml) as uo_total_min,
    percentile_cont(0.5) within group (order by urineoutput_0_12h_total_ml) as uo_total_median,
    max(urineoutput_0_12h_total_ml) as uo_total_max,

    min(gcs_min) as gcs_min_min,
    percentile_cont(0.5) within group (order by gcs_min) as gcs_min_median,
    max(gcs_max) as gcs_max_max,

    min(vasoactive_agent_count_0_12h) as vaso_agent_count_min,
    percentile_cont(0.5) within group (order by vasoactive_agent_count_0_12h) as vaso_agent_count_median,
    max(vasoactive_agent_count_0_12h) as vaso_agent_count_max,

    min(nee_0_12h_max) as nee_max_min,
    percentile_cont(0.5) within group (order by nee_0_12h_max) as nee_max_median,
    max(nee_0_12h_max) as nee_max_max

from study_ahf_v4.model_070F_support_0_12h_v1;




-- 070F QC4：事件率按 0–12 h 血管活性药种类数分层
select
    case
        when vasoactive_agent_count_0_12h = 0 then '00_none'
        when vasoactive_agent_count_0_12h = 1 then '01_one_agent'
        when vasoactive_agent_count_0_12h = 2 then '02_two_agents'
        when vasoactive_agent_count_0_12h >= 3 then '03_three_or_more'
        else '99_other'
    end as vaso_agent_count_group,

    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate

from study_ahf_v4.model_070F_support_0_12h_v1
group by
    case
        when vasoactive_agent_count_0_12h = 0 then '00_none'
        when vasoactive_agent_count_0_12h = 1 then '01_one_agent'
        when vasoactive_agent_count_0_12h = 2 then '02_two_agents'
        when vasoactive_agent_count_0_12h >= 3 then '03_three_or_more'
        else '99_other'
    end
order by vaso_agent_count_group;




-- 070F QC5：事件率按 GCS 最低值分层
select
    case
        when gcs_min is null then '00_missing'
        when gcs_min <= 8 then '01_gcs_le8'
        when gcs_min between 9 and 12 then '02_gcs_9_12'
        when gcs_min between 13 and 15 then '03_gcs_13_15'
        else '99_other'
    end as gcs_min_group,

    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate

from study_ahf_v4.model_070F_support_0_12h_v1
group by
    case
        when gcs_min is null then '00_missing'
        when gcs_min <= 8 then '01_gcs_le8'
        when gcs_min between 9 and 12 then '02_gcs_9_12'
        when gcs_min between 13 and 15 then '03_gcs_13_15'
        else '99_other'
    end
order by gcs_min_group;




