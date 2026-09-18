-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/02_outcome/061C_create_pre12_overt_cs_flags.sql
-- Purpose:
--   Create pre-12h overt CS flags for 12h landmark analysis.
--
-- Main pre12 overt CS:
--   vasoactive/inotrope support within 0-12h
--   AND lactate >=2 mmol/L within 0-12h.
-- ============================================================

drop table if exists study_ahf.outcome_061C_pre12_overt_cs_flags_v1 cascade;

create table study_ahf.outcome_061C_pre12_overt_cs_flags_v1 as
with base as (
    select *
    from study_ahf.cohort_061B_ahf_strict_12h_v1
),

vital_0_12 as (
    select
        b.stay_id,
        count(v.charttime) as pre12_vital_records_n,
        min(v.sbp) as pre12_sbp_min,
        min(v.mbp) as pre12_mbp_min,
        count(v.sbp) filter (where v.sbp < 90) as pre12_sbp_lt90_n,
        count(v.mbp) filter (where v.mbp < 65) as pre12_mbp_lt65_n
    from base b
    left join mimiciv_derived.vitalsign v
        on b.stay_id = v.stay_id
       and v.charttime >= b.intime
       and v.charttime <  b.intime + interval '12 hour'
    group by b.stay_id
),

lactate_0_12 as (
    select
        b.stay_id,
        count(bg.lactate) as pre12_lactate_n,
        max(bg.lactate) as pre12_lactate_max,
        min(bg.charttime) filter (where bg.lactate is not null) as pre12_lactate_first_time,
        count(bg.lactate) filter (where bg.lactate >= 2) as pre12_lactate_ge2_n,
        count(bg.lactate) filter (where bg.lactate >= 4) as pre12_lactate_ge4_n
    from base b
    left join mimiciv_derived.bg bg
        on b.subject_id = bg.subject_id
       and b.hadm_id = bg.hadm_id
       and bg.charttime >= b.intime
       and bg.charttime <  b.intime + interval '12 hour'
    group by b.stay_id
),

uo_0_12 as (
    select
        b.stay_id,
        count(uo.charttime) as pre12_urineoutput_records_n,
        sum(uo.urineoutput) as pre12_urineoutput_total_ml
    from base b
    left join mimiciv_derived.urine_output uo
        on b.stay_id = uo.stay_id
       and uo.charttime >= b.intime
       and uo.charttime <  b.intime + interval '12 hour'
    group by b.stay_id
),

