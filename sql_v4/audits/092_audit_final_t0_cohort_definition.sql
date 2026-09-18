-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v4/audits/092_audit_final_t0_cohort_definition.sql
-- Purpose:
--   Freeze and audit a clinically interpretable T0 cohort:
--   AHF evidence before ICU admission + infection suspected before
--   ICU admission + Sepsis-3 operational confirmation by T12.
--
-- T0 = ICU intime
-- Pre-T0 evidence window = [T0 - 24 h, T0)
-- Predictor window = [T0, T0 + 12 h)
-- Outcome window = [T0 + 12 h, T0 + 60 h)
--
-- Important:
--   Final ICD codes are retrospective phenotype anchors only.
--   They must not be used as predictors.
--   The main flag uses a broad, cross-site-operational AHF time
--   evidence definition. A high-specificity definition is retained
--   as a sensitivity analysis because its sample size may be too small.
-- ============================================================

drop table if exists study_ahf_v4.audit_092_final_t0_definition_v1 cascade;

create table study_ahf_v4.audit_092_final_t0_definition_v1 as
with riskset as (
    select
        r.subject_id,
        r.hadm_id,
        r.stay_id,
        r.intime,
        r.outtime,
        r.icu_los_hours,
        r.reached_12h_landmark_flag,
        r.pre12_overt_cs_main_flag,
        a.hf_icd_any,
        a.hf_icd_acute_or_acute_on_chronic,
        a.hf_icd_primary_seq,
        a.hf_icd_seq_le5,
        a.iv_loop_rx_first_starttime_early12,
        a.loop_emar_first_charttime_early12,
        a.ntprobnp_first_charttime_early12,
        a.ntprobnp_max_early12,
        o.early_sepsis_admission_present_flag,
        o.early_sepsis12_first_suspected_infection_time,
        o.early_sepsis12_first_antibiotic_time,
        o.early_sepsis12_first_culture_time,
        o.early_sepsis12_first_sofa_time,
        o.early_sepsis12_max_sofa_score,
        o.primary_outcome_flag,
        o.secondary_hd_deterioration_nee010_flag,
        o.secondary_hd_deterioration_no_nee_flag,
        o.secondary_mixed_shock_proxy_flag,
        o.death_12_60_flag
    from study_ahf_v4.cohort_061d_landmark12_riskset_main_v1 r
    inner join study_ahf_v4.cohort_061a_ahf_evidence_early_window_12h_v1 a
        on r.stay_id = a.stay_id
    inner join study_ahf_v4.outcome_064_primary_hd_deterioration_v1 o
        on r.stay_id = o.stay_id
),

-- Re-evaluate eMAR at the row level so a pre-T0 oral tablet is not
-- accidentally paired with an IV-looking administration later in 0-12 h.
loop_emar_pre_t0 as (
    select
        b.stay_id,
        min(e.charttime) as first_loop_emar_any_pre_t0,
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
    from riskset b
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

flags as (
    select
        r.*,
        e.first_loop_emar_any_pre_t0,
        e.first_loop_emar_iv_pre_t0,

        case
            when r.hf_icd_any = 1
             and r.hf_icd_seq_le5 = 1
             and (
                    r.iv_loop_rx_first_starttime_early12 >= r.intime - interval '24 hour'
                and r.iv_loop_rx_first_starttime_early12 < r.intime
                 or e.first_loop_emar_any_pre_t0 is not null
                 or (
                        r.ntprobnp_first_charttime_early12 >= r.intime - interval '24 hour'
                    and r.ntprobnp_first_charttime_early12 < r.intime
                    and r.ntprobnp_max_early12 >= 300
                 )
             )
            then 1 else 0
        end as ahf_pre_t0_broad_flag,

        case
            when r.hf_icd_acute_or_acute_on_chronic = 1
             and r.hf_icd_seq_le5 = 1
             and (
                    e.first_loop_emar_iv_pre_t0 is not null
                 or (
                        r.ntprobnp_first_charttime_early12 >= r.intime - interval '24 hour'
                    and r.ntprobnp_first_charttime_early12 < r.intime
                    and r.ntprobnp_max_early12 >= 300
                 )
             )
            then 1 else 0
        end as ahf_pre_t0_high_specificity_flag

    from riskset r
    left join loop_emar_pre_t0 e
        on r.stay_id = e.stay_id
)

select
    f.*,

    case
        when f.ahf_pre_t0_broad_flag = 1
         and f.early_sepsis_admission_present_flag = 1
        then 1 else 0
    end as final_t0_ahf_sepsis_broad_flag,

    case
        when f.ahf_pre_t0_high_specificity_flag = 1
         and f.early_sepsis_admission_present_flag = 1
        then 1 else 0
    end as final_t0_ahf_sepsis_high_specificity_flag,

    'AHF evidence pre-T0; infection suspected pre-T0; Sepsis-3 sources confirmed by T12; no pre12 overt-CS proxy'::text
        as final_broad_definition,
    'Acute-HF ICD sequence <=5 plus pre-T0 IV-loop eMAR or NT-proBNP >=300; same sepsis rule'::text
        as final_high_specificity_definition

from flags f;

create index if not exists idx_audit_092_final_t0_stay
    on study_ahf_v4.audit_092_final_t0_definition_v1 (stay_id);

analyze study_ahf_v4.audit_092_final_t0_definition_v1;

-- QC1: explicit cohort feasibility and event rate.
select
    cohort_rule,
    count(*) as n_stays,
    sum(primary_outcome_flag) as n_primary_events,
    round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2) as primary_event_rate_pct,
    sum(case when complete60_flag = 1 then 1 else 0 end) as n_complete60
