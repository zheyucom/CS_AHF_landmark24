-- ============================================================
-- Project: CS_AHF_landmark12
-- File: sql/02_outcome/063A_create_candidate_hd_outcomes_overall.sql
-- Purpose:
--   Create candidate hemodynamic deterioration outcomes among
--   the overall AHF 12h-landmark risk set, with sepsis strata.
--
-- Input:
--   study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1
--
-- Population:
--   AHF strict 12h
--   + reached 12h landmark
--   + no pre12 overt CS
--
-- Time windows:
--   Predictor / baseline window: ICU intime to ICU intime +12h
--   Outcome window: ICU intime +12h to ICU intime +60h
--
-- Key principle:
--   Lactate >=2 alone is NOT an event.
--   Lactate is used only as worsening / hypoperfusion confirmation.
--   Mechanical ventilation and RRT are NOT included in the main composite.
-- ============================================================

drop table if exists study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1 cascade;

create table study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1 as
with base as (
    select
        *,
        intime + interval '12 hour' as landmark12_time_for_063,
        intime + interval '60 hour' as window60_time_for_063
    from study_ahf_v3.outcome_062A_post12_outcome_with_earlysepsis12_v1
),

-- ------------------------------------------------------------
-- Pre-12h lactate.
-- pre12_lactate_max is used to determine whether lactate was
-- already elevated before landmark.
-- pre12_lactate_last is used to assess delta from the value
-- closest to the landmark.
-- ------------------------------------------------------------
pre_lactate_all as (
    select
        b.stay_id,
        bg.charttime,
        bg.lactate
    from base b
    inner join mimiciv_derived.bg bg
        on b.subject_id = bg.subject_id
       and b.hadm_id = bg.hadm_id
    where bg.charttime >= b.intime
      and bg.charttime <  b.landmark12_time_for_063
      and bg.lactate is not null
),

pre_lactate_summary as (
    select
        stay_id,
        count(*) as pre12_lactate_n,
        max(lactate) as pre12_lactate_max,
        min(lactate) as pre12_lactate_min
    from pre_lactate_all
    group by stay_id
),

pre_lactate_last as (
    select
        stay_id,
        charttime as pre12_lactate_last_time,
        lactate as pre12_lactate_last
    from (
        select
            stay_id,
            charttime,
            lactate,
            row_number() over (
                partition by stay_id
                order by charttime desc
            ) as rn
        from pre_lactate_all
    ) x
    where rn = 1
),

-- ------------------------------------------------------------
-- Post-12h lactate in observable 12-60h ICU window.
-- ------------------------------------------------------------
post_lactate_all as (
    select
        b.stay_id,
        bg.charttime,
        bg.lactate
    from base b
    inner join mimiciv_derived.bg bg
        on b.subject_id = bg.subject_id
       and b.hadm_id = bg.hadm_id
    where bg.charttime >= b.landmark12_time_for_063
      and bg.charttime <  b.observed_until_time
      and bg.lactate is not null
),

post_lactate_summary as (
    select
        stay_id,
        count(*) as post12_lactate_n,
        max(lactate) as post12_lactate_max,
        min(charttime) filter (where lactate >= 2) as post12_lactate_ge2_first_time,
        min(charttime) filter (where lactate >= 4) as post12_lactate_ge4_first_time,
        count(*) filter (where lactate >= 2) as post12_lactate_ge2_n,
        count(*) filter (where lactate >= 4) as post12_lactate_ge4_n
    from post_lactate_all
    group by stay_id
),

