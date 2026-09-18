-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/02_outcome/061E_create_post12_overt_cs_future48h.sql
-- Purpose:
--   Define new-onset overt CS from 12h to 60h after ICU intime,
--   among the 12h landmark at-risk cohort.
--
-- Main outcome:
--   lactate >=2 mmol/L within 12-60h
--   AND vasoactive/inotrope support temporally paired within +/-6h.
--
-- Event time:
--   first lactate charttime satisfying the temporal-pair rule.
-- ============================================================

drop table if exists study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1 cascade;

create table study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1 as
with base as (
    select
        b.*,
        a.deathtime,
        b.intime + interval '12 hour' as landmark12_time,
        b.intime + interval '60 hour' as window60_time,

        least(
            b.outtime,
            b.intime + interval '60 hour'
        ) as observed_until_time,

        case
            when b.outtime >= b.intime + interval '60 hour' then 1
            else 0
        end as complete60_icu_flag

    from study_ahf_v3_1.cohort_061D_landmark12_riskset_main_v1 b
    left join mimiciv_hosp.admissions a
        on b.subject_id = a.subject_id
       and b.hadm_id = a.hadm_id
),

base_followup as (
    select
        *,
        extract(epoch from (observed_until_time - landmark12_time)) / 3600.0
            as followup_hours_12_60,

        case
            when deathtime >= landmark12_time
             and deathtime <  window60_time
            then 1 else 0
        end as death_12_60_flag

    from base
    where observed_until_time > landmark12_time
),

lactate_window as (
    select
        b.stay_id,
        bg.charttime,
        bg.lactate
    from base_followup b
    inner join mimiciv_derived.bg bg
        on b.subject_id = bg.subject_id
       and b.hadm_id = bg.hadm_id
    where bg.charttime >= b.landmark12_time
      and bg.charttime <  b.observed_until_time
      and bg.lactate is not null
),

lactate_summary as (
    select
        stay_id,
        count(*) as post12_lactate_n,
        max(lactate) as post12_lactate_max,
        min(charttime) filter (where lactate >= 2) as post12_lactate_ge2_first_time,
        min(charttime) filter (where lactate >= 4) as post12_lactate_ge4_first_time,
        count(*) filter (where lactate >= 2) as post12_lactate_ge2_n,
        count(*) filter (where lactate >= 4) as post12_lactate_ge4_n
    from lactate_window
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
    inner join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
    where va.starttime <  b.observed_until_time
      and coalesce(va.endtime, va.starttime + interval '1 minute') > b.landmark12_time
      and (
            coalesce(va.dopamine, 0) > 0
         or coalesce(va.epinephrine, 0) > 0
         or coalesce(va.norepinephrine, 0) > 0
         or coalesce(va.phenylephrine, 0) > 0
         or coalesce(va.vasopressin, 0) > 0
         or coalesce(va.dobutamine, 0) > 0
         or coalesce(va.milrinone, 0) > 0
      )
),

vaso_summary as (
    select
        stay_id,
        count(*) as post12_vaso_records_n,
        min(starttime) as post12_vaso_first_starttime,
        max(endtime) as post12_vaso_last_endtime,

        max(case when coalesce(norepinephrine, 0) > 0 then 1 else 0 end) as post12_norepinephrine_flag,
        max(case when coalesce(epinephrine, 0) > 0 then 1 else 0 end) as post12_epinephrine_flag,
        max(case when coalesce(dopamine, 0) > 0 then 1 else 0 end) as post12_dopamine_flag,
        max(case when coalesce(dobutamine, 0) > 0 then 1 else 0 end) as post12_dobutamine_flag,
        max(case when coalesce(milrinone, 0) > 0 then 1 else 0 end) as post12_milrinone_flag,
        max(case when coalesce(vasopressin, 0) > 0 then 1 else 0 end) as post12_vasopressin_flag,
        max(case when coalesce(phenylephrine, 0) > 0 then 1 else 0 end) as post12_phenylephrine_flag

    from vaso_window
    group by stay_id
),

event_pair_lac2 as (
    select
        l.stay_id,
        l.charttime as event_lactate_time,
        l.lactate,

        max(case when coalesce(v.norepinephrine, 0) > 0 then 1 else 0 end) as event_norepinephrine_flag,
        max(case when coalesce(v.epinephrine, 0) > 0 then 1 else 0 end) as event_epinephrine_flag,
        max(case when coalesce(v.dopamine, 0) > 0 then 1 else 0 end) as event_dopamine_flag,
        max(case when coalesce(v.dobutamine, 0) > 0 then 1 else 0 end) as event_dobutamine_flag,
        max(case when coalesce(v.milrinone, 0) > 0 then 1 else 0 end) as event_milrinone_flag,
        max(case when coalesce(v.vasopressin, 0) > 0 then 1 else 0 end) as event_vasopressin_flag,
        max(case when coalesce(v.phenylephrine, 0) > 0 then 1 else 0 end) as event_phenylephrine_flag

    from lactate_window l
    inner join vaso_window v
        on l.stay_id = v.stay_id
       and v.starttime <= l.charttime + interval '6 hour'
       and v.endtime   >= l.charttime - interval '6 hour'
    where l.lactate >= 2
    group by
        l.stay_id,
        l.charttime,
        l.lactate
),

