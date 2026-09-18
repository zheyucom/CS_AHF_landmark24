-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/02_outcome/064_create_primary_analysis_outcome.sql
-- Purpose:
--   Create final primary analysis outcome table.
--
-- Main population:
--   AHF strict 12h
--   + early sepsis by 12h
--   + reached 12h landmark
--   + no pre12 overt CS
--
-- Primary outcome:
--   12-60h hemodynamic deterioration:
--     new vasoactive/inotrope support
--     OR increased number of vasoactive/inotrope agents
--     OR NEE max increase >=0.05 mcg/kg/min from pre12 max
--     OR death within 12-60h.
-- ============================================================

drop table if exists study_ahf_v3.outcome_064_primary_hd_deterioration_v1 cascade;

create table study_ahf_v3.outcome_064_primary_hd_deterioration_v1 as
select
    *,
    'ahf_earlysepsis12_landmark12_future48h'::text as analysis_population,
    'hd_deterioration_broad_nee005'::text as primary_outcome_definition,

    hd_deterioration_broad_nee005_flag as primary_outcome_flag,

    -- Key secondary outcomes
    hd_deterioration_broad_nee010_flag as secondary_hd_deterioration_nee010_flag,
    hd_deterioration_broad_flag as secondary_hd_deterioration_no_nee_flag,
    current_mixed_shock_proxy_flag as secondary_mixed_shock_proxy_flag,
    current_mixed_shock_lac4_proxy_flag as secondary_mixed_shock_lac4_proxy_flag,
    hd_deterioration_lac_confirmed_nee005_flag as secondary_hd_lactate_confirmed_flag,
    mixed_shock_proxy_or_death_flag as secondary_mixed_shock_or_death_flag

from study_ahf_v3.outcome_063C_candidate_hd_outcomes_with_nee_v1
where early_sepsis12_main_flag = 1;




select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,

    sum(primary_outcome_flag) as n_primary_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as primary_event_rate,

    sum(secondary_hd_deterioration_nee010_flag) as n_hd_nee010,
    round(sum(secondary_hd_deterioration_nee010_flag) * 100.0 / count(*), 2) as rate_hd_nee010,

    sum(secondary_hd_deterioration_no_nee_flag) as n_hd_no_nee,
    round(sum(secondary_hd_deterioration_no_nee_flag) * 100.0 / count(*), 2) as rate_hd_no_nee,

    sum(secondary_mixed_shock_proxy_flag) as n_mixed_shock_proxy,
    round(sum(secondary_mixed_shock_proxy_flag) * 100.0 / count(*), 2) as rate_mixed_shock_proxy,

    sum(secondary_hd_lactate_confirmed_flag) as n_hd_lactate_confirmed,
    round(sum(secondary_hd_lactate_confirmed_flag) * 100.0 / count(*), 2) as rate_hd_lactate_confirmed,

    sum(death_12_60_flag) as n_death_12_60,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as death_12_60_rate

from study_ahf_v3.outcome_064_primary_hd_deterioration_v1;






select
    hd_support_initiation_or_count_increase_flag,
    nee_escalation_conservative_flag,
    death_12_60_flag,
    primary_outcome_flag,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct
from study_ahf_v3.outcome_064_primary_hd_deterioration_v1
group by
    hd_support_initiation_or_count_increase_flag,
    nee_escalation_conservative_flag,
    death_12_60_flag,
    primary_outcome_flag
order by n desc;






select
    complete60_icu_flag,
    count(*) as n,

    sum(primary_outcome_flag) as n_primary_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as primary_event_rate,

    sum(hd_support_initiation_or_count_increase_flag) as n_support_escalation,
    round(sum(hd_support_initiation_or_count_increase_flag) * 100.0 / count(*), 2) as rate_support_escalation,

    sum(nee_escalation_conservative_flag) as n_nee_escalation,
    round(sum(nee_escalation_conservative_flag) * 100.0 / count(*), 2) as rate_nee_escalation,

    sum(death_12_60_flag) as n_death,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as rate_death

from study_ahf_v3.outcome_064_primary_hd_deterioration_v1
group by complete60_icu_flag
order by complete60_icu_flag;





delete from study_ahf_v3.cohort_flow
where step_id = 68;

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
    68,
    'primary_hd_deterioration_outcome',
    'study_ahf_v3.outcome_064_primary_hd_deterioration_v1',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    (
        select count(*)
        from study_ahf_v3.outcome_063C_candidate_hd_outcomes_with_nee_v1
    ) - count(*),
    'Primary analysis cohort and outcome: AHF plus early sepsis by 12h, landmark 12h, future 48h hemodynamic deterioration. Primary outcome includes support initiation, increased agent count, NEE increase >=0.05, or death.'
from study_ahf_v3.outcome_064_primary_hd_deterioration_v1;






