-- Revised AHF evidence path. Historical v1 remains unchanged.
-- NT-proBNP uses the raw contract layer and availability_time in [T0-24h,T12).

drop table if exists study_ahf_v3_3.cohort_061A_ahf_evidence_early_window_12h_v2 cascade;

create table study_ahf_v3_3.cohort_061A_ahf_evidence_early_window_12h_v2 as
with base as (
    select *
    from study_ahf_v3_2.cohort_020_hf_icd_candidate_v1
),
ntprobnp_episode_candidates as (
    select
        b.stay_id,
        le.labevent_id,
        le.charttime,
        le.availability_time,
        le.result_class,
        le.censor_type,
        le.lower_bound,
        le.upper_bound,
        le.analysis_value,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base b
    join study_ahf_v3_3.lab_eligible_v1 le
     on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.concept = 'ntprobnp'
     and le.charttime >= b.intime - interval '24 hour'
     and le.charttime < b.intime + interval '12 hour'
     and le.availability_time >= b.intime - interval '24 hour'
     and le.availability_time < b.intime + interval '12 hour'
),
ntprobnp_classified as (
    select
        c.*,
        case
            when c.analysis_value >= 300 then 'definitely_above'
            when c.result_class = 'right_censored' and c.lower_bound >= 300 then 'definitely_above'
            when c.result_class = 'interval_censored' and c.lower_bound >= 300 then 'definitely_above'
            when c.analysis_value < 300 then 'definitely_below'
            when c.result_class = 'left_censored' and c.upper_bound <= 300 then 'definitely_below'
            when c.result_class = 'interval_censored' and c.upper_bound < 300 then 'definitely_below'
            else 'indeterminate_censored'
        end as ntprobnp_300_state,
        case
            when c.analysis_value >= 900 then 'definitely_above'
            when c.result_class = 'right_censored' and c.lower_bound >= 900 then 'definitely_above'
            when c.result_class = 'interval_censored' and c.lower_bound >= 900 then 'definitely_above'
            when c.analysis_value < 900 then 'definitely_below'
            when c.result_class = 'left_censored' and c.upper_bound <= 900 then 'definitely_below'
            when c.result_class = 'interval_censored' and c.upper_bound < 900 then 'definitely_below'
            else 'indeterminate_censored'
        end as ntprobnp_900_state,
        case
            when c.analysis_value >= 1800 then 'definitely_above'
            when c.result_class = 'right_censored' and c.lower_bound >= 1800 then 'definitely_above'
            when c.result_class = 'interval_censored' and c.lower_bound >= 1800 then 'definitely_above'
            when c.analysis_value < 1800 then 'definitely_below'
            when c.result_class = 'left_censored' and c.upper_bound <= 1800 then 'definitely_below'
            when c.result_class = 'interval_censored' and c.upper_bound < 1800 then 'definitely_below'
            else 'indeterminate_censored'
        end as ntprobnp_1800_state
    from ntprobnp_episode_candidates c
    where c.episode_match_count = 1
      and c.result_class in (
          'exact_numeric', 'right_censored', 'left_censored', 'interval_censored'
      )
),
ntprobnp_early as (
    select
        stay_id,
        count(*) as ntprobnp_n_measurements_early12,
        min(charttime) as ntprobnp_first_charttime_early12,
        min(availability_time) as ntprobnp_first_availability_time_early12,
        max(analysis_value) as ntprobnp_max_early12,
        min(analysis_value) as ntprobnp_min_early12,
        count(*) filter (where ntprobnp_300_state = 'definitely_above') as ntprobnp_definitely_above_300_n,
        count(*) filter (where ntprobnp_300_state = 'definitely_below') as ntprobnp_definitely_below_300_n,
        count(*) filter (where ntprobnp_300_state = 'indeterminate_censored') as ntprobnp_indeterminate_censored_300_n,
        count(*) filter (where ntprobnp_900_state = 'definitely_above') as ntprobnp_definitely_above_900_n,
        count(*) filter (where ntprobnp_1800_state = 'definitely_above') as ntprobnp_definitely_above_1800_n
    from ntprobnp_classified
    group by stay_id
),
ntprobnp_episode_audit as (
    select
        stay_id,
        count(*) filter (where episode_match_count > 1) as ambiguous_episode_match_n
    from ntprobnp_episode_candidates
    group by stay_id
),
iv_loop_rx_early as (
    select
        b.stay_id,
        count(*) as iv_loop_rx_n_orders_early12,
        min(p.starttime) as iv_loop_rx_first_starttime_early12
    from base b
    join mimiciv_hosp.prescriptions p
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
      and p.starttime < b.intime + interval '12 hour'
      and coalesce(p.stoptime, p.starttime) >= b.intime - interval '24 hour'
    group by b.stay_id
),
loop_emar_early as (
    select
        b.stay_id,
        count(*) as loop_emar_n_records_early12,
        min(e.charttime) as loop_emar_first_charttime_early12,
        count(*) filter (
            where upper(coalesce(ed.route, '')) in ('PO', 'NG', 'ORAL', 'G TUBE', 'GT', 'PEG')
        ) as loop_emar_oral_or_enteral_n_early12,
        count(*) filter (
            where lower(coalesce(ed.product_description, '')) like any (
                array['%vial%', '%syringe%', '%inject%', '%infusion%', '%iv%', '%conc:%']
            )
               or lower(coalesce(e.medication, '')) like '%in 0.9% sodium chloride%'
        ) as loop_emar_possible_iv_formulation_n_early12
    from base b
    join mimiciv_hosp.emar e
      on b.subject_id = e.subject_id
     and b.hadm_id = e.hadm_id
    left join mimiciv_hosp.emar_detail ed
      on e.emar_id = ed.emar_id
     and e.emar_seq = ed.emar_seq
    where (
            lower(coalesce(e.medication, '')) like any (
                array['%furosemide%', '%bumetanide%', '%torsemide%', '%ethacrynic%']
            )
         or lower(coalesce(ed.product_description, '')) like any (
                array['%furosemide%', '%bumetanide%', '%torsemide%', '%ethacrynic%']
            )
    )
      and e.charttime >= b.intime - interval '24 hour'
      and e.charttime < b.intime + interval '12 hour'
      and lower(coalesce(e.event_txt, '')) not like '%not given%'
      and lower(coalesce(e.event_txt, '')) not like '%hold%'
      and lower(coalesce(ed.complete_dose_not_given, '')) not in ('yes', 'y', 'true', '1')
    group by b.stay_id
)
select
    b.*,
    case when b.hf_icd_primary_seq <= 5 then 1 else 0 end as hf_icd_seq_le5,
    case when b.hf_icd_primary_seq = 1 then 1 else 0 end as hf_icd_seq_eq1,
    coalesce(n.ntprobnp_n_measurements_early12, 0) as ntprobnp_n_measurements_early12,
    n.ntprobnp_first_charttime_early12,
    n.ntprobnp_first_availability_time_early12,
    n.ntprobnp_max_early12,
    n.ntprobnp_min_early12,
    case when coalesce(n.ntprobnp_n_measurements_early12, 0) > 0 then 1 else 0 end as ntprobnp_measured_early12_flag,
    case when coalesce(n.ntprobnp_definitely_above_300_n, 0) > 0 then 1 else 0 end as ntprobnp_ge300_early12_flag,
    case
        when coalesce(n.ntprobnp_definitely_above_300_n, 0) > 0 then 'definitely_above'
        when coalesce(n.ntprobnp_indeterminate_censored_300_n, 0) > 0 then 'indeterminate_censored'
        when coalesce(n.ntprobnp_n_measurements_early12, 0) > 0
         and n.ntprobnp_definitely_below_300_n = n.ntprobnp_n_measurements_early12 then 'definitely_below'
        else 'not_measured'
    end as ntprobnp_300_patient_state,
    case when coalesce(n.ntprobnp_definitely_above_900_n, 0) > 0 then 1 else 0 end as ntprobnp_ge900_early12_flag,
    case when coalesce(n.ntprobnp_definitely_above_1800_n, 0) > 0 then 1 else 0 end as ntprobnp_ge1800_early12_flag,
    coalesce(a.ambiguous_episode_match_n, 0) as ntprobnp_ambiguous_episode_match_n,
    case when coalesce(a.ambiguous_episode_match_n, 0) > 0 then 1 else 0 end as ambiguous_episode_match,
    coalesce(rx.iv_loop_rx_n_orders_early12, 0) as iv_loop_rx_n_orders_early12,
    rx.iv_loop_rx_first_starttime_early12,
    case when coalesce(rx.iv_loop_rx_n_orders_early12, 0) > 0 then 1 else 0 end as iv_loop_rx_early12_flag,
    coalesce(em.loop_emar_n_records_early12, 0) as loop_emar_n_records_early12,
    em.loop_emar_first_charttime_early12,
    coalesce(em.loop_emar_oral_or_enteral_n_early12, 0) as loop_emar_oral_or_enteral_n_early12,
    coalesce(em.loop_emar_possible_iv_formulation_n_early12, 0) as loop_emar_possible_iv_formulation_n_early12,
    case when coalesce(em.loop_emar_n_records_early12, 0) > 0 then 1 else 0 end as loop_emar_any_early12_flag,
    case when coalesce(em.loop_emar_possible_iv_formulation_n_early12, 0) > 0 then 1 else 0 end as iv_loop_emar_formulation_early12_flag,
    (
        case when b.hf_icd_acute_or_acute_on_chronic = 1 then 1 else 0 end
      + case when b.hf_icd_primary_seq <= 5 then 1 else 0 end
      + case when coalesce(rx.iv_loop_rx_n_orders_early12, 0) > 0 then 1 else 0 end
      + case when coalesce(n.ntprobnp_definitely_above_300_n, 0) > 0 then 1 else 0 end
    ) as ahf_evidence_score_primary_12h,
    case when b.hf_icd_any = 1 then 1 else 0 end as ahf_retro_confirmed_flag,
    case when (
        coalesce(em.loop_emar_n_records_early12, 0) > 0
     or coalesce(rx.iv_loop_rx_n_orders_early12, 0) > 0
     or coalesce(n.ntprobnp_n_measurements_early12, 0) > 0
    ) then 1 else 0 end as ahf_time_confirmed_by_t12_flag,
    case when (
        (em.loop_emar_first_charttime_early12 is not null and em.loop_emar_first_charttime_early12 < b.intime)
     or (rx.iv_loop_rx_first_starttime_early12 is not null and rx.iv_loop_rx_first_starttime_early12 < b.intime)
     or (n.ntprobnp_first_availability_time_early12 is not null and n.ntprobnp_first_availability_time_early12 < b.intime)
    ) then 1 else 0 end as ahf_pre_icu_confirmed_flag
from base b
left join ntprobnp_early n on b.stay_id = n.stay_id
left join ntprobnp_episode_audit a on b.stay_id = a.stay_id
left join iv_loop_rx_early rx on b.stay_id = rx.stay_id
left join loop_emar_early em on b.stay_id = em.stay_id;

-- Promotion QC: any ambiguous match is a hard failure for this path.
select
    count(*) as n_total,
    sum(ambiguous_episode_match) as ambiguous_episode_match_n,
    sum(ntprobnp_ge300_early12_flag) as ntprobnp_definitely_above_300_n,
    count(*) filter (where ntprobnp_300_patient_state = 'indeterminate_censored') as ntprobnp_indeterminate_censored_n
from study_ahf_v3_3.cohort_061A_ahf_evidence_early_window_12h_v2;
