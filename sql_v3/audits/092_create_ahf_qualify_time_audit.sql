-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v3/audits/092_create_ahf_qualify_time_audit.sql
-- Purpose:
--   Audit AHF qualification time (T_qualify) relative to ICU T0.
--
--   Rationale (study discussion 2026-08-26):
--   The main cohort keeps "AHF time-confirmed by T12" with evidence
--   window [T0-24h, T12). For stays whose AHF evidence first appears
--   AFTER T0, part of the 0-12h feature window was observed in an
--   unconfirmed-AHF state. This is not future leakage (all features
--   < T12), but it creates within-cohort asymmetry: the proportion of
--   the feature window spent in an unconfirmed state differs by
--   patient. This audit quantifies that asymmetry and provides the
--   strata for planned sensitivity analyses.
--
--   T0 = ICU intime. Evidence window for cohort = [T0-24h, T12).
--
--   This is an audit only. It does not modify the modeling cohort.
--   Final ICD codes remain retrospective phenotype anchors only.
-- ============================================================

drop table if exists study_ahf_v3.audit_092_ahf_qualify_time_v1 cascade;

create table study_ahf_v3.audit_092_ahf_qualify_time_v1 as
with riskset as (
    select
        r.stay_id,
        r.subject_id,
        r.hadm_id,
        r.intime,
        ad.admittime,
        o.hd_deterioration_broad_nee005_flag as primary_outcome_flag,
        o.complete60_icu_flag,
        o.death_12_60_flag,
        o.early_sepsis12_main_flag,
        a.hf_icd_acute_or_acute_on_chronic as acute_hf_icd_retro_flag,
        a.hf_icd_seq_le5,
        a.ntprobnp_first_charttime_early12,
        a.loop_emar_first_charttime_early12,
        a.iv_loop_rx_first_starttime_early12
    from study_ahf_v3.cohort_061D_landmark12_riskset_main_v1 r
    inner join study_ahf_v3.cohort_061A_ahf_evidence_early_window_12h_v1 a
        on r.stay_id = a.stay_id
    inner join study_ahf_v3.outcome_063C_candidate_hd_outcomes_with_nee_v1 o
        on r.stay_id = o.stay_id
    inner join mimiciv_hosp.admissions ad
        on r.hadm_id = ad.hadm_id
),
timed as (
    select
        *,
        -- Executed/lab evidence only (eMAR administration or NT-proBNP
        -- measurement). Pharmacy order start time excluded here.
        least(
            loop_emar_first_charttime_early12,
            ntprobnp_first_charttime_early12
        ) as qualify_time_exe,

        -- Including pharmacy IV loop order start time (order may precede
        -- administration; used only as a sensitivity definition).
        least(
            loop_emar_first_charttime_early12,
            ntprobnp_first_charttime_early12,
            iv_loop_rx_first_starttime_early12
        ) as qualify_time_all
    from riskset
)
select
    t.*,
    extract(epoch from (t.intime - t.admittime)) / 3600.0 as adm_to_t0_hours,

    case
        when t.qualify_time_exe is null then 'icd_only'
        when t.qualify_time_exe < t.intime then 'pre_t0'
        when t.qualify_time_exe < t.intime + interval '6 hour' then 't0_6h'
        else '6_12h'
    end as qualify_stratum_exe,

    case
        when t.qualify_time_all is null then 'icd_only'
        when t.qualify_time_all < t.intime then 'pre_t0'
        when t.qualify_time_all < t.intime + interval '6 hour' then 't0_6h'
        else '6_12h'
    end as qualify_stratum_all,

    case
        when t.qualify_time_exe is null then null::numeric
        else extract(epoch from (t.qualify_time_exe - t.intime)) / 3600.0
    end as qualify_offset_h_exe,

    case
        when t.qualify_time_all is null then null::numeric
        else extract(epoch from (t.qualify_time_all - t.intime)) / 3600.0
    end as qualify_offset_h_all,

    -- Fraction of the 12h feature window observed in an unconfirmed-AHF
    -- state. 0 = AHF already confirmed before/at T0; 1 = ICD-only (no
    -- timestamped evidence at all, cohort support entirely retrospective).
    case
        when t.qualify_time_exe is null then 1.0
        when t.qualify_time_exe <= t.intime then 0.0
        when t.qualify_time_exe >= t.intime + interval '12 hour' then 1.0
        else extract(epoch from (t.qualify_time_exe - t.intime)) / 43200.0
    end as unconfirmed_frac_exe
from timed t;

create index if not exists idx_092_qualify_stay
    on study_ahf_v3.audit_092_ahf_qualify_time_v1 (stay_id);

analyze study_ahf_v3.audit_092_ahf_qualify_time_v1;

-- ============================================================
-- Summary table: stratum x cohort
-- ============================================================
drop table if exists study_ahf_v3.audit_092_ahf_qualify_summary_v1 cascade;

