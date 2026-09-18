-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v3/audits/093_pre_t0_ahf_definition_audit.sql
-- Purpose:
--   Audit a revised pre-T0 AHF definition before any model rerun.
--
-- T0 = ICU intime
-- Main AHF evidence window = [hospital admittime, ICU intime)
-- Sensitivity AHF evidence window = [T0 - 24h, T0)
-- Predictor window = [T0, T0 + 12h)
-- Outcome window = [T0 + 12h, T0 + 60h)
--
-- AHF is considered time-established before T0 only when:
--   1) acute/acute-on-chronic HF ICD is present with sequence <= 5;
--   2) actual IV loop diuretic eMAR OR NT-proBNP >= 300 is recorded
--      during the current hospitalization before ICU admission.
--
-- Final ICD fields are retrospective phenotype anchors only.
-- This audit does not modify the existing modeling dataset.
-- ============================================================

drop table if exists study_ahf_v3.audit_093_pre_t0_ahf_definition_v1 cascade;

create table study_ahf_v3.audit_093_pre_t0_ahf_definition_v1 as
with riskset as (
    select
        r.stay_id,
        r.subject_id,
        r.hadm_id,
        r.intime,
        r.outtime,
        ad.admittime,
        o.hd_deterioration_broad_nee005_flag as primary_outcome_flag,
        o.complete60_icu_flag,
        o.death_12_60_flag,
        o.early_sepsis12_main_flag,
        a.hf_icd_acute_or_acute_on_chronic as acute_hf_icd_flag,
        a.hf_icd_seq_le5
    from study_ahf_v3.cohort_061D_landmark12_riskset_main_v1 r
    inner join study_ahf_v3.cohort_061A_ahf_evidence_early_window_12h_v1 a
        on r.stay_id = a.stay_id
    inner join study_ahf_v3.outcome_063C_candidate_hd_outcomes_with_nee_v1 o
        on r.stay_id = o.stay_id
    inner join mimiciv_hosp.admissions ad
        on r.hadm_id = ad.hadm_id
),

loop_emar as (
    select
        r.stay_id,
        min(e.charttime) as first_iv_loop_emar_adm_to_t0,
        min(e.charttime) filter (
            where e.charttime >= r.intime - interval '24 hour'
        ) as first_iv_loop_emar_pre24
    from riskset r
    inner join mimiciv_hosp.emar e
        on r.subject_id = e.subject_id
       and r.hadm_id = e.hadm_id
    left join mimiciv_hosp.emar_detail ed
        on e.emar_id = ed.emar_id
       and e.emar_seq = ed.emar_seq
    where e.charttime >= r.admittime
      and e.charttime < r.intime
      and (
            lower(coalesce(e.medication, '')) like '%furosemide%'
         or lower(coalesce(e.medication, '')) like '%bumetanide%'
         or lower(coalesce(e.medication, '')) like '%torsemide%'
         or lower(coalesce(e.medication, '')) like '%ethacrynic%'
         or lower(coalesce(ed.product_description, '')) like '%furosemide%'
         or lower(coalesce(ed.product_description, '')) like '%bumetanide%'
         or lower(coalesce(ed.product_description, '')) like '%torsemide%'
         or lower(coalesce(ed.product_description, '')) like '%ethacrynic%'
      )
      and (
            upper(coalesce(ed.route, '')) in ('IV', 'INTRAVENOUS')
         or lower(coalesce(ed.product_description, '')) like '%vial%'
         or lower(coalesce(ed.product_description, '')) like '%syringe%'
         or lower(coalesce(ed.product_description, '')) like '%inject%'
         or lower(coalesce(ed.product_description, '')) like '%infusion%'
         or lower(coalesce(ed.product_description, '')) like '%solution%'
         or lower(coalesce(ed.product_description, '')) like '%bag%'
         or lower(coalesce(ed.product_description, '')) like '%premix%'
         or lower(coalesce(ed.product_description, '')) like '%ampule%'
      )
      and lower(coalesce(e.event_txt, '')) not like '%not given%'
      and lower(coalesce(e.event_txt, '')) not like '%hold%'
      and lower(coalesce(ed.complete_dose_not_given, '')) not in ('yes', 'y', 'true', '1')
    group by r.stay_id
),

ntprobnp as (
    select
        r.stay_id,
        min(le.charttime) filter (
            where le.valuenum >= 300
        ) as first_ntprobnp_ge300_adm_to_t0,
        max(le.valuenum) as ntprobnp_max_adm_to_t0,
        min(le.charttime) filter (
            where le.charttime >= r.intime - interval '24 hour'
              and le.valuenum >= 300
        ) as first_ntprobnp_pre24,
        max(le.valuenum) filter (
            where le.charttime >= r.intime - interval '24 hour'
        ) as ntprobnp_max_pre24
    from riskset r
    inner join mimiciv_hosp.labevents le
        on r.subject_id = le.subject_id
       and r.hadm_id = le.hadm_id
    where le.itemid = 50963
      and le.valuenum is not null
      and le.charttime >= r.admittime
      and le.charttime < r.intime
    group by r.stay_id
),

