-- ============================================================
-- Project: CS_AHF_landmark24
-- Version: v4.2 AHF-only, strict pre-T0 AHF
-- Purpose:
--   Remove the early-sepsis inclusion requirement while retaining
--   the previously fixed pre-T0 AHF requirement.
--
-- T0 = ICU intime
-- AHF must have retrospective acute/acute-on-chronic HF diagnosis
-- in a high admission sequence (<=5) and objective AHF evidence
-- before T0: IV-loop eMAR or pre-T0 NT-proBNP >=300.
--
-- The cohort still comes from the 12 h landmark risk set and therefore
-- retains: adult first ICU stay, reached T12, and no pre12 overt-CS proxy.
-- No early-sepsis filter is applied.
-- ============================================================

drop table if exists study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1 cascade;

create table study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1 as
with base as (
    select
        o.*,
        a.first_careunit,
        a.last_careunit,
        a.icu_los_hours,
        a.gender,
        a.anchor_age,
        a.hf_icd_any,
        a.hf_icd_acute_or_acute_on_chronic,
        a.hf_icd_primary_seq,
        a.hf_icd_seq_le5,
        a.iv_loop_rx_early12_flag,
        a.ntprobnp_ge300_early12_flag,
        a.ahf_evidence_score_primary_12h,
        a.iv_loop_rx_first_starttime_early12,
        a.ntprobnp_first_charttime_early12,
        a.ntprobnp_max_early12
    from study_ahf_v4.outcome_063c_candidate_hd_outcomes_with_nee_v1 o
    inner join study_ahf_v4.cohort_061a_ahf_evidence_early_window_12h_v1 a
        on o.stay_id = a.stay_id
),

loop_emar_pre_t0 as (
    select
        b.stay_id,
        min(e.charttime) filter (
            where upper(coalesce(ed.route, '')) in ('IV', 'INTRAVENOUS')
               or lower(coalesce(ed.product_description, '')) like '%vial%'
               or lower(coalesce(ed.product_description, '')) like '%syringe%'
               or lower(coalesce(ed.product_description, '')) like '%inject%'
               or lower(coalesce(ed.product_description, '')) like '%infusion%'
               or lower(coalesce(ed.product_description, '')) like '%solution%'
               or lower(coalesce(ed.product_description, '')) like '%bag%'
               or lower(coalesce(ed.product_description, '')) like '%premix%'
               or lower(coalesce(ed.product_description, '')) like '%ampule%'
        ) as first_loop_emar_iv_pre_t0
    from base b
    inner join mimiciv_hosp.emar e
        on b.subject_id = e.subject_id
       and b.hadm_id = e.hadm_id
    left join mimiciv_hosp.emar_detail ed
        on e.emar_id = ed.emar_id
       and e.emar_seq = ed.emar_seq
    where e.charttime >= b.intime - interval '24 hour'
      and e.charttime < b.intime
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
      and lower(coalesce(e.event_txt, '')) not like '%not given%'
      and lower(coalesce(e.event_txt, '')) not like '%hold%'
      and lower(coalesce(ed.complete_dose_not_given, '')) not in ('yes', 'y', 'true', '1')
    group by b.stay_id
),

-- Recompute NT-proBNP strictly before T0. The inherited early12
-- summary spans T0 to T12 and cannot be used for cohort definition.
ntprobnp_pre_t0 as (
    select
        b.stay_id,
        count(*) as ntprobnp_pre_t0_n,
        min(le.charttime) as ntprobnp_pre_t0_first_charttime,
        max(le.valuenum) as ntprobnp_pre_t0_max
    from base b
    inner join mimiciv_hosp.labevents le
        on b.subject_id = le.subject_id
       and b.hadm_id = le.hadm_id
    where le.itemid = 50963
      and le.valuenum is not null
      and le.charttime >= b.intime - interval '24 hour'
      and le.charttime < b.intime
    group by b.stay_id
),

flags as (
    select
        b.*,
        e.first_loop_emar_iv_pre_t0,
        n.ntprobnp_pre_t0_n,
        n.ntprobnp_pre_t0_first_charttime,
        n.ntprobnp_pre_t0_max,
        case
            when b.hf_icd_acute_or_acute_on_chronic = 1
             and b.hf_icd_seq_le5 = 1
             and (
                    e.first_loop_emar_iv_pre_t0 is not null
                 or (
                        n.ntprobnp_pre_t0_first_charttime is not null
                    and n.ntprobnp_pre_t0_max >= 300
                 )
             )
            then 1 else 0
        end as strict_pre_t0_ahf_flag
    from base b
    left join loop_emar_pre_t0 e
        on b.stay_id = e.stay_id
    left join ntprobnp_pre_t0 n
        on b.stay_id = n.stay_id
)

select
    f.*,
    'strict pre-T0 AHF: acute/acute-on-chronic HF ICD with seq <=5 plus pre-T0 IV-loop eMAR or pre-T0 NT-proBNP >=300; no sepsis inclusion criterion'::text
        as cohort_definition
from flags f
where strict_pre_t0_ahf_flag = 1;

create index if not exists idx_093a_strict_pre_t0_ahf_stay
    on study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1 (stay_id);

analyze study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1;

select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(hd_deterioration_broad_nee005_flag) as n_events,
    round(sum(hd_deterioration_broad_nee005_flag) * 100.0 / nullif(count(*), 0), 2) as event_rate_pct,
    sum(complete60_icu_flag) as n_complete60,
    sum(death_12_60_flag) as n_death_12_60,
    sum(hd_deterioration_broad_nee010_flag) as n_nee010,
    sum(hd_deterioration_broad_flag) as n_no_nee
from study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1;

insert into study_ahf_v4_2.cohort_flow (
    step_id, step_name, table_name, n_rows, n_subjects, n_hadm, n_stay,
    excluded_from_prior, notes
)
select
    93,
    'strict_pre_t0_ahf_only_no_sepsis_filter',
    'study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1',
    count(*), count(distinct subject_id), count(distinct hadm_id), count(distinct stay_id),
    null,
    'AHF-only analysis; strict pre-T0 AHF definition retained; 12h landmark and no pre12 overt-CS proxy retained; no early-sepsis inclusion filter.'
from study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1;