-- ------------------------------------------------------------
-- Pre-12h vasoactive/inotrope exposure.
-- Infusions overlapping 0-12h count as pre12 exposure.
-- ------------------------------------------------------------
pre_agent as (
    select
        b.stay_id,

        max(case when coalesce(va.norepinephrine, 0) > 0 then 1 else 0 end) as pre12_norepinephrine_flag,
        max(case when coalesce(va.epinephrine, 0) > 0 then 1 else 0 end) as pre12_epinephrine_flag,
        max(case when coalesce(va.dopamine, 0) > 0 then 1 else 0 end) as pre12_dopamine_flag,
        max(case when coalesce(va.phenylephrine, 0) > 0 then 1 else 0 end) as pre12_phenylephrine_flag,
        max(case when coalesce(va.vasopressin, 0) > 0 then 1 else 0 end) as pre12_vasopressin_flag,
        max(case when coalesce(va.dobutamine, 0) > 0 then 1 else 0 end) as pre12_dobutamine_flag,
        max(case when coalesce(va.milrinone, 0) > 0 then 1 else 0 end) as pre12_milrinone_flag,

        count(va.starttime) as pre12_vaso_records_n

    from base b
    left join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
       and va.starttime <  b.landmark12_time_for_063
       and coalesce(va.endtime, va.starttime + interval '1 minute') > b.intime
    group by b.stay_id
),

-- ------------------------------------------------------------
-- Post-12h vasoactive/inotrope exposure.
-- Infusions overlapping observable 12-60h window count.
-- ------------------------------------------------------------
post_agent as (
    select
        b.stay_id,

        max(case when coalesce(va.norepinephrine, 0) > 0 then 1 else 0 end) as post12_norepinephrine_flag,
        max(case when coalesce(va.epinephrine, 0) > 0 then 1 else 0 end) as post12_epinephrine_flag,
        max(case when coalesce(va.dopamine, 0) > 0 then 1 else 0 end) as post12_dopamine_flag,
        max(case when coalesce(va.phenylephrine, 0) > 0 then 1 else 0 end) as post12_phenylephrine_flag,
        max(case when coalesce(va.vasopressin, 0) > 0 then 1 else 0 end) as post12_vasopressin_flag,
        max(case when coalesce(va.dobutamine, 0) > 0 then 1 else 0 end) as post12_dobutamine_flag,
        max(case when coalesce(va.milrinone, 0) > 0 then 1 else 0 end) as post12_milrinone_flag,

        count(va.starttime) as post12_vaso_records_n,
        min(va.starttime) as post12_vaso_first_starttime

    from base b
    left join mimiciv_derived.vasoactive_agent va
        on b.stay_id = va.stay_id
       and va.starttime <  b.observed_until_time
       and coalesce(va.endtime, va.starttime + interval '1 minute') > b.landmark12_time_for_063
    group by b.stay_id
),