event_summary_lac2 as (
    select
        stay_id,
        min(event_lactate_time) as post12_overt_cs_main_event_time,
        max(lactate) as post12_overt_cs_main_lactate_max,
        count(*) as post12_overt_cs_main_pair_n,

        max(event_norepinephrine_flag) as event_norepinephrine_flag,
        max(event_epinephrine_flag) as event_epinephrine_flag,
        max(event_dopamine_flag) as event_dopamine_flag,
        max(event_dobutamine_flag) as event_dobutamine_flag,
        max(event_milrinone_flag) as event_milrinone_flag,
        max(event_vasopressin_flag) as event_vasopressin_flag,
        max(event_phenylephrine_flag) as event_phenylephrine_flag

    from event_pair_lac2
    group by stay_id
),

event_summary_lac4 as (
    select
        stay_id,
        min(event_lactate_time) as post12_overt_cs_lac4_event_time,
        max(lactate) as post12_overt_cs_lac4_lactate_max,
        count(*) as post12_overt_cs_lac4_pair_n
    from event_pair_lac2
    where lactate >= 4
    group by stay_id
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
    b.landmark12_time,
    b.window60_time,
    b.observed_until_time,
    b.followup_hours_12_60,
    b.complete60_icu_flag,
    b.deathtime,
    b.death_12_60_flag,

    coalesce(l.post12_lactate_n, 0) as post12_lactate_n,
    l.post12_lactate_max,
    l.post12_lactate_ge2_first_time,
    l.post12_lactate_ge4_first_time,
    coalesce(l.post12_lactate_ge2_n, 0) as post12_lactate_ge2_n,
    coalesce(l.post12_lactate_ge4_n, 0) as post12_lactate_ge4_n,

    coalesce(v.post12_vaso_records_n, 0) as post12_vaso_records_n,
    v.post12_vaso_first_starttime,
    v.post12_vaso_last_endtime,

    case
        when coalesce(v.post12_vaso_records_n, 0) > 0 then 1
        else 0
    end as post12_vasoactive_flag,

    coalesce(v.post12_norepinephrine_flag, 0) as post12_norepinephrine_flag,
    coalesce(v.post12_epinephrine_flag, 0) as post12_epinephrine_flag,
    coalesce(v.post12_dopamine_flag, 0) as post12_dopamine_flag,
    coalesce(v.post12_dobutamine_flag, 0) as post12_dobutamine_flag,
    coalesce(v.post12_milrinone_flag, 0) as post12_milrinone_flag,
    coalesce(v.post12_vasopressin_flag, 0) as post12_vasopressin_flag,
    coalesce(v.post12_phenylephrine_flag, 0) as post12_phenylephrine_flag,

    case
        when coalesce(l.post12_lactate_ge2_n, 0) > 0 then 1
        else 0
    end as post12_lactate_ge2_flag,

    case
        when coalesce(l.post12_lactate_ge4_n, 0) > 0 then 1
        else 0
    end as post12_lactate_ge4_flag,

    case
        when e2.stay_id is not null then 1
        else 0
    end as post12_overt_cs_main_flag,

    e2.post12_overt_cs_main_event_time,
    e2.post12_overt_cs_main_lactate_max,
    coalesce(e2.post12_overt_cs_main_pair_n, 0) as post12_overt_cs_main_pair_n,

    case
        when e4.stay_id is not null then 1
        else 0
    end as post12_overt_cs_lac4_flag,

    e4.post12_overt_cs_lac4_event_time,
    e4.post12_overt_cs_lac4_lactate_max,
    coalesce(e4.post12_overt_cs_lac4_pair_n, 0) as post12_overt_cs_lac4_pair_n,

    case
        when e2.post12_overt_cs_main_event_time is not null
         and e2.post12_overt_cs_main_event_time < b.intime + interval '36 hour'
            then '12_36h'
        when e2.post12_overt_cs_main_event_time is not null
         and e2.post12_overt_cs_main_event_time >= b.intime + interval '36 hour'
            then '36_60h'
        else null
    end as post12_overt_cs_main_interval,

    coalesce(e2.event_norepinephrine_flag, 0) as event_norepinephrine_flag,
    coalesce(e2.event_epinephrine_flag, 0) as event_epinephrine_flag,
    coalesce(e2.event_dopamine_flag, 0) as event_dopamine_flag,
    coalesce(e2.event_dobutamine_flag, 0) as event_dobutamine_flag,
    coalesce(e2.event_milrinone_flag, 0) as event_milrinone_flag,
    coalesce(e2.event_vasopressin_flag, 0) as event_vasopressin_flag,
    coalesce(e2.event_phenylephrine_flag, 0) as event_phenylephrine_flag

from base_followup b
left join lactate_summary l
    on b.stay_id = l.stay_id
left join vaso_summary v
    on b.stay_id = v.stay_id
left join event_summary_lac2 e2
    on b.stay_id = e2.stay_id
left join event_summary_lac4 e4
    on b.stay_id = e4.stay_id;
		
		
		
		
-- 		061E 质控查询
-- QC1：事件率
select
    count(*) as n_total,

    sum(complete60_icu_flag) as n_complete60_icu,
    round(sum(complete60_icu_flag) * 100.0 / count(*), 2) as pct_complete60_icu,

    sum(case when followup_hours_12_60 < 48 then 1 else 0 end) as n_censored_before60_icu,
    round(sum(case when followup_hours_12_60 < 48 then 1 else 0 end) * 100.0 / count(*), 2) as pct_censored_before60_icu,

    sum(death_12_60_flag) as n_death_12_60,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as pct_death_12_60,

    sum(post12_lactate_ge2_flag) as n_lactate_ge2,
    round(sum(post12_lactate_ge2_flag) * 100.0 / count(*), 2) as pct_lactate_ge2,

    sum(post12_vasoactive_flag) as n_vasoactive,
    round(sum(post12_vasoactive_flag) * 100.0 / count(*), 2) as pct_vasoactive,

    sum(post12_overt_cs_main_flag) as n_post12_overt_cs_main,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate_main,

    sum(post12_overt_cs_lac4_flag) as n_post12_overt_cs_lac4,
    round(sum(post12_overt_cs_lac4_flag) * 100.0 / count(*), 2) as event_rate_lac4

from study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1;




-- QC2：事件分段
select
    post12_overt_cs_main_interval,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct
from study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1
where post12_overt_cs_main_flag = 1
group by post12_overt_cs_main_interval
order by post12_overt_cs_main_interval;




-- QC3：事件用药组成
select
    sum(event_norepinephrine_flag) as n_event_norepinephrine,
    sum(event_epinephrine_flag) as n_event_epinephrine,
    sum(event_dopamine_flag) as n_event_dopamine,
    sum(event_dobutamine_flag) as n_event_dobutamine,
    sum(event_milrinone_flag) as n_event_milrinone,
    sum(event_vasopressin_flag) as n_event_vasopressin,
    sum(event_phenylephrine_flag) as n_event_phenylephrine
from study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1
where post12_overt_cs_main_flag = 1;




-- QC4：complete60 事件率
select
    complete60_icu_flag,
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1
group by complete60_icu_flag
order by complete60_icu_flag;




-- QC5：sepsis3 交叉
select
    o.post12_overt_cs_main_flag,
    case
        when s.stay_id is not null then 1 else 0
    end as sepsis3_any_flag,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct
from study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1 o
left join mimiciv_derived.sepsis3 s
    on o.stay_id = s.stay_id
group by
    o.post12_overt_cs_main_flag,
    case
        when s.stay_id is not null then 1 else 0
    end
order by
    o.post12_overt_cs_main_flag,
    sepsis3_any_flag;
		
		
		
		delete from study_ahf_v3_1.cohort_flow
where step_id in (61, 62, 63, 64, 65);

insert into study_ahf_v3_1.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    61,
    'ahf_evidence_12h',
    'study_ahf_v3_1.cohort_061A_ahf_evidence_early_window_12h_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    0,
    'AHF evidence table for 12h landmark. Evidence window: ICU intime -24h to +12h.'
from study_ahf_v3_1.cohort_061A_ahf_evidence_early_window_12h_v1;

insert into study_ahf_v3_1.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    62,
    'ahf_strict_12h',
    'study_ahf_v3_1.cohort_061B_ahf_strict_12h_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    (
        select count(*)
        from study_ahf_v3_1.cohort_061A_ahf_evidence_early_window_12h_v1
    ) - count(*),
    'Strict AHF cohort for 12h landmark: HF ICD seq <=5 plus early AHF evidence by 12h.'
from study_ahf_v3_1.cohort_061B_ahf_strict_12h_v1;

insert into study_ahf_v3_1.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    63,
    'pre12_overt_cs_flags',
    'study_ahf_v3_1.outcome_061C_pre12_overt_cs_flags_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    0,
    'Pre-12h overt CS proxy flags created in strict AHF 12h cohort. No exclusion applied in this table.'
from study_ahf_v3_1.outcome_061C_pre12_overt_cs_flags_v1;

insert into study_ahf_v3_1.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    64,
    'landmark12_riskset_main',
    'study_ahf_v3_1.cohort_061D_landmark12_riskset_main_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    (
        select count(*)
        from study_ahf_v3_1.cohort_061B_ahf_strict_12h_v1
    ) - count(*),
    'Reached 12h landmark and excluded pre12 overt CS by main proxy.'
from study_ahf_v3_1.cohort_061D_landmark12_riskset_main_v1;

insert into study_ahf_v3_1.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    65,
    'post12_future48_overt_cs_outcome',
    'study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    0,
    'Outcome table for candidate main analysis: 12h landmark, future 48h window, new overt CS proxy.'
from study_ahf_v3_1.outcome_061E_post12_overt_cs_future48h_main_v1;




