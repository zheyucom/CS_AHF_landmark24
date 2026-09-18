-- ============================================================
-- Project: CS_AHF_landmark12_earlysepsis
-- File: sql/02_outcome/062B_create_ahf_earlysepsis12_main_outcome.sql
-- Purpose:
--   Create the candidate main analysis cohort:
--   AHF + early sepsis by 12h, 12h landmark risk set,
--   12-60h new overt CS outcome.
-- ============================================================

drop table if exists study_ahf_v3.outcome_062B_ahf_earlysepsis12_post12_future48_main_v1 cascade;

create table study_ahf_v3.outcome_062B_ahf_earlysepsis12_post12_future48_main_v1 as
select
    *,
    'ahf_earlysepsis12_landmark12_future48h'::text as main_analysis_definition
from study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_main_flag = 1;


drop table if exists study_ahf_v3.outcome_062B_ahf_noearlysepsis12_post12_future48_sensitivity_v1 cascade;

create table study_ahf_v3.outcome_062B_ahf_noearlysepsis12_post12_future48_sensitivity_v1 as
select
    *,
    'ahf_no_earlysepsis12_landmark12_future48h'::text as sensitivity_definition
from study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_main_flag = 0;





select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,

    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate,

    sum(post12_overt_cs_lac4_flag) as n_lac4_events,
    round(sum(post12_overt_cs_lac4_flag) * 100.0 / count(*), 2) as lac4_event_rate,

    sum(complete60_icu_flag) as n_complete60,
    round(sum(complete60_icu_flag) * 100.0 / count(*), 2) as pct_complete60,

    sum(case when followup_hours_12_60 < 48 then 1 else 0 end) as n_censored_before60,
    round(sum(case when followup_hours_12_60 < 48 then 1 else 0 end) * 100.0 / count(*), 2) as pct_censored_before60,

    sum(death_12_60_flag) as n_death_12_60,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as pct_death_12_60

from study_ahf_v3.outcome_062B_ahf_earlysepsis12_post12_future48_main_v1;





select
    post12_overt_cs_main_interval,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct
from study_ahf_v3.outcome_062B_ahf_earlysepsis12_post12_future48_main_v1
where post12_overt_cs_main_flag = 1
group by post12_overt_cs_main_interval
order by post12_overt_cs_main_interval;




select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,

    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate,

    sum(post12_overt_cs_lac4_flag) as n_lac4_events,
    round(sum(post12_overt_cs_lac4_flag) * 100.0 / count(*), 2) as lac4_event_rate,

    sum(complete60_icu_flag) as n_complete60,
    round(sum(complete60_icu_flag) * 100.0 / count(*), 2) as pct_complete60,

    sum(death_12_60_flag) as n_death_12_60,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as pct_death_12_60

from study_ahf_v3.outcome_062B_ahf_noearlysepsis12_post12_future48_sensitivity_v1;




delete from study_ahf_v3.cohort_flow
where step_id in (66, 67);

insert into study_ahf_v3.cohort_flow (
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
    66,
    'post12_outcome_with_earlysepsis12_flags',
    'study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    0,
    'Added early sepsis flags to 12h AHF risk set outcome table. Early sepsis main definition uses sepsis3 evidence available by 12h landmark.'
from study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1;


insert into study_ahf_v3.cohort_flow (
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
    67,
    'ahf_earlysepsis12_main_analysis',
    'study_ahf_v3.outcome_062B_ahf_earlysepsis12_post12_future48_main_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    (
        select count(*)
        from study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1
    ) - count(*),
    'Candidate main analysis cohort: AHF plus early sepsis by 12h, no pre12 overt CS, prediction window 12-60h.'
from study_ahf_v3.outcome_062B_ahf_earlysepsis12_post12_future48_main_v1;