from (
    select
        '00_current_v4_admission_present'::text as cohort_rule,
        primary_outcome_flag,
        case when outtime >= intime + interval '60 hour' then 1 else 0 end as complete60_flag
    from study_ahf_v4.audit_092_final_t0_definition_v1
    where early_sepsis_admission_present_flag = 1

    union all
    select
        '01_AHF_preT0_broad_plus_sepsis_admission_present',
        primary_outcome_flag,
        case when outtime >= intime + interval '60 hour' then 1 else 0 end
    from study_ahf_v4.audit_092_final_t0_definition_v1
    where final_t0_ahf_sepsis_broad_flag = 1

    union all
    select
        '02_AHF_preT0_high_specificity_plus_sepsis_admission_present',
        primary_outcome_flag,
        case when outtime >= intime + interval '60 hour' then 1 else 0 end
    from study_ahf_v4.audit_092_final_t0_definition_v1
    where final_t0_ahf_sepsis_high_specificity_flag = 1
) x
group by cohort_rule
order by cohort_rule;

-- QC2: components of the broad T0 definition.
select
    ahf_pre_t0_broad_flag,
    ahf_pre_t0_high_specificity_flag,
    early_sepsis_admission_present_flag,
    count(*) as n,
    sum(primary_outcome_flag) as events
from study_ahf_v4.audit_092_final_t0_definition_v1
group by 1, 2, 3
order by 1, 2, 3;

-- QC3: source timing required by the sepsis operational definition.
select
    count(*) as n_broad_t0_cohort,
    sum(case when early_sepsis12_first_suspected_infection_time < intime then 1 else 0 end) as n_infection_suspected_pre_t0,
    sum(case when early_sepsis12_first_antibiotic_time < intime + interval '12 hour' then 1 else 0 end) as n_antibiotic_by_t12,
    sum(case when early_sepsis12_first_culture_time < intime + interval '12 hour' then 1 else 0 end) as n_culture_by_t12,
    sum(case when early_sepsis12_first_sofa_time < intime + interval '12 hour' then 1 else 0 end) as n_sofa_by_t12,
    min(early_sepsis12_max_sofa_score) as min_max_sofa,
    percentile_cont(0.5) within group (order by early_sepsis12_max_sofa_score) as p50_max_sofa
from study_ahf_v4.audit_092_final_t0_definition_v1
where final_t0_ahf_sepsis_broad_flag = 1;

-- QC4: export-ready summary used by the project report.
select
    'broad' as definition,
    count(*) as n,
    sum(primary_outcome_flag) as events,
    round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2) as event_rate_pct,
    sum(death_12_60_flag) as deaths_12_60,
    sum(secondary_hd_deterioration_nee010_flag) as nee010_events,
    sum(secondary_hd_deterioration_no_nee_flag) as no_nee_events,
    sum(secondary_mixed_shock_proxy_flag) as mixed_shock_events
from study_ahf_v4.audit_092_final_t0_definition_v1
where final_t0_ahf_sepsis_broad_flag = 1
union all
select
    'high_specificity', count(*), sum(primary_outcome_flag),
    round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2),
    sum(death_12_60_flag), sum(secondary_hd_deterioration_nee010_flag),
    sum(secondary_hd_deterioration_no_nee_flag), sum(secondary_mixed_shock_proxy_flag)
from study_ahf_v4.audit_092_final_t0_definition_v1
where final_t0_ahf_sepsis_high_specificity_flag = 1;
