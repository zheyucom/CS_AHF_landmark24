-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v3/audits/091_audit_t0_ahf_earlysepsis_feasibility.sql
-- Purpose:
--   Audit whether the clinical target "AHF plus early sepsis already
--   present at ICU admission" is identifiable from timestamped MIMIC data.
--
-- Scope:
--   This audit does not change the v3 cohort or train a model.
--   The analysis base is the existing 12 h at-risk cohort. Final ICD codes
--   are used only as retrospective phenotype anchors, never as predictors.
--
-- Definitions:
--   T0        = ICU intime.
--   pre-T0    = [T0 - 24 h, T0).
--   T0-6 h    = [T0, T0 + 6 h).
--   T0-12 h   = [T0, T0 + 12 h).
-- ============================================================

drop table if exists study_ahf_v4.audit_091_t0_evidence_by_stay_v1 cascade;

create table study_ahf_v4.audit_091_t0_evidence_by_stay_v1 as
with base as (
    select
        o.subject_id,
        o.hadm_id,
        o.stay_id,
        o.intime,
        o.hd_deterioration_broad_nee005_flag as primary_outcome_flag,

        a.hf_icd_any as ahf_retro_confirmed_flag,
        a.hf_icd_acute_or_acute_on_chronic as acute_hf_icd_retro_flag,
        a.iv_loop_rx_first_starttime_early12,
        a.loop_emar_first_charttime_early12,
        a.ntprobnp_first_charttime_early12,
        a.ntprobnp_max_early12
    from study_ahf_v4.outcome_063c_candidate_hd_outcomes_with_nee_v1 o
    inner join study_ahf_v4.cohort_061a_ahf_evidence_early_window_12h_v1 a
        on o.subject_id = a.subject_id
       and o.hadm_id = a.hadm_id
       and o.stay_id = a.stay_id
),
timed_evidence as (
    select
        b.*,
        s.antibiotic_time,
        s.culture_time,
        s.suspected_infection_time,
        s.sofa_time,
        s.sofa_score,
        case when s.sepsis3 is true then 1 else 0 end as sepsis3_flag,

        case when (
            (b.loop_emar_first_charttime_early12 >= b.intime - interval '24 hour'
             and b.loop_emar_first_charttime_early12 < b.intime)
            or
            (b.iv_loop_rx_first_starttime_early12 >= b.intime - interval '24 hour'
             and b.iv_loop_rx_first_starttime_early12 < b.intime)
            or
            (b.ntprobnp_first_charttime_early12 >= b.intime - interval '24 hour'
             and b.ntprobnp_first_charttime_early12 < b.intime)
        ) then 1 else 0 end as ahf_time_evidence_pre_t0_flag,

        case when (
            (b.loop_emar_first_charttime_early12 >= b.intime - interval '24 hour'
             and b.loop_emar_first_charttime_early12 < b.intime + interval '12 hour')
            or
            (b.iv_loop_rx_first_starttime_early12 >= b.intime - interval '24 hour'
             and b.iv_loop_rx_first_starttime_early12 < b.intime + interval '12 hour')
            or
            (b.ntprobnp_first_charttime_early12 >= b.intime - interval '24 hour'
             and b.ntprobnp_first_charttime_early12 < b.intime + interval '12 hour')
        ) then 1 else 0 end as ahf_time_evidence_by_t12_flag,

        case when s.sepsis3 is true
              and s.antibiotic_time >= b.intime - interval '24 hour'
              and s.antibiotic_time < b.intime
              and s.culture_time >= b.intime - interval '24 hour'
              and s.culture_time < b.intime
              and s.suspected_infection_time >= b.intime - interval '24 hour'
              and s.suspected_infection_time < b.intime
             then 1 else 0 end as infection_source_pre_t0_flag,

        case when s.sepsis3 is true
              and s.sofa_time >= b.intime - interval '24 hour'
              and s.sofa_time < b.intime
             then 1 else 0 end as sofa_pre_t0_flag,

        case when s.sepsis3 is true
              and s.sofa_time >= b.intime
              and s.sofa_time < b.intime + interval '6 hour'
             then 1 else 0 end as sofa_t0_6h_flag,

        case when s.sepsis3 is true
              and s.sofa_time >= b.intime
              and s.sofa_time < b.intime + interval '12 hour'
             then 1 else 0 end as sofa_t0_12h_flag,

        case when s.sepsis3 is true
              and s.antibiotic_time >= b.intime - interval '24 hour'
              and s.antibiotic_time < b.intime + interval '12 hour'
              and s.culture_time >= b.intime - interval '24 hour'
              and s.culture_time < b.intime + interval '12 hour'
              and s.suspected_infection_time >= b.intime - interval '24 hour'
              and s.suspected_infection_time < b.intime + interval '12 hour'
              and s.sofa_time >= b.intime - interval '24 hour'
              and s.sofa_time < b.intime + interval '12 hour'
             then 1 else 0 end as sepsis_fully_confirmed_by_t12_flag
    from base b
    left join mimiciv_derived.sepsis3 s
        on b.stay_id = s.stay_id
)
select
    *,
    case when ahf_retro_confirmed_flag = 1
              and ahf_time_evidence_pre_t0_flag = 1
              and infection_source_pre_t0_flag = 1
              and sofa_pre_t0_flag = 1
         then 1 else 0 end as strict_t0_ahf_sepsis_flag,

    case when ahf_retro_confirmed_flag = 1
              and ahf_time_evidence_pre_t0_flag = 1
              and infection_source_pre_t0_flag = 1
              and sofa_t0_6h_flag = 1
         then 1 else 0 end as t0_present_sepsis_confirmed_6h_flag,

    case when ahf_retro_confirmed_flag = 1
              and ahf_time_evidence_pre_t0_flag = 1
              and infection_source_pre_t0_flag = 1
              and sofa_t0_12h_flag = 1
         then 1 else 0 end as t0_present_sepsis_confirmed_12h_flag,

    case when ahf_retro_confirmed_flag = 1
              and ahf_time_evidence_pre_t0_flag = 1
              and sepsis_fully_confirmed_by_t12_flag = 1
         then 1 else 0 end as ahf_t0_sepsis_confirmed_by_t12_flag