create table study_ahf_v3.audit_092_ahf_qualify_summary_v1 as
with u as (
    select
        'riskset'::text as cohort,
        qualify_stratum_exe as stratum,
        primary_outcome_flag,
        complete60_icu_flag,
        death_12_60_flag
    from study_ahf_v3.audit_092_ahf_qualify_time_v1

    union all

    select
        'main_cohort',
        qualify_stratum_exe,
        primary_outcome_flag,
        complete60_icu_flag,
        death_12_60_flag
    from study_ahf_v3.audit_092_ahf_qualify_time_v1
    where early_sepsis12_main_flag = 1
)
select
    cohort,
    stratum,
    count(*) as n_stays,
    sum(primary_outcome_flag) as n_events,
    round(avg(primary_outcome_flag::numeric) * 100.0, 2) as event_rate_pct,
    sum(complete60_icu_flag) as n_complete60,
    sum(death_12_60_flag) as n_death_12_60
from u
group by cohort, stratum
order by cohort, stratum;

-- ============================================================
-- QC1: stratum x cohort summary (executed-evidence definition)
-- ============================================================
select *
from study_ahf_v3.audit_092_ahf_qualify_summary_v1
order by cohort, stratum;

-- ============================================================
-- QC2: offset buckets within the feature window (main cohort)
-- ============================================================
select
    bucket,
    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(avg(primary_outcome_flag::numeric) * 100.0, 2) as event_rate_pct
from (
    select
        case
            when qualify_time_exe is null then 'icd_only'
            when qualify_time_exe < intime then 'pre_t0'
            when qualify_time_exe < intime + interval '2 hour' then 't0_2h'
            when qualify_time_exe < intime + interval '4 hour' then '2_4h'
            when qualify_time_exe < intime + interval '6 hour' then '4_6h'
            when qualify_time_exe < intime + interval '8 hour' then '6_8h'
            when qualify_time_exe < intime + interval '10 hour' then '8_10h'
            else '10_12h'
        end as bucket,
        primary_outcome_flag
    from study_ahf_v3.audit_092_ahf_qualify_time_v1
    where early_sepsis12_main_flag = 1
) x
group by bucket
order by bucket;

-- ============================================================
-- QC3: offset distribution (hours, negative = before ICU) by cohort
-- ============================================================
select
    cohort,
    count(*) as n_with_exe_evidence,
    round(min(qualify_offset_h_exe)::numeric, 2) as min_h,
    round(percentile_cont(0.25) within group (order by qualify_offset_h_exe)::numeric, 2) as p25_h,
    round(percentile_cont(0.50) within group (order by qualify_offset_h_exe)::numeric, 2) as median_h,
    round(percentile_cont(0.75) within group (order by qualify_offset_h_exe)::numeric, 2) as p75_h,
    round(max(qualify_offset_h_exe)::numeric, 2) as max_h,
    round(avg(unconfirmed_frac_exe)::numeric, 4) as avg_unconfirmed_frac
from (
    select
        case when early_sepsis12_main_flag = 1 then 'main_cohort' else 'riskset' end as cohort,
        qualify_offset_h_exe,
        unconfirmed_frac_exe
    from study_ahf_v3.audit_092_ahf_qualify_time_v1
    where qualify_time_exe is not null
) y
group by cohort
order by cohort;

-- ============================================================
-- QC4: ICU-before evidence window length (adm -> T0) by stratum
-- ============================================================
select
    qualify_stratum_exe,
    count(*) as n,
    round(avg(adm_to_t0_hours)::numeric, 1) as mean_adm_to_t0_h,
    round(percentile_cont(0.25) within group (order by adm_to_t0_hours)::numeric, 1) as p25_h,
    round(percentile_cont(0.50) within group (order by adm_to_t0_hours)::numeric, 1) as median_h,
    round(percentile_cont(0.75) within group (order by adm_to_t0_hours)::numeric, 1) as p75_h,
    sum(case when adm_to_t0_hours < 2 then 1 else 0 end) as n_adm_to_t0_lt2h
from study_ahf_v3.audit_092_ahf_qualify_time_v1
where early_sepsis12_main_flag = 1
group by qualify_stratum_exe
order by qualify_stratum_exe;

-- ============================================================
-- QC5: sensitivity definition including pharmacy order time
-- (cross-tab exe vs all, main cohort)
-- ============================================================
select
    qualify_stratum_exe,
    qualify_stratum_all,
    count(*) as n,
    sum(primary_outcome_flag) as n_events
from study_ahf_v3.audit_092_ahf_qualify_time_v1
where early_sepsis12_main_flag = 1
group by qualify_stratum_exe, qualify_stratum_all
order by qualify_stratum_exe, qualify_stratum_all;

-- ============================================================
-- QC6: distribution of unconfirmed fraction in the 12h feature
-- window (main cohort): how much of 0-12h was pre-confirmation
-- ============================================================
select
    case
        when unconfirmed_frac_exe = 0 then '0_confirmed_by_t0'
        when unconfirmed_frac_exe < 0.25 then '0_25pct'
        when unconfirmed_frac_exe < 0.5 then '25_50pct'
        when unconfirmed_frac_exe < 1 then '50_99pct'
        else '1_icd_only'
    end as unconfirmed_frac_bucket,
    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(avg(primary_outcome_flag::numeric) * 100.0, 2) as event_rate_pct
from study_ahf_v3.audit_092_ahf_qualify_time_v1
where early_sepsis12_main_flag = 1
group by 1
order by 1;
