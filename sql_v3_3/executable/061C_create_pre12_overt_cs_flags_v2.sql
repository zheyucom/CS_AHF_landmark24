-- Revised pre-T12 overt-CS path. Lactate comes only from lab_eligible_v1.

drop table if exists study_ahf_v3_3.outcome_061C_pre12_overt_cs_flags_v2 cascade;

create table study_ahf_v3_3.outcome_061C_pre12_overt_cs_flags_v2 as
with base as (
    select *
    from study_ahf_v3_2.cohort_061B_ahf_strict_12h_v1
),
lactate_episode_candidates as (
    select
        b.stay_id,
        le.labevent_id,
        le.availability_time,
        le.result_class,
        le.lower_bound,
        le.upper_bound,
        le.analysis_value,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base b
    join study_ahf_v3_3.lab_eligible_v1 le
     on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.concept = 'lactate'
     and le.charttime >= b.intime
     and le.charttime < b.intime + interval '12 hour'
     and le.availability_time >= b.intime
     and le.availability_time < b.intime + interval '12 hour'
),
lactate_valid as (
    select
        c.*,
        case
            when c.analysis_value >= 2 then 1
            when c.result_class in ('right_censored', 'interval_censored') and c.lower_bound >= 2 then 1
            else 0
        end as definitely_ge2,
        case
            when c.analysis_value >= 4 then 1
            when c.result_class in ('right_censored', 'interval_censored') and c.lower_bound >= 4 then 1
            else 0
        end as definitely_ge4
    from lactate_episode_candidates c
    where c.episode_match_count = 1
      and c.result_class in (
          'exact_numeric', 'right_censored', 'left_censored', 'interval_censored'
      )
),
lactate_0_12 as (
    select
        stay_id,
        count(*) as pre12_lactate_n,
        count(analysis_value) as pre12_lactate_exact_n,
        max(analysis_value) as pre12_lactate_max,
        min(availability_time) filter (where analysis_value is not null) as pre12_lactate_first_time,
        sum(definitely_ge2) as pre12_lactate_ge2_n,
        sum(definitely_ge4) as pre12_lactate_ge4_n
    from lactate_valid
    group by stay_id
),
lactate_episode_audit as (
    select
        stay_id,
        count(*) filter (where episode_match_count > 1) as ambiguous_episode_match_n
    from lactate_episode_candidates
    group by stay_id
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
     and v.charttime < b.intime + interval '12 hour'
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
     and uo.charttime < b.intime + interval '12 hour'
    group by b.stay_id
),
vaso_0_12 as (
    select
        b.stay_id,
        count(va.starttime) as pre12_vaso_records_n,
        min(va.starttime) as pre12_vaso_first_starttime,
        max(va.endtime) as pre12_vaso_last_endtime,
        max(case when coalesce(va.dopamine, 0) > 0
                       or coalesce(va.epinephrine, 0) > 0
                       or coalesce(va.norepinephrine, 0) > 0
                       or coalesce(va.phenylephrine, 0) > 0
                       or coalesce(va.vasopressin, 0) > 0
                       or coalesce(va.dobutamine, 0) > 0
                       or coalesce(va.milrinone, 0) > 0
                 then 1 else 0 end) as pre12_vasoactive_flag
    from base b
    left join mimiciv_derived.vasoactive_agent va
      on b.stay_id = va.stay_id
     and va.starttime < b.intime + interval '12 hour'
     and coalesce(va.endtime, va.starttime + interval '1 minute') > b.intime
    group by b.stay_id
)
select
    b.*,
    case when b.icu_los_hours >= 12 then 1 else 0 end as reached_12h_landmark_flag,
    coalesce(v.pre12_vital_records_n, 0) as pre12_vital_records_n,
    v.pre12_sbp_min,
    v.pre12_mbp_min,
    coalesce(v.pre12_sbp_lt90_n, 0) as pre12_sbp_lt90_n,
    coalesce(v.pre12_mbp_lt65_n, 0) as pre12_mbp_lt65_n,
    case when v.pre12_sbp_min < 90 or v.pre12_mbp_min < 65 then 1 else 0 end as pre12_hypotension_any_flag,
    case when coalesce(v.pre12_sbp_lt90_n, 0) >= 2 or coalesce(v.pre12_mbp_lt65_n, 0) >= 2 then 1 else 0 end as pre12_hypotension_recurrent_flag,
    coalesce(l.pre12_lactate_n, 0) as pre12_lactate_n,
    coalesce(l.pre12_lactate_exact_n, 0) as pre12_lactate_exact_n,
    l.pre12_lactate_max,
    l.pre12_lactate_first_time,
    coalesce(l.pre12_lactate_ge2_n, 0) as pre12_lactate_ge2_n,
    coalesce(l.pre12_lactate_ge4_n, 0) as pre12_lactate_ge4_n,
    case when coalesce(l.pre12_lactate_ge2_n, 0) > 0 then 1 else 0 end as pre12_lactate_ge2_flag,
    case when coalesce(l.pre12_lactate_ge4_n, 0) > 0 then 1 else 0 end as pre12_lactate_ge4_flag,
    coalesce(a.ambiguous_episode_match_n, 0) as lactate_ambiguous_episode_match_n,
    case when coalesce(a.ambiguous_episode_match_n, 0) > 0 then 1 else 0 end as ambiguous_episode_match,
    coalesce(u.pre12_urineoutput_records_n, 0) as pre12_urineoutput_records_n,
    u.pre12_urineoutput_total_ml,
    case when u.pre12_urineoutput_total_ml is not null and u.pre12_urineoutput_total_ml < 200 then 1 else 0 end as pre12_low_uo_crude_flag,
    coalesce(va.pre12_vaso_records_n, 0) as pre12_vaso_records_n,
    va.pre12_vaso_first_starttime,
    va.pre12_vaso_last_endtime,
    coalesce(va.pre12_vasoactive_flag, 0) as pre12_vasoactive_flag,
    case when coalesce(va.pre12_vasoactive_flag, 0) = 1 and coalesce(l.pre12_lactate_ge2_n, 0) > 0 then 1 else 0 end as pre12_overt_cs_main_flag,
    case when coalesce(va.pre12_vasoactive_flag, 0) = 1 and coalesce(l.pre12_lactate_ge4_n, 0) > 0 then 1 else 0 end as pre12_overt_cs_very_strict_flag,
    case when coalesce(va.pre12_vasoactive_flag, 0) = 1 and (
             coalesce(l.pre12_lactate_ge2_n, 0) > 0
          or (u.pre12_urineoutput_total_ml is not null and u.pre12_urineoutput_total_ml < 200)
          or coalesce(v.pre12_sbp_lt90_n, 0) >= 2
          or coalesce(v.pre12_mbp_lt65_n, 0) >= 2
         ) then 1 else 0 end as pre12_overt_cs_broad_flag
from base b
left join vital_0_12 v on b.stay_id = v.stay_id
left join lactate_0_12 l on b.stay_id = l.stay_id
left join lactate_episode_audit a on b.stay_id = a.stay_id
left join uo_0_12 u on b.stay_id = u.stay_id
left join vaso_0_12 va on b.stay_id = va.stay_id;

select
    count(*) as n_total,
    sum(ambiguous_episode_match) as ambiguous_episode_match_n,
    sum(pre12_overt_cs_main_flag) as pre12_overt_cs_main_n
from study_ahf_v3_3.outcome_061C_pre12_overt_cs_flags_v2;
