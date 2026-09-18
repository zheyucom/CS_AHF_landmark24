-- ============================================================
-- Project: CS_AHF_landmark12
-- File: sql/02_outcome/063C_create_hd_outcomes_with_nee.sql
-- Purpose:
--   Add norepinephrine-equivalent dose escalation to candidate
--   hemodynamic deterioration outcomes.
--
-- Input:
--   study_ahf_v4.outcome_063A_candidate_hd_outcomes_overall_v1
--
-- Main idea:
--   pre12 NEE is calculated using infusion intervals overlapping
--   ICU intime to ICU intime +12h.
--
--   post12 NEE is calculated using infusion intervals overlapping
--   ICU intime +12h to observed_until_time.
--
-- Leakage control:
--   pre12 NEE uses only data before / overlapping landmark.
--   post12 NEE is used only as outcome definition, never as predictor.
-- ============================================================

drop table if exists study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1 cascade;

create table study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1 as
with base as (
    select
        *,
        intime + interval '12 hour' as landmark12_time_for_063c
    from study_ahf_v4.outcome_063A_candidate_hd_outcomes_overall_v1
),

pre12_nee as (
    select
        b.stay_id,

        count(ne.starttime) as pre12_nee_records_n,
        max(ne.norepinephrine_equivalent_dose) as pre12_nee_max,
        min(ne.norepinephrine_equivalent_dose) as pre12_nee_min,

        max(ne.endtime) as pre12_nee_last_endtime

    from base b
    left join mimiciv_derived.norepinephrine_equivalent_dose ne
        on b.stay_id = ne.stay_id
       and ne.starttime <  b.landmark12_time_for_063c
       and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.intime
    group by b.stay_id
),

pre12_nee_last as (
    select
        stay_id,
        norepinephrine_equivalent_dose as pre12_nee_last,
        starttime as pre12_nee_last_starttime,
        endtime as pre12_nee_last_endtime
    from (
        select
            b.stay_id,
            ne.starttime,
            ne.endtime,
            ne.norepinephrine_equivalent_dose,
            row_number() over (
                partition by b.stay_id
                order by coalesce(ne.endtime, ne.starttime) desc, ne.starttime desc
            ) as rn
        from base b
        inner join mimiciv_derived.norepinephrine_equivalent_dose ne
            on b.stay_id = ne.stay_id
           and ne.starttime <  b.landmark12_time_for_063c
           and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.intime
    ) x
    where rn = 1
),

post12_nee as (
    select
        b.stay_id,

        count(ne.starttime) as post12_nee_records_n,
        max(ne.norepinephrine_equivalent_dose) as post12_nee_max,
        min(ne.norepinephrine_equivalent_dose) as post12_nee_min,
        min(ne.starttime) as post12_nee_first_starttime

    from base b
    left join mimiciv_derived.norepinephrine_equivalent_dose ne
        on b.stay_id = ne.stay_id
       and ne.starttime <  b.observed_until_time
       and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.landmark12_time_for_063c
    group by b.stay_id
)

select
    b.*,

    coalesce(pre.pre12_nee_records_n, 0) as pre12_nee_records_n,
    pre.pre12_nee_max,
    pre.pre12_nee_min,
    last.pre12_nee_last,
    last.pre12_nee_last_starttime,
    last.pre12_nee_last_endtime,

    coalesce(post.post12_nee_records_n, 0) as post12_nee_records_n,
    post.post12_nee_max,
    post.post12_nee_min,
    post.post12_nee_first_starttime,

    case
        when coalesce(pre.pre12_nee_records_n, 0) = 0
         and coalesce(post.post12_nee_records_n, 0) > 0
        then 1 else 0
    end as nee_new_start_flag,

    case
        when pre.pre12_nee_max is not null
         and post.post12_nee_max is not null
         and post.post12_nee_max - pre.pre12_nee_max >= 0.05
        then 1 else 0
    end as nee_delta_from_premax_ge005_flag,

    case
        when pre.pre12_nee_max is not null
         and post.post12_nee_max is not null
         and post.post12_nee_max - pre.pre12_nee_max >= 0.10
        then 1 else 0
    end as nee_delta_from_premax_ge010_flag,

    case
        when last.pre12_nee_last is not null
         and post.post12_nee_max is not null
         and post.post12_nee_max - last.pre12_nee_last >= 0.05
        then 1 else 0
    end as nee_delta_from_prelast_ge005_flag,

    case
        when last.pre12_nee_last is not null
         and post.post12_nee_max is not null
         and post.post12_nee_max - last.pre12_nee_last >= 0.10
        then 1 else 0
    end as nee_delta_from_prelast_ge010_flag,

    case
        when pre.pre12_nee_max is not null
         and pre.pre12_nee_max >= 0.02
         and post.post12_nee_max is not null
         and post.post12_nee_max >= pre.pre12_nee_max * 1.5
        then 1 else 0
    end as nee_relative_increase_50pct_flag,

    -- Conservative NEE escalation:
    -- post12 max exceeds pre12 max by >=0.05.
    case
        when pre.pre12_nee_max is not null
         and post.post12_nee_max is not null
         and post.post12_nee_max - pre.pre12_nee_max >= 0.05
        then 1 else 0
    end as nee_escalation_conservative_flag,

    -- Sensitive NEE escalation:
    -- post12 max exceeds pre12 last by >=0.05, or relative increase >=50%.
    case
        when (
                last.pre12_nee_last is not null
            and post.post12_nee_max is not null
            and post.post12_nee_max - last.pre12_nee_last >= 0.05
             )
          or (
                pre.pre12_nee_max is not null
            and pre.pre12_nee_max >= 0.02
            and post.post12_nee_max is not null
            and post.post12_nee_max >= pre.pre12_nee_max * 1.5
             )
        then 1 else 0
    end as nee_escalation_sensitive_flag,

    -- New composite including conservative NEE escalation.
    case
        when hd_support_initiation_or_count_increase_flag = 1
          or (
                pre.pre12_nee_max is not null
            and post.post12_nee_max is not null
            and post.post12_nee_max - pre.pre12_nee_max >= 0.05
             )
          or death_12_60_flag = 1
        then 1 else 0
    end as hd_deterioration_broad_nee005_flag,

    case
        when hd_support_initiation_or_count_increase_flag = 1
          or (
                pre.pre12_nee_max is not null
            and post.post12_nee_max is not null
            and post.post12_nee_max - pre.pre12_nee_max >= 0.10
             )
          or death_12_60_flag = 1
        then 1 else 0
    end as hd_deterioration_broad_nee010_flag,

    -- Lactate-confirmed version including NEE escalation.
    case
        when (
                (
                    hd_support_initiation_or_count_increase_flag = 1
                 or (
                        pre.pre12_nee_max is not null
                    and post.post12_nee_max is not null
                    and post.post12_nee_max - pre.pre12_nee_max >= 0.05
                    )
                )
            and lactate_worsening_any_flag = 1
             )
          or death_12_60_flag = 1
        then 1 else 0
    end as hd_deterioration_lac_confirmed_nee005_flag