agent_flags as (
    select
        b.stay_id,

        coalesce(pre.pre12_norepinephrine_flag, 0) as pre12_norepinephrine_flag,
        coalesce(pre.pre12_epinephrine_flag, 0) as pre12_epinephrine_flag,
        coalesce(pre.pre12_dopamine_flag, 0) as pre12_dopamine_flag,
        coalesce(pre.pre12_phenylephrine_flag, 0) as pre12_phenylephrine_flag,
        coalesce(pre.pre12_vasopressin_flag, 0) as pre12_vasopressin_flag,
        coalesce(pre.pre12_dobutamine_flag, 0) as pre12_dobutamine_flag,
        coalesce(pre.pre12_milrinone_flag, 0) as pre12_milrinone_flag,

        coalesce(post.post12_norepinephrine_flag, 0) as post12_norepinephrine_flag,
        coalesce(post.post12_epinephrine_flag, 0) as post12_epinephrine_flag,
        coalesce(post.post12_dopamine_flag, 0) as post12_dopamine_flag,
        coalesce(post.post12_phenylephrine_flag, 0) as post12_phenylephrine_flag,
        coalesce(post.post12_vasopressin_flag, 0) as post12_vasopressin_flag,
        coalesce(post.post12_dobutamine_flag, 0) as post12_dobutamine_flag,
        coalesce(post.post12_milrinone_flag, 0) as post12_milrinone_flag,

        coalesce(pre.pre12_vaso_records_n, 0) as pre12_vaso_records_n,
        coalesce(post.post12_vaso_records_n, 0) as post12_vaso_records_n,
        post.post12_vaso_first_starttime,

        (
            coalesce(pre.pre12_norepinephrine_flag, 0)
          + coalesce(pre.pre12_epinephrine_flag, 0)
          + coalesce(pre.pre12_dopamine_flag, 0)
          + coalesce(pre.pre12_phenylephrine_flag, 0)
          + coalesce(pre.pre12_vasopressin_flag, 0)
          + coalesce(pre.pre12_dobutamine_flag, 0)
          + coalesce(pre.pre12_milrinone_flag, 0)
        ) as pre12_agent_count,

        (
            coalesce(post.post12_norepinephrine_flag, 0)
          + coalesce(post.post12_epinephrine_flag, 0)
          + coalesce(post.post12_dopamine_flag, 0)
          + coalesce(post.post12_phenylephrine_flag, 0)
          + coalesce(post.post12_vasopressin_flag, 0)
          + coalesce(post.post12_dobutamine_flag, 0)
          + coalesce(post.post12_milrinone_flag, 0)
        ) as post12_agent_count,

        (
            case when coalesce(pre.pre12_norepinephrine_flag, 0) = 0 and coalesce(post.post12_norepinephrine_flag, 0) = 1 then 1 else 0 end
          + case when coalesce(pre.pre12_epinephrine_flag, 0) = 0 and coalesce(post.post12_epinephrine_flag, 0) = 1 then 1 else 0 end
          + case when coalesce(pre.pre12_dopamine_flag, 0) = 0 and coalesce(post.post12_dopamine_flag, 0) = 1 then 1 else 0 end
          + case when coalesce(pre.pre12_phenylephrine_flag, 0) = 0 and coalesce(post.post12_phenylephrine_flag, 0) = 1 then 1 else 0 end
          + case when coalesce(pre.pre12_vasopressin_flag, 0) = 0 and coalesce(post.post12_vasopressin_flag, 0) = 1 then 1 else 0 end
          + case when coalesce(pre.pre12_dobutamine_flag, 0) = 0 and coalesce(post.post12_dobutamine_flag, 0) = 1 then 1 else 0 end
          + case when coalesce(pre.pre12_milrinone_flag, 0) = 0 and coalesce(post.post12_milrinone_flag, 0) = 1 then 1 else 0 end
        ) as post12_new_agent_count

    from base b
    left join pre_agent pre
        on b.stay_id = pre.stay_id
    left join post_agent post
        on b.stay_id = post.stay_id
),

