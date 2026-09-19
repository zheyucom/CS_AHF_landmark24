-- Revised candidate hemodynamic-deterioration path.
-- Lactate rollups use exact analysis_value; censored results only support
-- one-sided "definitely above" threshold statements.

drop table if exists study_ahf_v3_3.outcome_063A_candidate_hd_outcomes_overall_v2 cascade;

create table study_ahf_v3_3.outcome_063A_candidate_hd_outcomes_overall_v2 as
with base as (
    select
        e.*,
        s.sepsis3_any_icu_flag,
        s.early_sepsis12_main_flag,
        s.early_sepsis12_suspected_infection_only_flag,
        s.early_sepsis12_broad_flag,
        s.early_sepsis12_first_suspected_infection_time,
        s.early_sepsis12_first_sofa_time,
        s.early_sepsis12_max_sofa_score
    from study_ahf_v3_3.outcome_061E_post12_overt_cs_future48h_main_v2 e
    left join study_ahf_v3_2.outcome_062A_post12_outcome_with_earlysepsis12_v1 s
      on e.stay_id = s.stay_id
),
lactate_episode_candidates as (
    select
        b.stay_id,
        le.labevent_id,
        le.charttime,
        le.availability_time,
        le.result_class,
        le.lower_bound,
        le.upper_bound,
        le.analysis_value,
        case when le.charttime < b.landmark12_time then 'pre12' else 'post12' end as lab_window,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base b
    join study_ahf_v3_3.lab_eligible_v1 le
      on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.concept = 'lactate'
     and le.charttime >= b.intime
     and le.charttime < b.observed_until_time
     and le.availability_time >= b.intime
     and le.availability_time < b.observed_until_time
),
lactate_valid as (
    select
        c.*,
        case
            when c.analysis_value >= 2 then 1
            when c.result_class in ('right_censored', 'interval_censored') and c.lower_bound >= 2 then 1
            else 0
        end as definitely_ge2,
        case
            when c.analysis_value >= 4 then 1
            when c.result_class in ('right_censored', 'interval_censored') and c.lower_bound >= 4 then 1
            else 0
        end as definitely_ge4
    from lactate_episode_candidates c
    where c.episode_match_count = 1
      and c.result_class in (
          'exact_numeric', 'right_censored', 'left_censored', 'interval_censored'
      )
),
pre_lactate_summary as (
    select
        stay_id,
        count(*) as pre12_lactate_n,
        count(analysis_value) as pre12_lactate_exact_n,
        max(analysis_value) as pre12_lactate_max,
        min(analysis_value) as pre12_lactate_min
    from lactate_valid
    where lab_window = 'pre12'
    group by stay_id
),
pre_lactate_last as (
    select stay_id, charttime as pre12_lactate_last_time, analysis_value as pre12_lactate_last
    from (
        select
            stay_id,
            charttime,
            analysis_value,
            row_number() over (partition by stay_id order by charttime desc, labevent_id desc) as rn
        from lactate_valid
        where lab_window = 'pre12' and analysis_value is not null
    ) ranked
    where rn = 1
),
post_lactate_summary as (
    select
        stay_id,
        count(*) as post12_lactate_n,
        count(analysis_value) as post12_lactate_exact_n,
        max(analysis_value) as post12_lactate_max,
        min(charttime) filter (where definitely_ge2 = 1) as post12_lactate_ge2_first_time,
        min(charttime) filter (where definitely_ge4 = 1) as post12_lactate_ge4_first_time,
        sum(definitely_ge2) as post12_lactate_ge2_n,
        sum(definitely_ge4) as post12_lactate_ge4_n
    from lactate_valid
    where lab_window = 'post12'
    group by stay_id
),
lactate_episode_audit as (
    select
        stay_id,
        count(*) filter (where episode_match_count > 1) as ambiguous_episode_match_n
    from lactate_episode_candidates
    group by stay_id
),
pre_agent as (
    select
        b.stay_id,
        max((coalesce(va.norepinephrine, 0) > 0)::integer) as norepinephrine_flag,
        max((coalesce(va.epinephrine, 0) > 0)::integer) as epinephrine_flag,
        max((coalesce(va.dopamine, 0) > 0)::integer) as dopamine_flag,
        max((coalesce(va.phenylephrine, 0) > 0)::integer) as phenylephrine_flag,
        max((coalesce(va.vasopressin, 0) > 0)::integer) as vasopressin_flag,
        max((coalesce(va.dobutamine, 0) > 0)::integer) as dobutamine_flag,
        max((coalesce(va.milrinone, 0) > 0)::integer) as milrinone_flag,
        count(*) as vaso_records_n,
        min(va.starttime) as first_starttime
    from base b
    join mimiciv_derived.vasoactive_agent va
      on b.stay_id = va.stay_id
     and va.starttime < b.landmark12_time
     and coalesce(va.endtime, va.starttime + interval '1 minute') > b.intime
    group by b.stay_id
),
post_agent as (
    select
        b.stay_id,
        max((coalesce(va.norepinephrine, 0) > 0)::integer) as norepinephrine_flag,
        max((coalesce(va.epinephrine, 0) > 0)::integer) as epinephrine_flag,
        max((coalesce(va.dopamine, 0) > 0)::integer) as dopamine_flag,
        max((coalesce(va.phenylephrine, 0) > 0)::integer) as phenylephrine_flag,
        max((coalesce(va.vasopressin, 0) > 0)::integer) as vasopressin_flag,
        max((coalesce(va.dobutamine, 0) > 0)::integer) as dobutamine_flag,
        max((coalesce(va.milrinone, 0) > 0)::integer) as milrinone_flag,
        count(*) as vaso_records_n,
        min(va.starttime) as first_starttime
    from base b
    join mimiciv_derived.vasoactive_agent va
      on b.stay_id = va.stay_id
     and va.starttime < b.observed_until_time
     and coalesce(va.endtime, va.starttime + interval '1 minute') > b.landmark12_time
    group by b.stay_id
),
agent_flags as (
    select
        b.stay_id,
        coalesce(pre.norepinephrine_flag, 0) + coalesce(pre.epinephrine_flag, 0)
          + coalesce(pre.dopamine_flag, 0) + coalesce(pre.phenylephrine_flag, 0)
          + coalesce(pre.vasopressin_flag, 0) + coalesce(pre.dobutamine_flag, 0)
          + coalesce(pre.milrinone_flag, 0) as pre12_agent_count,
        coalesce(post.norepinephrine_flag, 0) + coalesce(post.epinephrine_flag, 0)
          + coalesce(post.dopamine_flag, 0) + coalesce(post.phenylephrine_flag, 0)
          + coalesce(post.vasopressin_flag, 0) + coalesce(post.dobutamine_flag, 0)
          + coalesce(post.milrinone_flag, 0) as post12_agent_count,
        (case when coalesce(pre.norepinephrine_flag, 0) = 0 and coalesce(post.norepinephrine_flag, 0) = 1 then 1 else 0 end)
          + (case when coalesce(pre.epinephrine_flag, 0) = 0 and coalesce(post.epinephrine_flag, 0) = 1 then 1 else 0 end)
          + (case when coalesce(pre.dopamine_flag, 0) = 0 and coalesce(post.dopamine_flag, 0) = 1 then 1 else 0 end)
          + (case when coalesce(pre.phenylephrine_flag, 0) = 0 and coalesce(post.phenylephrine_flag, 0) = 1 then 1 else 0 end)
          + (case when coalesce(pre.vasopressin_flag, 0) = 0 and coalesce(post.vasopressin_flag, 0) = 1 then 1 else 0 end)
          + (case when coalesce(pre.dobutamine_flag, 0) = 0 and coalesce(post.dobutamine_flag, 0) = 1 then 1 else 0 end)
          + (case when coalesce(pre.milrinone_flag, 0) = 0 and coalesce(post.milrinone_flag, 0) = 1 then 1 else 0 end) as post12_new_agent_count,
        coalesce(pre.vaso_records_n, 0) as pre12_vaso_records_n,
        coalesce(post.vaso_records_n, 0) as post12_vaso_records_n,
        post.first_starttime as post12_vaso_first_starttime
    from base b
    left join pre_agent pre on b.stay_id = pre.stay_id
    left join post_agent post on b.stay_id = post.stay_id
),
final_flags as (
    select
        b.*,
        coalesce(pls.pre12_lactate_n, 0) as pre12_lactate_contract_n,
        coalesce(pls.pre12_lactate_exact_n, 0) as pre12_lactate_contract_exact_n,
        pls.pre12_lactate_max as pre12_lactate_contract_max,
        pls.pre12_lactate_min as pre12_lactate_contract_min,
        pll.pre12_lactate_last_time as pre12_lactate_contract_last_time,
        pll.pre12_lactate_last as pre12_lactate_contract_last,
        coalesce(pol.post12_lactate_n, 0) as post12_lactate_contract_n,
        coalesce(pol.post12_lactate_exact_n, 0) as post12_lactate_contract_exact_n,
        pol.post12_lactate_max as post12_lactate_contract_max,
        pol.post12_lactate_ge2_first_time as post12_lactate_contract_ge2_first_time,
        pol.post12_lactate_ge4_first_time as post12_lactate_contract_ge4_first_time,
        coalesce(pol.post12_lactate_ge2_n, 0) as post12_lactate_contract_ge2_n,
        coalesce(pol.post12_lactate_ge4_n, 0) as post12_lactate_contract_ge4_n,
        coalesce(aud.ambiguous_episode_match_n, 0) as lactate_contract_ambiguous_episode_match_n,
        case when coalesce(aud.ambiguous_episode_match_n, 0) > 0 then 1 else 0 end as lactate_contract_ambiguous_episode_match,
        a.pre12_agent_count,
        a.post12_agent_count,
        a.post12_new_agent_count,
        a.pre12_vaso_records_n as overlap_pre12_vaso_records_n,
        a.post12_vaso_records_n as overlap_post12_vaso_records_n,
        a.post12_vaso_first_starttime as overlap_post12_vaso_first_starttime,
        case when a.pre12_agent_count = 0 and a.post12_agent_count > 0 then 1 else 0 end as new_support_initiation_flag,
        case when a.post12_agent_count > a.pre12_agent_count then 1 else 0 end as agent_count_increase_flag,
        case when (a.pre12_agent_count = 0 and a.post12_agent_count > 0)
                    or a.post12_agent_count > a.pre12_agent_count then 1 else 0 end as hd_support_initiation_or_count_increase_flag,
        case when pls.pre12_lactate_max is not null and pls.pre12_lactate_max < 2
                   and pol.post12_lactate_max >= 2 then 1 else 0 end as lactate_new_ge2_flag,
        case when pls.pre12_lactate_max >= 2 and pls.pre12_lactate_max < 4
                   and pol.post12_lactate_max >= 4 then 1 else 0 end as lactate_2to4_worsen_ge4_flag,
        case when pll.pre12_lactate_last is not null and pol.post12_lactate_max is not null
                   and pol.post12_lactate_max - pll.pre12_lactate_last >= 2 then 1 else 0 end as lactate_delta_ge2_from_last_flag
    from base b
    left join pre_lactate_summary pls on b.stay_id = pls.stay_id
    left join pre_lactate_last pll on b.stay_id = pll.stay_id
    left join post_lactate_summary pol on b.stay_id = pol.stay_id
    left join lactate_episode_audit aud on b.stay_id = aud.stay_id
    left join agent_flags a on b.stay_id = a.stay_id
)
select
    f.*,
    case when lactate_new_ge2_flag = 1 or lactate_2to4_worsen_ge4_flag = 1
                   or lactate_delta_ge2_from_last_flag = 1 then 1 else 0 end as lactate_worsening_any_flag,
    case when hd_support_initiation_or_count_increase_flag = 1 or death_12_60_flag = 1 then 1 else 0 end as hd_deterioration_broad_flag,
    case when (hd_support_initiation_or_count_increase_flag = 1 and (
                        lactate_new_ge2_flag = 1
                     or lactate_2to4_worsen_ge4_flag = 1
                     or lactate_delta_ge2_from_last_flag = 1
                   )) or death_12_60_flag = 1 then 1 else 0 end as hd_deterioration_lac_confirmed_flag
from final_flags f;

select
    count(*) as n_total,
    sum(lactate_contract_ambiguous_episode_match) as ambiguous_episode_match_n,
    sum(hd_deterioration_lac_confirmed_flag) as hd_deterioration_lac_confirmed_n
from study_ahf_v3_3.outcome_063A_candidate_hd_outcomes_overall_v2;