from base b
left join pre12_nee pre
    on b.stay_id = pre.stay_id
left join pre12_nee_last last
    on b.stay_id = last.stay_id
left join post12_nee post
    on b.stay_id = post.stay_id;
		
		
		
		
		
-- 		063C QC1：NEE 升级事件率
with cohorted as (
    select
        '01_overall_ahf12' as cohort,
        *
    from study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1

    union all

    select
        '02_early_sepsis12_main' as cohort,
        *
    from study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1
    where early_sepsis12_main_flag = 1

    union all

    select
        '03_no_early_sepsis12_main' as cohort,
        *
    from study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1
    where early_sepsis12_main_flag = 0
),

long_outcomes as (
    select
        cohort,
        outcome,
        event_flag
    from cohorted c
    cross join lateral (
        values
            ('01_hd_broad_original', hd_deterioration_broad_flag),
            ('02_nee_new_start', nee_new_start_flag),
            ('03_nee_delta_premax_ge005', nee_delta_from_premax_ge005_flag),
            ('04_nee_delta_premax_ge010', nee_delta_from_premax_ge010_flag),
            ('05_nee_delta_prelast_ge005', nee_delta_from_prelast_ge005_flag),
            ('06_nee_delta_prelast_ge010', nee_delta_from_prelast_ge010_flag),
            ('07_nee_relative_increase_50pct', nee_relative_increase_50pct_flag),
            ('08_nee_escalation_conservative', nee_escalation_conservative_flag),
            ('09_nee_escalation_sensitive', nee_escalation_sensitive_flag),
            ('10_hd_broad_nee005', hd_deterioration_broad_nee005_flag),
            ('11_hd_broad_nee010', hd_deterioration_broad_nee010_flag),
            ('12_hd_lac_confirmed_nee005', hd_deterioration_lac_confirmed_nee005_flag)
    ) as v(outcome, event_flag)
)

select
    cohort,
    outcome,
    count(*) as n_total,
    sum(event_flag) as n_events,
    round(sum(event_flag) * 100.0 / count(*), 2) as event_rate
from long_outcomes
group by
    cohort,
    outcome
order by
    cohort,
    outcome;
		
		
		
		
		select
    count(*) as n_total,

    sum(case when pre12_nee_records_n > 0 then 1 else 0 end) as n_pre12_nee,
    round(sum(case when pre12_nee_records_n > 0 then 1 else 0 end) * 100.0 / count(*), 2) as pct_pre12_nee,

    sum(case when post12_nee_records_n > 0 then 1 else 0 end) as n_post12_nee,
    round(sum(case when post12_nee_records_n > 0 then 1 else 0 end) * 100.0 / count(*), 2) as pct_post12_nee,

    percentile_cont(0.25) within group (order by pre12_nee_max) as pre12_nee_max_p25,
    percentile_cont(0.50) within group (order by pre12_nee_max) as pre12_nee_max_p50,
    percentile_cont(0.75) within group (order by pre12_nee_max) as pre12_nee_max_p75,

    percentile_cont(0.25) within group (order by post12_nee_max) as post12_nee_max_p25,
    percentile_cont(0.50) within group (order by post12_nee_max) as post12_nee_max_p50,
    percentile_cont(0.75) within group (order by post12_nee_max) as post12_nee_max_p75

from study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1;




select
    early_sepsis12_main_flag,
    hd_support_initiation_or_count_increase_flag,
    nee_escalation_conservative_flag,
    death_12_60_flag,
    hd_deterioration_broad_flag,
    hd_deterioration_broad_nee005_flag,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (partition by early_sepsis12_main_flag), 2) as pct_within_sepsis_stratum
from study_ahf_v4.outcome_063C_candidate_hd_outcomes_with_nee_v1
group by
    early_sepsis12_main_flag,
    hd_support_initiation_or_count_increase_flag,
    nee_escalation_conservative_flag,
    death_12_60_flag,
    hd_deterioration_broad_flag,
    hd_deterioration_broad_nee005_flag
order by
    early_sepsis12_main_flag,
    n desc;
		
		
		
		
		