final_flags as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        b.intime,
        b.outtime,
        b.observed_until_time,
        b.followup_hours_12_60,
        b.complete60_icu_flag,
        b.death_12_60_flag,

        -- sepsis strata
        b.sepsis3_any_icu_flag,
        b.early_sepsis12_main_flag,
        b.early_sepsis12_suspected_infection_only_flag,
        b.early_sepsis12_broad_flag,

        b.early_sepsis12_first_suspected_infection_time,
        b.early_sepsis12_first_sofa_time,
        b.early_sepsis12_max_sofa_score,

        -- existing strict shock proxies
        b.post12_overt_cs_main_flag as current_mixed_shock_proxy_flag,
        b.post12_overt_cs_lac4_flag as current_mixed_shock_lac4_proxy_flag,

        coalesce(pls.pre12_lactate_n, 0) as pre12_lactate_n,
        pls.pre12_lactate_max,
        pls.pre12_lactate_min,
        pll.pre12_lactate_last_time,
        pll.pre12_lactate_last,

        coalesce(pol.post12_lactate_n, 0) as post12_lactate_n,
        pol.post12_lactate_max,
        pol.post12_lactate_ge2_first_time,
        pol.post12_lactate_ge4_first_time,
        coalesce(pol.post12_lactate_ge2_n, 0) as post12_lactate_ge2_n,
        coalesce(pol.post12_lactate_ge4_n, 0) as post12_lactate_ge4_n,

        a.pre12_agent_count,
        a.post12_agent_count,
        a.post12_new_agent_count,
        a.pre12_vaso_records_n,
        a.post12_vaso_records_n,
        a.post12_vaso_first_starttime,

        -- ----------------------------------------------------
        -- Hemodynamic support change flags
        -- ----------------------------------------------------
        case
            when a.pre12_agent_count = 0
             and a.post12_agent_count > 0
            then 1 else 0
        end as new_support_initiation_flag,

        -- Any new agent appearing after 12h that was not present before.
        -- This may include true addition or medication switch, so it should
        -- be interpreted with agent_count_increase.
        case
            when a.pre12_agent_count > 0
             and a.post12_new_agent_count > 0
            then 1 else 0
        end as new_agent_after_preuse_flag,

        -- Cleaner escalation proxy: number of agent classes increases.
        case
            when a.post12_agent_count > a.pre12_agent_count
            then 1 else 0
        end as agent_count_increase_flag,

        -- Main support-escalation candidate:
        -- new support initiation OR increased number of agents.
        -- This avoids counting pure drug switching as escalation.
        case
            when (
                    a.pre12_agent_count = 0
                and a.post12_agent_count > 0
                 )
              or (
                    a.post12_agent_count > a.pre12_agent_count
                 )
            then 1 else 0
        end as hd_support_initiation_or_count_increase_flag,

        -- Broader support-change candidate:
        -- includes new agent after preuse, even if total agent count does not increase.
        case
            when (
                    a.pre12_agent_count = 0
                and a.post12_agent_count > 0
                 )
              or (
                    a.pre12_agent_count > 0
                and a.post12_new_agent_count > 0
                 )
              or (
                    a.post12_agent_count > a.pre12_agent_count
                 )
            then 1 else 0
        end as hd_support_new_or_switched_agent_flag,

        -- ----------------------------------------------------
        -- Lactate worsening definitions.
        -- Lactate >=2 alone is NOT counted as an event.
        -- ----------------------------------------------------
        case
            when pls.pre12_lactate_max is not null
             and pls.pre12_lactate_max < 2
             and pol.post12_lactate_max >= 2
            then 1 else 0
        end as lactate_new_ge2_flag,

        case
            when pls.pre12_lactate_max >= 2
             and pls.pre12_lactate_max < 4
             and pol.post12_lactate_max >= 4
            then 1 else 0
        end as lactate_2to4_worsen_ge4_flag,

        case
            when pll.pre12_lactate_last is not null
             and pol.post12_lactate_max is not null
             and pol.post12_lactate_max - pll.pre12_lactate_last >= 2
            then 1 else 0
        end as lactate_delta_ge2_from_last_flag,

        case
            when (
                    pls.pre12_lactate_max is not null
                and pls.pre12_lactate_max < 2
                and pol.post12_lactate_max >= 2
                 )
              or (
                    pls.pre12_lactate_max >= 2
                and pls.pre12_lactate_max < 4
                and pol.post12_lactate_max >= 4
                 )
              or (
                    pll.pre12_lactate_last is not null
                and pol.post12_lactate_max is not null
                and pol.post12_lactate_max - pll.pre12_lactate_last >= 2
                 )
            then 1 else 0
        end as lactate_worsening_any_flag,

        case
            when pls.pre12_lactate_n = 0
             and pol.post12_lactate_max >= 4
            then 1 else 0
        end as post12_lactate_ge4_with_missing_pre12_flag

    from base b
    left join pre_lactate_summary pls
        on b.stay_id = pls.stay_id
    left join pre_lactate_last pll
        on b.stay_id = pll.stay_id
    left join post_lactate_summary pol
        on b.stay_id = pol.stay_id
    left join agent_flags a
        on b.stay_id = a.stay_id
)

