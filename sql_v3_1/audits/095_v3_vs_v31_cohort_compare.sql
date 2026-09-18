-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v3_1/audits/095_v3_vs_v31_cohort_compare.sql
-- Purpose:
--   Compare v3 (loose time availability) vs v3.1 (AHF time-confirmed
--   by T12 + early sepsis antibiotic/culture < T12) cohort sizes,
--   event counts and event rates side by side.
-- ============================================================

select
    'v3'::text as version,
    'existing_v3_main'::text as step,
    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(avg(primary_outcome_flag::numeric) * 100.0, 2) as event_rate_pct
from study_ahf_v3.outcome_064_primary_hd_deterioration_v1

union all

select
    'v3_1'::text,
    'main_time_confirmed',
    count(*),
    sum(primary_outcome_flag),
    round(avg(primary_outcome_flag::numeric) * 100.0, 2)
from study_ahf_v3_1.outcome_064_primary_hd_deterioration_v1
order by version, step;

-- ============================================================
-- v3.1 cohort flow (mirror of the QC output in 064 log)
-- ============================================================
select
    step,
    n_rows
from (
    select 10 as ord, 'adult_first_icu' as step, count(*)::bigint as n_rows
    from study_ahf_v3_1.cohort_010_adult_first_icu_v1
    union all
    select 20, 'hf_icd_candidate', count(*)
    from study_ahf_v3_1.cohort_020_hf_icd_candidate_v1
    union all
    select 61, 'strict_ahf_12h_time_confirmed', count(*)
    from study_ahf_v3_1.cohort_061B_ahf_strict_12h_v1
    union all
    select 64, 'landmark12_riskset', count(*)
    from study_ahf_v3_1.cohort_061D_landmark12_riskset_main_v1
    union all
    select 67, 'main_cohort_early_sepsis12', count(*)
    from study_ahf_v3_1.outcome_062b_ahf_earlysepsis12_post12_future48_main_v1
    union all
    select 68, 'primary_outcome_table', count(*)
    from study_ahf_v3_1.outcome_064_primary_hd_deterioration_v1
) x
order by ord;

-- ============================================================
-- Impact of the antibiotic/culture < T12 fix within v3.1 riskset:
-- how many stays lost the main sepsis flag purely due to timing
-- ============================================================
select
    case when abt.early_sepsis12_main_flag = 1 then 'main_flag_1' else 'main_flag_0' end as main_flag,
    case when loose.early_sepsis12_main_flag_loose = 1 then 'loose_flag_1' else 'loose_flag_0' end as loose_flag,
    count(*) as n
from study_ahf_v3_1.outcome_062A_post12_outcome_with_earlysepsis12_v1 abt
left join (
    select stay_id, max(case when sepsis3_flag = 1 and suspected_infection_by12_flag = 1 and sofa_by12_flag = 1 then 1 else 0 end) as early_sepsis12_main_flag_loose
    from (
        select
            b.stay_id,
            case when lower(coalesce(s.sepsis3::text, '')) in ('true', 't', '1', 'yes') then 1 else 0 end as sepsis3_flag,
            case when s.suspected_infection_time >= b.intime - interval '24 hour'
                  and s.suspected_infection_time < b.intime + interval '12 hour' then 1 else 0 end as suspected_infection_by12_flag,
            case when s.sofa_time >= b.intime - interval '24 hour'
                  and s.sofa_time < b.intime + interval '12 hour' then 1 else 0 end as sofa_by12_flag
        from study_ahf_v3_1.cohort_061D_landmark12_riskset_main_v1 b
        left join mimiciv_derived.sepsis3 s on b.stay_id = s.stay_id
    ) x
    group by stay_id
) loose on abt.stay_id = loose.stay_id
group by 1, 2
order by 1, 2;
