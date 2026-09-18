-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/01_cohort/061A_create_ahf_evidence_table_12h.sql
-- Purpose:
--   Create AHF evidence table for the 12h landmark analysis.
--
-- Key difference from previous 030D table:
--   Early AHF evidence window is ICU intime -24h to +12h,
--   not -24h to +24h.
--
-- This avoids using 12-24h information to define the cohort
-- when the prediction landmark is 12h.
-- ============================================================

drop table if exists study_ahf_v3.cohort_061A_ahf_evidence_early_window_12h_v1 cascade;

create table study_ahf_v3.cohort_061A_ahf_evidence_early_window_12h_v1 as
with base as (
    select *
    from study_ahf_v3.cohort_020_hf_icd_candidate_v1
),

ntprobnp_early as (
    select
        b.stay_id,
        count(*) as ntprobnp_n_measurements_early12,
        min(le.charttime) as ntprobnp_first_charttime_early12,
        max(le.valuenum) as ntprobnp_max_early12,
        min(le.valuenum) as ntprobnp_min_early12
    from base b
    inner join mimiciv_hosp.labevents le
        on b.subject_id = le.subject_id
       and b.hadm_id = le.hadm_id
    where le.itemid = 50963
      and le.valuenum is not null
      and le.charttime >= b.intime - interval '24 hour'
      and le.charttime <  b.intime + interval '12 hour'
    group by b.stay_id
),

iv_loop_rx_early as (
    select
        b.stay_id,
        count(*) as iv_loop_rx_n_orders_early12,
        min(p.starttime) as iv_loop_rx_first_starttime_early12
    from base b
    inner join mimiciv_hosp.prescriptions p
        on b.subject_id = p.subject_id
       and b.hadm_id = p.hadm_id
    where (
            lower(p.drug) like '%furosemide%'
         or lower(p.drug) like '%bumetanide%'
         or lower(p.drug) like '%torsemide%'
         or lower(p.drug) like '%ethacrynic%'
    )
      and (
            upper(coalesce(p.route, '')) like '%IV%'
         or upper(coalesce(p.route, '')) like '%INTRAVENOUS%'
         or upper(coalesce(p.route, '')) like '%INJ%'
      )
      and p.starttime <  b.intime + interval '12 hour'
      and coalesce(p.stoptime, p.starttime) >= b.intime - interval '24 hour'
    group by b.stay_id
),