select
    *,

    -- Broad HD deterioration:
    -- support initiation / agent-count escalation OR death.
    case
        when hd_support_initiation_or_count_increase_flag = 1
          or death_12_60_flag = 1
        then 1 else 0
    end as hd_deterioration_broad_flag,

    -- Lactate-confirmed HD deterioration:
    -- support initiation / agent-count escalation + lactate worsening OR death.
    case
        when (
                hd_support_initiation_or_count_increase_flag = 1
            and lactate_worsening_any_flag = 1
             )
          or death_12_60_flag = 1
        then 1 else 0
    end as hd_deterioration_lac_confirmed_flag,

    -- Broader medication-change composite:
    -- includes switching/new agent after prior exposure.
    case
        when hd_support_new_or_switched_agent_flag = 1
          or death_12_60_flag = 1
        then 1 else 0
    end as hd_deterioration_med_change_broad_flag,

    -- Strict shock proxy + death.
    case
        when current_mixed_shock_proxy_flag = 1
          or death_12_60_flag = 1
        then 1 else 0
    end as mixed_shock_proxy_or_death_flag

from final_flags;





-- 063A QC1：候选结局事件率，按队列分层
with cohorted as (
    select
        '01_overall_ahf12' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1

    union all

    select
        '02_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 1

    union all

    select
        '03_no_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 0

    union all

    select
        '04_early_sepsis12_broad' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_broad_flag = 1

    union all

    select
        '05_sepsis3_any_icu' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where sepsis3_any_icu_flag = 1
),

