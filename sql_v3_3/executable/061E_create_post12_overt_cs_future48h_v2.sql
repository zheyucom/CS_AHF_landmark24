-- Revised post-T12 overt-CS path. Historical v1 remains unchanged.
-- Lactate must be sampled after T12 and available before end of observable follow-up.

drop table if exists study_ahf_v3_3.outcome_061E_post12_overt_cs_future48h_main_v2 cascade;

create table study_ahf_v3_3.outcome_061E_post12_overt_cs_future48h_main_v2 as
with base as (
    select
        b.*,
        a.deathtime,
        b.intime + interval '12 hour' as landmark12_time,
        b.intime + interval '60 hour' as window60_time,
        least(b.outtime, b.intime + interval '60 hour') as observed_until_time,
        case when b.outtime >= b.intime + interval '60 hour' then 1 else 0 end as complete60_icu_flag
    from study_ahf_v3_2.cohort_061D_landmark12_riskset_main_v1 b
    left join mimiciv_hosp.admissions a
      on b.subject_id = a.subject_id
     and b.hadm_id = a.hadm_id
),
base_followup as (
    select
        b.*,
        extract(epoch from (observed_until_time - landmark12_time)) / 3600.0 as followup_hours_12_60,
        case when deathtime >= landmark12_time and deathtime < window60_time then 1 else 0 end as death_12_60_flag
    from base b
    where observed_until_time > landmark12_time
),
lactate_episode_candidates as (
    select
        b.stay_id,
        le.labevent_id,
        le.charttime,
        le.availability_time,
        le.result_class,
        le.lower_bound,
        le.upper_bound,
        le.analysis_value,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base_followup b
    join study_ahf_v3_3.lab_eligible_v1 le
      on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.concept = 'lactate'
     and le.charttime >= b.landmark12_time
     and le.charttime < b.observed_until_time
     and le.availability_time >= b.landmark12_time
     and le.availability_time < b.observed_until_time
),
lactate_window as (
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
lactate_summary as (
    select
        stay_id,
        count(*) as post12_lactate_n,
        count(analysis_value) as post12_lactate_exact_n,
        max(analysis_value) as post12_lactate_max,
        min(charttime) filter (where definitely_ge2 = 1) as post12_lactate_ge2_first_time,
        min(charttime) filter (where definitely_ge4 = 1) as post12_lactate_ge4_first_time,
        sum(definitely_ge2) as post12_lactate_ge2_n,
        sum(definitely_ge4) as post12_lactate_ge4_n
    from lactate_window
    group by stay_id
),
lactate_episode_audit as (
    select
        stay_id,
        count(*) filter (where episode_match_count > 1) as ambiguous_episode_match_n
    from lactate_episode_candidates
    group by stay_id
),
vaso_window as (
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
    from base_followup b
    join mimiciv_derived.vasoactive_agent va
      on b.stay_id = va.stay_id
     and va.starttime < b.observed_until_time
     and coalesce(va.endtime, va.starttime + interval '1 minute') > b.landmark12_time
    where coalesce(va.dopamine, 0) > 0
       or coalesce(va.epinephrine, 0) > 0
       or coalesce(va.norepinephrine, 0) > 0
       or coalesce(va.phenylephrine, 0) > 0
       or coalesce(va.vasopressin, 0) > 0
       or coalesce(va.dobutamine, 0) > 0
       or coalesce(va.milrinone, 0) > 0
),
vaso_summary as (
    select
        stay_id,
        count(*) as post12_vaso_records_n,
        min(starttime) as post12_vaso_first_starttime,
        max(endtime) as post12_vaso_last_endtime
    from vaso_window
    group by stay_id
),
event_pair_lac2 as (
    select
        l.stay_id,
        l.labevent_id,
        l.charttime as event_lactate_time,
        l.analysis_value as event_lactate_exact_value,
        l.lower_bound,
        l.result_class,
        l.definitely_ge4
    from lactate_window l
    join vaso_window v
      on l.stay_id = v.stay_id
     and v.starttime <= l.charttime + interval '6 hour'
     and v.endtime >= l.charttime - interval '6 hour'
    where l.definitely_ge2 = 1
    group by l.stay_id, l.labevent_id, l.charttime, l.analysis_value,
             l.lower_bound, l.result_class, l.definitely_ge4
),
event_summary as (
    select
        stay_id,
        min(event_lactate_time) as post12_overt_cs_main_event_time,
        max(event_lactate_exact_value) as post12_overt_cs_main_lactate_max,
        count(*) as post12_overt_cs_main_pair_n,
        min(event_lactate_time) filter (where definitely_ge4 = 1) as post12_overt_cs_lac4_event_time,
        count(*) filter (where definitely_ge4 = 1) as post12_overt_cs_lac4_pair_n
    from event_pair_lac2
    group by stay_id
)
select
    b.*,
    coalesce(l.post12_lactate_n, 0) as post12_lactate_n,
    coalesce(l.post12_lactate_exact_n, 0) as post12_lactate_exact_n,
    l.post12_lactate_max,
    l.post12_lactate_ge2_first_time,
    l.post12_lactate_ge4_first_time,
    coalesce(l.post12_lactate_ge2_n, 0) as post12_lactate_ge2_n,
    coalesce(l.post12_lactate_ge4_n, 0) as post12_lactate_ge4_n,
    coalesce(a.ambiguous_episode_match_n, 0) as lactate_ambiguous_episode_match_n,
    case when coalesce(a.ambiguous_episode_match_n, 0) > 0 then 1 else 0 end as ambiguous_episode_match,
    coalesce(v.post12_vaso_records_n, 0) as post12_vaso_records_n,
    v.post12_vaso_first_starttime,
    v.post12_vaso_last_endtime,
    case when coalesce(v.post12_vaso_records_n, 0) > 0 then 1 else 0 end as post12_vasoactive_flag,
    case when e.post12_overt_cs_main_event_time is not null then 1 else 0 end as post12_overt_cs_main_flag,
    e.post12_overt_cs_main_event_time,
    e.post12_overt_cs_main_lactate_max,
    coalesce(e.post12_overt_cs_main_pair_n, 0) as post12_overt_cs_main_pair_n,
    case when e.post12_overt_cs_lac4_event_time is not null then 1 else 0 end as post12_overt_cs_lac4_flag,
    e.post12_overt_cs_lac4_event_time,
    coalesce(e.post12_overt_cs_lac4_pair_n, 0) as post12_overt_cs_lac4_pair_n,
    case
        when e.post12_overt_cs_main_event_time < b.intime + interval '36 hour' then '12_36h'
        when e.post12_overt_cs_main_event_time >= b.intime + interval '36 hour' then '36_60h'
        else null
    end as post12_overt_cs_main_interval
from base_followup b
left join lactate_summary l on b.stay_id = l.stay_id
left join lactate_episode_audit a on b.stay_id = a.stay_id
left join vaso_summary v on b.stay_id = v.stay_id
left join event_summary e on b.stay_id = e.stay_id;

select
    count(*) as n_total,
    sum(ambiguous_episode_match) as ambiguous_episode_match_n,
    sum(post12_overt_cs_main_flag) as post12_overt_cs_main_n
from study_ahf_v3_3.outcome_061E_post12_overt_cs_future48h_main_v2;
