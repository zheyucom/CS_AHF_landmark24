-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v4_2/audits/094A_audit_pre_t0_ahf_filter_flow.sql
-- Purpose:
--   Audit why the strict pre-T0 AHF-only cohort contains 452 stays.
--
-- T0 = ICU intime
-- Main strict window currently used by v4.2: [T0-24h, T0)
-- Sensitivity window: [hospital admittime, T0)
--
-- This is an audit only. It does not modify the modeling cohort.
-- Final ICD codes are retrospective phenotype anchors; the timing
-- evidence is evaluated separately and is not a predictor.
-- ============================================================

drop table if exists study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1 cascade;

create table study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1 as
with riskset as (
    select
        r.stay_id,
        r.subject_id,
        r.hadm_id,
        r.intime,
        ad.admittime,
        o.hd_deterioration_broad_nee005_flag as primary_outcome_flag,
        o.complete60_icu_flag,
        a.hf_icd_acute_or_acute_on_chronic,
        a.hf_icd_seq_le5
    from study_ahf_v4.cohort_061D_landmark12_riskset_main_v1 r
    inner join study_ahf_v4.cohort_061A_ahf_evidence_early_window_12h_v1 a
        on r.stay_id = a.stay_id
    inner join study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1 o
        on r.stay_id = o.stay_id
    inner join mimiciv_hosp.admissions ad
        on r.hadm_id = ad.hadm_id
),

loop_emar as (
    select
        r.stay_id,
        min(e.charttime) filter (
            where e.charttime >= r.intime - interval '24 hour'
              and e.charttime < r.intime
        ) as first_iv_loop_pre24,
        min(e.charttime) filter (
            where e.charttime >= r.admittime
              and e.charttime < r.intime
        ) as first_iv_loop_adm_to_t0
    from riskset r
    inner join mimiciv_hosp.emar e
        on r.subject_id = e.subject_id
       and r.hadm_id = e.hadm_id
    left join mimiciv_hosp.emar_detail ed
        on e.emar_id = ed.emar_id
       and e.emar_seq = ed.emar_seq
    where e.charttime < r.intime
      and e.charttime >= r.admittime
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
        max(le.valuenum) filter (
            where le.charttime >= r.intime - interval '24 hour'
              and le.charttime < r.intime
        ) as ntprobnp_max_pre24,
        max(le.valuenum) filter (
            where le.charttime >= r.admittime
              and le.charttime < r.intime
        ) as ntprobnp_max_adm_to_t0
    from riskset r
    inner join mimiciv_hosp.labevents le
        on r.subject_id = le.subject_id
       and r.hadm_id = le.hadm_id
    where le.itemid = 50963
      and le.valuenum is not null
      and le.charttime < r.intime
      and le.charttime >= r.admittime
    group by r.stay_id
),

flags as (
    select
        r.*,
        e.first_iv_loop_pre24,
        e.first_iv_loop_adm_to_t0,
        n.ntprobnp_max_pre24,
        n.ntprobnp_max_adm_to_t0,

        case
            when r.hf_icd_acute_or_acute_on_chronic = 1
             and r.hf_icd_seq_le5 = 1
             and (
                    e.first_iv_loop_pre24 is not null
                 or n.ntprobnp_max_pre24 >= 300
             )
            then 1 else 0
        end as strict_pre_t0_24h_flag,

        case
            when r.hf_icd_acute_or_acute_on_chronic = 1
             and r.hf_icd_seq_le5 = 1
             and (
                    e.first_iv_loop_adm_to_t0 is not null
                 or n.ntprobnp_max_adm_to_t0 >= 300
             )
            then 1 else 0
        end as strict_pre_t0_admission_to_t0_flag
    from riskset r
    left join loop_emar e
        on r.stay_id = e.stay_id
    left join ntprobnp n
        on r.stay_id = n.stay_id
)

select *
from flags;

create index if not exists idx_094a_pre_t0_ahf_stay
    on study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1 (stay_id);

analyze study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1;

-- Overall filtering flow.
select
    stage,
    n_stays,
    n_events,
    round(n_events * 100.0 / nullif(n_stays, 0), 2) as event_rate_pct,
    n_complete60
from (
    select
        '01_adult_first_icu'::text as stage,
        count(*) as n_stays,
        null::bigint as n_events,
        null::bigint as n_complete60
    from study_ahf_v4.cohort_010_adult_first_icu_v1

    union all
    select
        '02_hf_icd_candidate',
        count(*),
        null::bigint,
        null::bigint
    from study_ahf_v4.cohort_020_hf_icd_candidate_v1

    union all
    select
        '03_strict_ahf_12h',
        count(*),
        null::bigint,
        null::bigint
    from study_ahf_v4.cohort_061B_ahf_strict_12h_v1

    union all
    select
        '04_reached_12h_landmark',
        count(*),
        null::bigint,
        null::bigint
    from study_ahf_v4.outcome_061C_pre12_overt_cs_flags_v1
    where reached_12h_landmark_flag = 1

    union all
    select
        '05_riskset_no_pre12_overt_cs',
        count(*),
        null::bigint,
        null::bigint
    from study_ahf_v4.cohort_061D_landmark12_riskset_main_v1

    union all
    select
        '06_strict_pre_t0_ahf_24h',
        count(*) filter (where strict_pre_t0_24h_flag = 1),
        sum(primary_outcome_flag) filter (where strict_pre_t0_24h_flag = 1),
        sum(complete60_icu_flag) filter (where strict_pre_t0_24h_flag = 1)
    from study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1

    union all
    select
        '07_strict_pre_t0_ahf_admission_to_t0',
        count(*) filter (where strict_pre_t0_admission_to_t0_flag = 1),
        sum(primary_outcome_flag) filter (where strict_pre_t0_admission_to_t0_flag = 1),
        sum(complete60_icu_flag) filter (where strict_pre_t0_admission_to_t0_flag = 1)
    from study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1
) x
order by stage;

-- Components of the two pre-T0 definitions within the 12h risk set.
select
    '24h'::text as window,
    count(*) as n_riskset,
    sum(case when hf_icd_acute_or_acute_on_chronic = 1 then 1 else 0 end) as n_acute_hf_icd,
    sum(case when first_iv_loop_pre24 is not null then 1 else 0 end) as n_iv_loop_emar,
    sum(case when ntprobnp_max_pre24 >= 300 then 1 else 0 end) as n_ntprobnp_ge300,
    sum(strict_pre_t0_24h_flag) as n_strict_ahf,
    sum(primary_outcome_flag) filter (where strict_pre_t0_24h_flag = 1) as n_events
from study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1

union all

select
    'admission_to_t0',
    count(*),
    sum(case when hf_icd_acute_or_acute_on_chronic = 1 then 1 else 0 end),
    sum(case when first_iv_loop_adm_to_t0 is not null then 1 else 0 end),
    sum(case when ntprobnp_max_adm_to_t0 >= 300 then 1 else 0 end),
    sum(strict_pre_t0_admission_to_t0_flag),
    sum(primary_outcome_flag) filter (where strict_pre_t0_admission_to_t0_flag = 1)
from study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1;

-- Definition cross-tab: identifies stays rescued by the wider pre-T0 window.
select
    strict_pre_t0_24h_flag,
    strict_pre_t0_admission_to_t0_flag,
    count(*) as n,
    sum(primary_outcome_flag) as events
from study_ahf_v4_2.audit_094a_pre_t0_ahf_filter_flow_v1
group by strict_pre_t0_24h_flag, strict_pre_t0_admission_to_t0_flag
order by strict_pre_t0_24h_flag, strict_pre_t0_admission_to_t0_flag;