long_outcomes as (
    select
        cohort,
        outcome,
        event_flag
    from cohorted c
    cross join lateral (
        values
            ('01_current_mixed_shock_proxy', current_mixed_shock_proxy_flag),
            ('02_current_mixed_shock_lac4_proxy', current_mixed_shock_lac4_proxy_flag),
            ('03_new_support_initiation', new_support_initiation_flag),
            ('04_new_agent_after_preuse', new_agent_after_preuse_flag),
            ('05_agent_count_increase', agent_count_increase_flag),
            ('06_hd_support_initiation_or_count_increase', hd_support_initiation_or_count_increase_flag),
            ('07_hd_support_new_or_switched_agent', hd_support_new_or_switched_agent_flag),
            ('08_lactate_new_ge2', lactate_new_ge2_flag),
            ('09_lactate_2to4_worsen_ge4', lactate_2to4_worsen_ge4_flag),
            ('10_lactate_delta_ge2_from_last', lactate_delta_ge2_from_last_flag),
            ('11_lactate_worsening_any', lactate_worsening_any_flag),
            ('12_death_12_60', death_12_60_flag),
            ('13_hd_deterioration_broad', hd_deterioration_broad_flag),
            ('14_hd_deterioration_lac_confirmed', hd_deterioration_lac_confirmed_flag),
            ('15_hd_deterioration_med_change_broad', hd_deterioration_med_change_broad_flag),
            ('16_mixed_shock_proxy_or_death', mixed_shock_proxy_or_death_flag)
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
		
		
		
		
-- 		063A QC2：主候选 composite 组成模式
with cohorted as (
    select
        '01_overall_ahf12' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1

    union all

    select
        '02_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 1

    union all

    select
        '03_no_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 0
)

select
    cohort,
    hd_support_initiation_or_count_increase_flag,
    hd_support_new_or_switched_agent_flag,
    lactate_worsening_any_flag,
    death_12_60_flag,
    hd_deterioration_broad_flag,
    hd_deterioration_lac_confirmed_flag,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (partition by cohort), 2) as pct
from cohorted
group by
    cohort,
    hd_support_initiation_or_count_increase_flag,
    hd_support_new_or_switched_agent_flag,
    lactate_worsening_any_flag,
    death_12_60_flag,
    hd_deterioration_broad_flag,
    hd_deterioration_lac_confirmed_flag
order by
    cohort,
    n desc;
		
		
		
		
-- 		063A QC3：complete60 分层事件率
with cohorted as (
    select
        '01_overall_ahf12' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1

    union all

    select
        '02_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 1

    union all

    select
        '03_no_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 0
)

select
    cohort,
    complete60_icu_flag,
    count(*) as n,

    sum(current_mixed_shock_proxy_flag) as n_current_mixed_shock,
    round(sum(current_mixed_shock_proxy_flag) * 100.0 / count(*), 2) as rate_current_mixed_shock,

    sum(hd_support_initiation_or_count_increase_flag) as n_support_escalation,
    round(sum(hd_support_initiation_or_count_increase_flag) * 100.0 / count(*), 2) as rate_support_escalation,

    sum(hd_deterioration_broad_flag) as n_hd_broad,
    round(sum(hd_deterioration_broad_flag) * 100.0 / count(*), 2) as rate_hd_broad,

    sum(hd_deterioration_lac_confirmed_flag) as n_hd_lac_confirmed,
    round(sum(hd_deterioration_lac_confirmed_flag) * 100.0 / count(*), 2) as rate_hd_lac_confirmed,

    sum(death_12_60_flag) as n_death,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as rate_death

from cohorted
group by
    cohort,
    complete60_icu_flag
order by
    cohort,
    complete60_icu_flag;
		
		
		
		
-- 		063A QC4：乳酸基线与乳酸恶化
with cohorted as (
    select
        '01_overall_ahf12' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1

    union all

    select
        '02_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 1

    union all

    select
        '03_no_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 0
)

select
    cohort,
    case
        when pre12_lactate_n = 0 then '00_no_pre12_lactate'
        when pre12_lactate_max < 2 then '01_pre12_max_lt2'
        when pre12_lactate_max >= 2 and pre12_lactate_max < 4 then '02_pre12_max_2_4'
        when pre12_lactate_max >= 4 then '03_pre12_max_ge4'
        else '99_other'
    end as pre12_lactate_group,
    count(*) as n,

    sum(lactate_new_ge2_flag) as n_lactate_new_ge2,
    round(sum(lactate_new_ge2_flag) * 100.0 / count(*), 2) as pct_lactate_new_ge2,

    sum(lactate_2to4_worsen_ge4_flag) as n_lactate_2to4_worsen_ge4,
    round(sum(lactate_2to4_worsen_ge4_flag) * 100.0 / count(*), 2) as pct_lactate_2to4_worsen_ge4,

    sum(lactate_delta_ge2_from_last_flag) as n_lactate_delta_ge2,
    round(sum(lactate_delta_ge2_from_last_flag) * 100.0 / count(*), 2) as pct_lactate_delta_ge2,

    sum(lactate_worsening_any_flag) as n_lactate_worsening_any,
    round(sum(lactate_worsening_any_flag) * 100.0 / count(*), 2) as pct_lactate_worsening_any,

    sum(hd_deterioration_lac_confirmed_flag) as n_hd_lac_confirmed,
    round(sum(hd_deterioration_lac_confirmed_flag) * 100.0 / count(*), 2) as pct_hd_lac_confirmed

from cohorted
group by
    cohort,
    case
        when pre12_lactate_n = 0 then '00_no_pre12_lactate'
        when pre12_lactate_max < 2 then '01_pre12_max_lt2'
        when pre12_lactate_max >= 2 and pre12_lactate_max < 4 then '02_pre12_max_2_4'
        when pre12_lactate_max >= 4 then '03_pre12_max_ge4'
        else '99_other'
    end
order by
    cohort,
    pre12_lactate_group;
		
		
		
		
-- 		063A QC5：药物变化模式
with cohorted as (
    select
        '01_overall_ahf12' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1

    union all

    select
        '02_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 1

    union all

    select
        '03_no_early_sepsis12_main' as cohort,
        *
    from study_ahf_v3.outcome_063A_candidate_hd_outcomes_overall_v1
    where early_sepsis12_main_flag = 0
)

select
    cohort,
    pre12_agent_count,
    post12_agent_count,
    post12_new_agent_count,
    new_support_initiation_flag,
    new_agent_after_preuse_flag,
    agent_count_increase_flag,
    hd_support_initiation_or_count_increase_flag,
    hd_support_new_or_switched_agent_flag,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (partition by cohort), 2) as pct
from cohorted
group by
    cohort,
    pre12_agent_count,
    post12_agent_count,
    post12_new_agent_count,
    new_support_initiation_flag,
    new_agent_after_preuse_flag,
    agent_count_increase_flag,
    hd_support_initiation_or_count_increase_flag,
    hd_support_new_or_switched_agent_flag
order by
    cohort,
    n desc;
		
		
		