vaso_0_12 as (
    select
        b.stay_id,
        count(va.starttime) as pre12_vaso_records_n,
        min(va.starttime) as pre12_vaso_first_starttime,
        max(va.endtime) as pre12_vaso_last_endtime,

        max(
            case
                when coalesce(va.dopamine, 0) > 0
                  or coalesce(va.epinephrine, 0) > 0
                  or coalesce(va.norepinephrine, 0) > 0
                  or coalesce(va.phenylephrine, 0) > 0
                  or coalesce(va.vasopressin, 0) > 0
                  or coalesce(va.dobutamine, 0) > 0
                  or coalesce(va.milrinone, 0) > 0
                then 1 else 0
            end
        ) as pre12_vasoactive_flag,

        max(case when coalesce(va.norepinephrine, 0) > 0 then 1 else 0 end) as pre12_norepinephrine_flag,
        max(case when coalesce(va.epinephrine, 0) > 0 then 1 else 0 end) as pre12_epinephrine_flag,
        max(case when coalesce(va.dopamine, 0) > 0 then 1 else 0 end) as pre12_dopamine_flag,
        max(case when coalesce(va.dobutamine, 0) > 0 then 1 else 0 end) as pre12_dobutamine_flag,
        max(case when coalesce(va.milrinone, 0) > 0 then 1 else 0 end) as pre12_milrinone_flag,
        max(case when coalesce(va.vasopressin, 0) > 0 then 1 else 0 end) as pre12_vasopressin_flag,
        max(case when coalesce(va.phenylephrine, 0) > 0 then 1 else 0 end) as pre12_phenylephrine_flag

    from base b
    left join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
       and va.starttime <  b.intime + interval '12 hour'
       and coalesce(va.endtime, va.starttime + interval '1 minute') > b.intime
    group by b.stay_id
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.first_careunit,
    b.last_careunit,
    b.intime,
    b.outtime,
    b.icu_los_hours,
    b.gender,
    b.anchor_age,
    b.hf_icd_primary_seq,
    b.hf_icd_acute_or_acute_on_chronic,
    b.iv_loop_rx_early12_flag,
    b.ntprobnp_ge300_early12_flag,
    b.ahf_cohort_definition_12h,

    case
        when b.icu_los_hours >= 12 then 1
        else 0
    end as reached_12h_landmark_flag,

    coalesce(v.pre12_vital_records_n, 0) as pre12_vital_records_n,
    v.pre12_sbp_min,
    v.pre12_mbp_min,
    coalesce(v.pre12_sbp_lt90_n, 0) as pre12_sbp_lt90_n,
    coalesce(v.pre12_mbp_lt65_n, 0) as pre12_mbp_lt65_n,

    case
        when v.pre12_sbp_min < 90
          or v.pre12_mbp_min < 65
        then 1 else 0
    end as pre12_hypotension_any_flag,

    case
        when coalesce(v.pre12_sbp_lt90_n, 0) >= 2
          or coalesce(v.pre12_mbp_lt65_n, 0) >= 2
        then 1 else 0
    end as pre12_hypotension_recurrent_flag,

    coalesce(l.pre12_lactate_n, 0) as pre12_lactate_n,
    l.pre12_lactate_max,
    l.pre12_lactate_first_time,
    coalesce(l.pre12_lactate_ge2_n, 0) as pre12_lactate_ge2_n,
    coalesce(l.pre12_lactate_ge4_n, 0) as pre12_lactate_ge4_n,

    case
        when l.pre12_lactate_max >= 2 then 1
        else 0
    end as pre12_lactate_ge2_flag,

    case
        when l.pre12_lactate_max >= 4 then 1
        else 0
    end as pre12_lactate_ge4_flag,

    coalesce(u.pre12_urineoutput_records_n, 0) as pre12_urineoutput_records_n,
    u.pre12_urineoutput_total_ml,

    case
        when u.pre12_urineoutput_total_ml is not null
         and u.pre12_urineoutput_total_ml < 200
        then 1 else 0
    end as pre12_low_uo_crude_flag,

    coalesce(va.pre12_vaso_records_n, 0) as pre12_vaso_records_n,
    va.pre12_vaso_first_starttime,
    va.pre12_vaso_last_endtime,

    coalesce(va.pre12_vasoactive_flag, 0) as pre12_vasoactive_flag,
    coalesce(va.pre12_norepinephrine_flag, 0) as pre12_norepinephrine_flag,
    coalesce(va.pre12_epinephrine_flag, 0) as pre12_epinephrine_flag,
    coalesce(va.pre12_dopamine_flag, 0) as pre12_dopamine_flag,
    coalesce(va.pre12_dobutamine_flag, 0) as pre12_dobutamine_flag,
    coalesce(va.pre12_milrinone_flag, 0) as pre12_milrinone_flag,
    coalesce(va.pre12_vasopressin_flag, 0) as pre12_vasopressin_flag,
    coalesce(va.pre12_phenylephrine_flag, 0) as pre12_phenylephrine_flag,

    case
        when coalesce(va.pre12_vasoactive_flag, 0) = 1
         and l.pre12_lactate_max >= 2
        then 1 else 0
    end as pre12_overt_cs_main_flag,

    case
        when coalesce(va.pre12_vasoactive_flag, 0) = 1
         and l.pre12_lactate_max >= 4
        then 1 else 0
    end as pre12_overt_cs_very_strict_flag,

    case
        when coalesce(va.pre12_vasoactive_flag, 0) = 1
         and (
                l.pre12_lactate_max >= 2
             or (
                    u.pre12_urineoutput_total_ml is not null
                and u.pre12_urineoutput_total_ml < 200
             )
             or coalesce(v.pre12_sbp_lt90_n, 0) >= 2
             or coalesce(v.pre12_mbp_lt65_n, 0) >= 2
         )
        then 1 else 0
    end as pre12_overt_cs_broad_flag

from base b
left join vital_0_12 v
    on b.stay_id = v.stay_id
left join lactate_0_12 l
    on b.stay_id = l.stay_id
left join uo_0_12 u
    on b.stay_id = u.stay_id
left join vaso_0_12 va
    on b.stay_id = va.stay_id;
		
		
		
		
-- 		质控
select
    count(*) as n_total,

    sum(reached_12h_landmark_flag) as n_reached_12h,
    round(sum(reached_12h_landmark_flag) * 100.0 / count(*), 2) as pct_reached_12h,

    sum(pre12_hypotension_any_flag) as n_hypotension_any,
    round(sum(pre12_hypotension_any_flag) * 100.0 / count(*), 2) as pct_hypotension_any,

    sum(pre12_hypotension_recurrent_flag) as n_hypotension_recurrent,
    round(sum(pre12_hypotension_recurrent_flag) * 100.0 / count(*), 2) as pct_hypotension_recurrent,

    sum(pre12_lactate_ge2_flag) as n_lactate_ge2,
    round(sum(pre12_lactate_ge2_flag) * 100.0 / count(*), 2) as pct_lactate_ge2,

    sum(pre12_lactate_ge4_flag) as n_lactate_ge4,
    round(sum(pre12_lactate_ge4_flag) * 100.0 / count(*), 2) as pct_lactate_ge4,

    sum(pre12_low_uo_crude_flag) as n_low_uo_crude,
    round(sum(pre12_low_uo_crude_flag) * 100.0 / count(*), 2) as pct_low_uo_crude,

    sum(pre12_vasoactive_flag) as n_vasoactive,
    round(sum(pre12_vasoactive_flag) * 100.0 / count(*), 2) as pct_vasoactive,

    sum(pre12_overt_cs_main_flag) as n_pre12_overt_cs_main,
    round(sum(pre12_overt_cs_main_flag) * 100.0 / count(*), 2) as pct_pre12_overt_cs_main,

    sum(pre12_overt_cs_broad_flag) as n_pre12_overt_cs_broad,
    round(sum(pre12_overt_cs_broad_flag) * 100.0 / count(*), 2) as pct_pre12_overt_cs_broad

from study_ahf.outcome_061C_pre12_overt_cs_flags_v1;