flags as (
    select
        r.*,
        e.first_iv_loop_emar_adm_to_t0,
        e.first_iv_loop_emar_pre24,
        n.first_ntprobnp_ge300_adm_to_t0,
        n.ntprobnp_max_adm_to_t0,
        n.first_ntprobnp_pre24,
        n.ntprobnp_max_pre24,
        least(
            e.first_iv_loop_emar_adm_to_t0,
            n.first_ntprobnp_ge300_adm_to_t0
        ) as ahf_qualify_time_adm_to_t0,
        case
            when r.acute_hf_icd_flag = 1
             and r.hf_icd_seq_le5 = 1
             and (
                    e.first_iv_loop_emar_adm_to_t0 is not null
                 or n.first_ntprobnp_ge300_adm_to_t0 is not null
             )
            then 1 else 0
        end as ahf_pre_t0_confirmed_flag,
        case
            when r.acute_hf_icd_flag = 1
             and r.hf_icd_seq_le5 = 1
             and (
                    e.first_iv_loop_emar_pre24 is not null
                 or n.first_ntprobnp_pre24 is not null
             )
            then 1 else 0
        end as ahf_pre24_confirmed_flag
    from riskset r
    left join loop_emar e
        on r.stay_id = e.stay_id
    left join ntprobnp n
        on r.stay_id = n.stay_id
)

select
    f.*,
    case
        when ahf_qualify_time_adm_to_t0 is null then 'icd_only'
        else 'time_evidence_pre_t0'
    end as ahf_qualification_stratum,
    case
        when ahf_qualify_time_adm_to_t0 is null then null::numeric
        else extract(
            epoch from (ahf_qualify_time_adm_to_t0 - intime)
        ) / 3600.0
    end as ahf_qualify_offset_h
from flags f;

create index if not exists idx_093_pre_t0_ahf_stay
    on study_ahf_v3.audit_093_pre_t0_ahf_definition_v1 (stay_id);

analyze study_ahf_v3.audit_093_pre_t0_ahf_definition_v1;

select
    definition,
    count(*) as n_stays,
    sum(primary_outcome_flag) as n_events,
    round(avg(primary_outcome_flag::numeric) * 100.0, 2) as event_rate_pct,
    sum(complete60_icu_flag) as n_complete60,
    sum(death_12_60_flag) as n_death_12_60,
    sum(case when early_sepsis12_main_flag = 1 then 1 else 0 end) as n_early_sepsis12
from (
    select
        '00_existing_landmark_riskset'::text as definition,
        primary_outcome_flag,
        complete60_icu_flag,
        death_12_60_flag,
        early_sepsis12_main_flag
    from study_ahf_v3.audit_093_pre_t0_ahf_definition_v1

    union all

    select
        '01_pre_t0_admission_to_icu',
        primary_outcome_flag,
        complete60_icu_flag,
        death_12_60_flag,
        early_sepsis12_main_flag
    from study_ahf_v3.audit_093_pre_t0_ahf_definition_v1
    where ahf_pre_t0_confirmed_flag = 1

    union all

    select
        '02_pre24_strict_sensitivity',
        primary_outcome_flag,
        complete60_icu_flag,
        death_12_60_flag,
        early_sepsis12_main_flag
    from study_ahf_v3.audit_093_pre_t0_ahf_definition_v1
    where ahf_pre24_confirmed_flag = 1

    union all

    select
        '03_icd_only_excluded_from_primary',
        primary_outcome_flag,
        complete60_icu_flag,
        death_12_60_flag,
        early_sepsis12_main_flag
    from study_ahf_v3.audit_093_pre_t0_ahf_definition_v1
    where ahf_pre_t0_confirmed_flag = 0
      and acute_hf_icd_flag = 1
      and hf_icd_seq_le5 = 1
) x
group by definition
order by definition;

select
    ahf_pre_t0_confirmed_flag,
    ahf_pre24_confirmed_flag,
    acute_hf_icd_flag,
    count(*) as n,
    sum(primary_outcome_flag) as n_events
from study_ahf_v3.audit_093_pre_t0_ahf_definition_v1
group by 1, 2, 3
order by 1, 2, 3;

select
    case
        when ahf_qualify_offset_h is null then '00_icd_only'
        when ahf_qualify_offset_h < -24 then '01_adm_to_t0_earlier_than_24h'
        when ahf_qualify_offset_h < 0 then '02_pre_t0_last_24h'
        else '03_invalid_post_t0'
    end as qualify_timing_group,
    count(*) as n,
    sum(primary_outcome_flag) as n_events
from study_ahf_v3.audit_093_pre_t0_ahf_definition_v1
where ahf_pre_t0_confirmed_flag = 1
   or (acute_hf_icd_flag = 1 and hf_icd_seq_le5 = 1)
group by 1
order by 1;