from timed_evidence;

drop table if exists study_ahf_v4.audit_091_t0_cohort_feasibility_v1 cascade;

create table study_ahf_v4.audit_091_t0_cohort_feasibility_v1 as
select
    cohort_rule,
    count(*)::bigint as n_stays,
    sum(primary_outcome_flag)::bigint as n_primary_events,
    round(avg(primary_outcome_flag::numeric) * 100, 2) as primary_event_rate_pct
from (
    select '00_existing_v3_12h_riskset'::text as cohort_rule, primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1

    union all
    select '01_AHF_time_evidence_pre_T0', primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1
    where ahf_time_evidence_pre_t0_flag = 1

    union all
    select '02_AHF_preT0_plus_infection_sources_preT0', primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1
    where ahf_time_evidence_pre_t0_flag = 1
      and infection_source_pre_t0_flag = 1

    union all
    select '03_strict_T0_AHF_plus_Sepsis3', primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1
    where strict_t0_ahf_sepsis_flag = 1

    union all
    select '04_T0_present_sepsis_confirmed_by_6h', primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1
    where t0_present_sepsis_confirmed_6h_flag = 1

    union all
    select '05_T0_present_sepsis_confirmed_by_12h', primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1
    where t0_present_sepsis_confirmed_12h_flag = 1

    union all
    select '06_AHF_preT0_plus_Sepsis3_fully_confirmed_by_T12', primary_outcome_flag
    from study_ahf_v4.audit_091_t0_evidence_by_stay_v1
    where ahf_t0_sepsis_confirmed_by_t12_flag = 1
) x
group by cohort_rule
order by cohort_rule;

-- QC1: formal cohort-feasibility summary.
select *
from study_ahf_v4.audit_091_t0_cohort_feasibility_v1
order by cohort_rule;

-- QC2: source timing among the existing 12 h risk set.
select
    count(*) as n_riskset,
    sum(ahf_time_evidence_pre_t0_flag) as n_ahf_pre_t0,
    sum(infection_source_pre_t0_flag) as n_infection_source_pre_t0,
    sum(sofa_pre_t0_flag) as n_sofa_pre_t0,
    sum(sofa_t0_6h_flag) as n_sofa_t0_6h,
    sum(sofa_t0_12h_flag) as n_sofa_t0_12h,
    sum(sepsis_fully_confirmed_by_t12_flag) as n_sepsis_fully_confirmed_by_t12,
    sum(strict_t0_ahf_sepsis_flag) as n_strict_t0_ahf_sepsis,
    sum(t0_present_sepsis_confirmed_6h_flag) as n_t0_present_confirmed_6h,
    sum(t0_present_sepsis_confirmed_12h_flag) as n_t0_present_confirmed_12h
from study_ahf_v4.audit_091_t0_evidence_by_stay_v1;