loop_emar_early as (
    select
        b.stay_id,
        count(*) as loop_emar_n_records_early12,
        min(e.charttime) as loop_emar_first_charttime_early12,

        sum(
            case
                when upper(coalesce(ed.route, '')) in ('PO', 'NG', 'ORAL', 'G TUBE', 'GT', 'PEG')
                    then 1
                else 0
            end
        ) as loop_emar_oral_or_enteral_n_early12,

        sum(
            case
                when lower(coalesce(ed.product_description, '')) like '%vial%'
                  or lower(coalesce(ed.product_description, '')) like '%syringe%'
                  or lower(coalesce(ed.product_description, '')) like '%inject%'
                  or lower(coalesce(ed.product_description, '')) like '%infusion%'
                  or lower(coalesce(ed.product_description, '')) like '%iv%'
                  or lower(coalesce(ed.product_description, '')) like '%conc:%'
                  or lower(coalesce(e.medication, '')) like '%in 0.9% sodium chloride%'
                    then 1
                else 0
            end
        ) as loop_emar_possible_iv_formulation_n_early12

    from base b
    inner join mimiciv_hosp.emar e
        on b.subject_id = e.subject_id
       and b.hadm_id = e.hadm_id
    left join mimiciv_hosp.emar_detail ed
        on e.emar_id = ed.emar_id
       and e.emar_seq = ed.emar_seq
    where (
            lower(coalesce(e.medication, '')) like '%furosemide%'
         or lower(coalesce(e.medication, '')) like '%bumetanide%'
         or lower(coalesce(e.medication, '')) like '%torsemide%'
         or lower(coalesce(e.medication, '')) like '%ethacrynic%'
         or lower(coalesce(ed.product_description, '')) like '%furosemide%'
         or lower(coalesce(ed.product_description, '')) like '%bumetanide%'
         or lower(coalesce(ed.product_description, '')) like '%torsemide%'
         or lower(coalesce(ed.product_description, '')) like '%ethacrynic%'
    )
      and e.charttime >= b.intime - interval '24 hour'
      and e.charttime <  b.intime + interval '12 hour'
      and lower(coalesce(e.event_txt, '')) not like '%not given%'
      and lower(coalesce(e.event_txt, '')) not like '%hold%'
      and lower(coalesce(ed.complete_dose_not_given, '')) not in ('yes', 'y', 'true', '1')
    group by b.stay_id
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

    b.hf_icd_any,
    b.hf_icd_i50_or_428,
    b.hf_icd_hypertensive_hf,
    b.hf_icd_acute_or_acute_on_chronic,
    b.hf_icd_primary_seq,
    b.hf_icd_codes,
    b.hf_icd_titles,

    case
        when b.hf_icd_primary_seq <= 5 then 1
        else 0
    end as hf_icd_seq_le5,

    case
        when b.hf_icd_primary_seq = 1 then 1
        else 0
    end as hf_icd_seq_eq1,

    coalesce(n.ntprobnp_n_measurements_early12, 0) as ntprobnp_n_measurements_early12,
    n.ntprobnp_first_charttime_early12,
    n.ntprobnp_max_early12,
    n.ntprobnp_min_early12,

    case
        when coalesce(n.ntprobnp_n_measurements_early12, 0) > 0 then 1
        else 0
    end as ntprobnp_measured_early12_flag,

    case
        when n.ntprobnp_max_early12 >= 300 then 1
        else 0
    end as ntprobnp_ge300_early12_flag,

    case
        when n.ntprobnp_max_early12 >= 900 then 1
        else 0
    end as ntprobnp_ge900_early12_flag,

    case
        when n.ntprobnp_max_early12 >= 1800 then 1
        else 0
    end as ntprobnp_ge1800_early12_flag,

    coalesce(rx.iv_loop_rx_n_orders_early12, 0) as iv_loop_rx_n_orders_early12,
    rx.iv_loop_rx_first_starttime_early12,

    case
        when coalesce(rx.iv_loop_rx_n_orders_early12, 0) > 0 then 1
        else 0
    end as iv_loop_rx_early12_flag,

    coalesce(em.loop_emar_n_records_early12, 0) as loop_emar_n_records_early12,
    em.loop_emar_first_charttime_early12,
    coalesce(em.loop_emar_oral_or_enteral_n_early12, 0) as loop_emar_oral_or_enteral_n_early12,
    coalesce(em.loop_emar_possible_iv_formulation_n_early12, 0) as loop_emar_possible_iv_formulation_n_early12,

    case
        when coalesce(em.loop_emar_n_records_early12, 0) > 0 then 1
        else 0
    end as loop_emar_any_early12_flag,

    case
        when coalesce(em.loop_emar_possible_iv_formulation_n_early12, 0) > 0 then 1
        else 0
    end as iv_loop_emar_formulation_early12_flag,

    (
        case when b.hf_icd_acute_or_acute_on_chronic = 1 then 1 else 0 end
      + case when b.hf_icd_primary_seq <= 5 then 1 else 0 end
      + case when coalesce(rx.iv_loop_rx_n_orders_early12, 0) > 0 then 1 else 0 end
      + case when n.ntprobnp_max_early12 >= 300 then 1 else 0 end
    ) as ahf_evidence_score_primary_12h

from base b
left join ntprobnp_early n
    on b.stay_id = n.stay_id
left join iv_loop_rx_early rx
    on b.stay_id = rx.stay_id
left join loop_emar_early em
    on b.stay_id = em.stay_id;
		
		
		
		
-- 		061A 质控查询
select
    count(*) as n_total,

    sum(hf_icd_acute_or_acute_on_chronic) as n_acute_icd,
    round(sum(hf_icd_acute_or_acute_on_chronic) * 100.0 / count(*), 2) as pct_acute_icd,

    sum(hf_icd_seq_le5) as n_hf_seq_le5,
    round(sum(hf_icd_seq_le5) * 100.0 / count(*), 2) as pct_hf_seq_le5,

    sum(ntprobnp_ge300_early12_flag) as n_ntprobnp_ge300_early12,
    round(sum(ntprobnp_ge300_early12_flag) * 100.0 / count(*), 2) as pct_ntprobnp_ge300_early12,

    sum(iv_loop_rx_early12_flag) as n_iv_loop_rx_early12,
    round(sum(iv_loop_rx_early12_flag) * 100.0 / count(*), 2) as pct_iv_loop_rx_early12,

    sum(loop_emar_any_early12_flag) as n_loop_emar_any_early12,
    round(sum(loop_emar_any_early12_flag) * 100.0 / count(*), 2) as pct_loop_emar_any_early12

from study_ahf_v3.cohort_061A_ahf_evidence_early_window_12h_v1;


