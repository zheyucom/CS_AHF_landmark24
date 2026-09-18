-- ============================================================
-- Project: CS_AHF_landmark12 v3.2
-- File: sql_v3_2/audits/094_create_outcome_label_audit.sql
-- Purpose:
--   Audit validity of the 12-60h treatment-escalation outcome in
--   the overall AHF-by-T12 risk set (early sepsis remains a stratum).
--
-- Questions addressed:
--   1. Is an agent-count event a true concurrent escalation or an
--      artefact of agents appearing at different times?
--   2. Are NEE >=0.05 / >=0.10 events persistent for >=30 or >=60 min?
--   3. How often is a support event phenylephrine-only?
--   4. How do stricter candidate labels change event counts and timing?
--
-- Important:
--   This is an outcome-label audit only. All post-T12 fields below
--   are forbidden as predictor variables in the final model.
-- ============================================================

drop table if exists study_ahf_v3_2.audit_094_outcome_label_v1 cascade;

create table study_ahf_v3_2.audit_094_outcome_label_v1 as
with base as (
    select
        o.*,
        o.intime + interval '12 hour' as landmark12_time,
        o.intime + interval '60 hour' as window60_time
    from study_ahf_v3_2.outcome_063C_candidate_hd_outcomes_with_nee_v1 o
),

-- One row per active vasoactive/inotrope agent and clipped infusion interval.
vaso_agent_intervals as (
    select
        b.stay_id,
        b.landmark12_time,
        b.observed_until_time,
        greatest(v.starttime, b.intime) as effective_starttime,
        least(
            coalesce(v.endtime, v.starttime + interval '1 minute'),
            b.observed_until_time
        ) as effective_endtime,
        x.agent_name
    from base b
    inner join mimiciv_derived.vasoactive_agent v
        on b.stay_id = v.stay_id
       and v.starttime < b.observed_until_time
       and coalesce(v.endtime, v.starttime + interval '1 minute') > b.intime
    cross join lateral (
        values
            ('norepinephrine'::text, coalesce(v.norepinephrine, 0)),
            ('epinephrine'::text, coalesce(v.epinephrine, 0)),
            ('dopamine'::text, coalesce(v.dopamine, 0)),
            ('phenylephrine'::text, coalesce(v.phenylephrine, 0)),
            ('vasopressin'::text, coalesce(v.vasopressin, 0)),
            ('dobutamine'::text, coalesce(v.dobutamine, 0)),
            ('milrinone'::text, coalesce(v.milrinone, 0))
    ) x(agent_name, dose)
    where x.dose > 0
),

pre_agent_intervals as (
    select
        stay_id,
        agent_name,
        effective_starttime,
        least(effective_endtime, landmark12_time) as effective_endtime
    from vaso_agent_intervals
    where effective_starttime < landmark12_time
      and effective_endtime > effective_starttime
),

post_agent_intervals as (
    select
        stay_id,
        agent_name,
        greatest(effective_starttime, landmark12_time) as effective_starttime,
        effective_endtime
    from vaso_agent_intervals
    where effective_endtime > landmark12_time
      and effective_endtime > greatest(effective_starttime, landmark12_time)
),

pre_agent_exposure as (
    select
        stay_id,
        agent_name,
        max(effective_endtime) as pre12_agent_last_endtime
    from pre_agent_intervals
    group by stay_id, agent_name
),

pre_agent_starts as (
    select distinct stay_id, effective_starttime as point_time
    from pre_agent_intervals
),

pre_agent_concurrency as (
    select
        p.stay_id,
        p.point_time,
        count(distinct i.agent_name) as concurrent_agent_count
    from pre_agent_starts p
    inner join pre_agent_intervals i
        on p.stay_id = i.stay_id
       and i.effective_starttime <= p.point_time
       and i.effective_endtime > p.point_time
    group by p.stay_id, p.point_time
),

pre_agent_concurrency_summary as (
    select
        stay_id,
        max(concurrent_agent_count) as pre12_max_concurrent_agent_count
    from pre_agent_concurrency
    group by stay_id
),

post_agent_starts as (
    select distinct stay_id, effective_starttime as point_time
    from post_agent_intervals
),

post_agent_concurrency as (
    select
        p.stay_id,
        p.point_time,
        count(distinct i.agent_name) as concurrent_agent_count
    from post_agent_starts p
    inner join post_agent_intervals i
        on p.stay_id = i.stay_id
       and i.effective_starttime <= p.point_time
       and i.effective_endtime > p.point_time
    group by p.stay_id, p.point_time
),

post_agent_concurrency_summary as (
    select
        stay_id,
        max(concurrent_agent_count) as post12_max_concurrent_agent_count,
        min(point_time) filter (where concurrent_agent_count > 0) as first_post12_support_time,
        max(case when concurrent_agent_count > 0 then 1 else 0 end) as post12_any_agent_flag
    from post_agent_concurrency
    group by stay_id
),

post_agent_exposure_summary as (
    select
        stay_id,
        min(effective_starttime) as first_post12_any_agent_time,
        max(case when agent_name = 'phenylephrine' then 1 else 0 end) as post12_phenylephrine_any_flag,
        max(case when agent_name <> 'phenylephrine' then 1 else 0 end) as post12_nonphenylephrine_any_flag
    from post_agent_intervals
    group by stay_id
),

-- New relative to any agent documented before T12. These intervals are used to
-- examine whether the support-change component persists beyond a single record.
post_new_agent_intervals as (
    select p.*
    from post_agent_intervals p
    left join pre_agent_exposure pre
        on p.stay_id = pre.stay_id
       and p.agent_name = pre.agent_name
    where pre.agent_name is null
),

post_new_agent_prev_end as (
    select
        *,
        max(effective_endtime) over (
            partition by stay_id, agent_name
            order by effective_starttime, effective_endtime
            rows between unbounded preceding and 1 preceding
        ) as previous_max_endtime
    from post_new_agent_intervals
),

post_new_agent_grouped as (
    select
        *,
        sum(
            case
                when previous_max_endtime is null
                  or effective_starttime > previous_max_endtime
                then 1 else 0
            end
        ) over (
            partition by stay_id, agent_name
            order by effective_starttime, effective_endtime
            rows unbounded preceding
        ) as episode_id
    from post_new_agent_prev_end
),

post_new_agent_episodes as (
    select
        stay_id,
        agent_name,
        episode_id,
        min(effective_starttime) as episode_starttime,
        max(effective_endtime) as episode_endtime,
        extract(epoch from (max(effective_endtime) - min(effective_starttime))) / 3600.0
            as episode_duration_hours
    from post_new_agent_grouped
    group by stay_id, agent_name, episode_id
),

post_new_agent_summary as (
    select
        stay_id,
        min(episode_starttime) as first_new_agent_time,
        max(episode_duration_hours) as new_agent_max_continuous_duration_hours,
        sum(episode_duration_hours) as new_agent_total_duration_hours,
        max(case when episode_duration_hours >= 0.5 then 1 else 0 end) as new_agent_persistent_30min_flag,
        max(case when episode_duration_hours >= 1.0 then 1 else 0 end) as new_agent_persistent_60min_flag
    from post_new_agent_episodes
    group by stay_id
),

-- NEE intervals above each candidate threshold, merged into continuous episodes.
nee_threshold_intervals as (
    select
        b.stay_id,
        t.threshold,
        greatest(ne.starttime, b.landmark12_time) as effective_starttime,
        least(
            coalesce(ne.endtime, ne.starttime + interval '1 minute'),
            b.observed_until_time
        ) as effective_endtime
    from base b
    inner join mimiciv_derived.norepinephrine_equivalent_dose ne
        on b.stay_id = ne.stay_id
       and ne.starttime < b.observed_until_time
       and coalesce(ne.endtime, ne.starttime + interval '1 minute') > b.landmark12_time
    cross join lateral (values (0.05::numeric), (0.10::numeric)) t(threshold)
    where b.pre12_nee_max is not null
      and ne.norepinephrine_equivalent_dose - b.pre12_nee_max >= t.threshold
),

nee_threshold_prev_end as (
    select
        *,
        max(effective_endtime) over (
            partition by stay_id, threshold
            order by effective_starttime, effective_endtime
            rows between unbounded preceding and 1 preceding
        ) as previous_max_endtime
    from nee_threshold_intervals
    where effective_endtime > effective_starttime
),

nee_threshold_grouped as (
    select
        *,
        sum(
            case
                when previous_max_endtime is null
                  or effective_starttime > previous_max_endtime
                then 1 else 0
            end
        ) over (
            partition by stay_id, threshold
            order by effective_starttime, effective_endtime
            rows unbounded preceding
        ) as episode_id
    from nee_threshold_prev_end
),

nee_threshold_episodes as (
    select
        stay_id,
        threshold,
        episode_id,
        min(effective_starttime) as episode_starttime,
        max(effective_endtime) as episode_endtime,
        extract(epoch from (max(effective_endtime) - min(effective_starttime))) / 3600.0
            as episode_duration_hours
    from nee_threshold_grouped
    group by stay_id, threshold, episode_id
),

nee_threshold_summary as (
    select
        stay_id,
        threshold,
        min(episode_starttime) as first_escalation_time,
        max(episode_duration_hours) as max_continuous_duration_hours,
        sum(episode_duration_hours) as total_duration_hours,
        max(case when episode_duration_hours >= 0.5 then 1 else 0 end) as persistent_30min_flag,
        max(case when episode_duration_hours >= 1.0 then 1 else 0 end) as persistent_60min_flag
    from nee_threshold_episodes
    group by stay_id, threshold
),

nee_summary_wide as (
    select
        stay_id,
        min(first_escalation_time) filter (where threshold = 0.05) as first_nee005_escalation_time,
        max(max_continuous_duration_hours) filter (where threshold = 0.05) as nee005_max_continuous_duration_hours,
        max(total_duration_hours) filter (where threshold = 0.05) as nee005_total_duration_hours,
        max(persistent_30min_flag) filter (where threshold = 0.05) as nee005_persistent_30min_flag,
        max(persistent_60min_flag) filter (where threshold = 0.05) as nee005_persistent_60min_flag,
        min(first_escalation_time) filter (where threshold = 0.10) as first_nee010_escalation_time,
        max(max_continuous_duration_hours) filter (where threshold = 0.10) as nee010_max_continuous_duration_hours,
        max(total_duration_hours) filter (where threshold = 0.10) as nee010_total_duration_hours,
        max(persistent_30min_flag) filter (where threshold = 0.10) as nee010_persistent_30min_flag,
        max(persistent_60min_flag) filter (where threshold = 0.10) as nee010_persistent_60min_flag
    from nee_threshold_summary
    group by stay_id
),

death_times as (
    select
        b.stay_id,
        a.deathtime as death_time_12_60,
        case when a.deathtime >= b.outtime then 1 else 0 end as death_after_icu_discharge_flag
    from base b
    inner join mimiciv_hosp.admissions a
        on b.hadm_id = a.hadm_id
    where a.deathtime >= b.landmark12_time
      and a.deathtime < b.window60_time
),

audit_components as (
    select
        b.*,
        coalesce(precon.pre12_max_concurrent_agent_count, 0) as pre12_max_concurrent_agent_count,
        coalesce(postcon.post12_max_concurrent_agent_count, 0) as post12_max_concurrent_agent_count,
        postcon.first_post12_support_time,
        postexp.first_post12_any_agent_time,
        coalesce(postexp.post12_phenylephrine_any_flag, 0) as post12_phenylephrine_any_flag,
        coalesce(postexp.post12_nonphenylephrine_any_flag, 0) as post12_nonphenylephrine_any_flag,
        newagent.first_new_agent_time,
        coalesce(newagent.new_agent_max_continuous_duration_hours, 0) as new_agent_max_continuous_duration_hours,
        coalesce(newagent.new_agent_total_duration_hours, 0) as new_agent_total_duration_hours,
        coalesce(newagent.new_agent_persistent_30min_flag, 0) as new_agent_persistent_30min_flag,
        coalesce(newagent.new_agent_persistent_60min_flag, 0) as new_agent_persistent_60min_flag,
        nee.first_nee005_escalation_time,
        coalesce(nee.nee005_max_continuous_duration_hours, 0) as nee005_max_continuous_duration_hours,
        coalesce(nee.nee005_total_duration_hours, 0) as nee005_total_duration_hours,
        coalesce(nee.nee005_persistent_30min_flag, 0) as nee005_persistent_30min_flag,
        coalesce(nee.nee005_persistent_60min_flag, 0) as nee005_persistent_60min_flag,
        nee.first_nee010_escalation_time,
        coalesce(nee.nee010_max_continuous_duration_hours, 0) as nee010_max_continuous_duration_hours,
        coalesce(nee.nee010_total_duration_hours, 0) as nee010_total_duration_hours,
        coalesce(nee.nee010_persistent_30min_flag, 0) as nee010_persistent_30min_flag,
        coalesce(nee.nee010_persistent_60min_flag, 0) as nee010_persistent_60min_flag,
        d.death_time_12_60,
        coalesce(d.death_after_icu_discharge_flag, 0) as death_after_icu_discharge_flag
    from base b
    left join pre_agent_concurrency_summary precon on b.stay_id = precon.stay_id
    left join post_agent_concurrency_summary postcon on b.stay_id = postcon.stay_id
    left join post_agent_exposure_summary postexp on b.stay_id = postexp.stay_id
    left join post_new_agent_summary newagent on b.stay_id = newagent.stay_id
    left join nee_summary_wide nee on b.stay_id = nee.stay_id
    left join death_times d on b.stay_id = d.stay_id
),

classified as (
    select
        *,
        case
            when hd_support_initiation_or_count_increase_flag = 1
             and post12_max_concurrent_agent_count > pre12_max_concurrent_agent_count
            then 1 else 0
        end as support_concurrent_escalation_flag,

        case
            when hd_support_initiation_or_count_increase_flag = 1
             and new_agent_persistent_30min_flag = 1
            then 1 else 0
        end as support_durable_30min_flag,

        case
            when hd_support_initiation_or_count_increase_flag = 1
             and new_agent_persistent_60min_flag = 1
            then 1 else 0
        end as support_durable_60min_flag,

        case
            when hd_support_initiation_or_count_increase_flag = 1
             and post12_max_concurrent_agent_count > pre12_max_concurrent_agent_count
             and new_agent_persistent_30min_flag = 1
            then 1 else 0
        end as support_concurrent_durable_30min_flag,

        case
            when hd_support_initiation_or_count_increase_flag = 1
             and post12_max_concurrent_agent_count > pre12_max_concurrent_agent_count
             and new_agent_persistent_60min_flag = 1
            then 1 else 0
        end as support_concurrent_durable_60min_flag,

        case
            when hd_support_initiation_or_count_increase_flag = 1
             and post12_phenylephrine_any_flag = 1
             and post12_nonphenylephrine_any_flag = 0
            then 1 else 0
        end as support_phenylephrine_only_flag,

        case
            when hd_support_initiation_or_count_increase_flag = 1
             and new_support_initiation_flag = 1 then 'new_support_initiation'
            when hd_support_initiation_or_count_increase_flag = 1
             and agent_count_increase_flag = 1 then 'agent_count_increase'
            when hd_support_initiation_or_count_increase_flag = 1 then 'other_support_flag'
            when new_agent_after_preuse_flag = 1 then 'drug_switch_only_not_primary_component'
            else 'no_support_change'
        end as support_event_type
    from audit_components
),

timed as (
    select
        *,
        least(
            case
                when hd_support_initiation_or_count_increase_flag = 1
                then coalesce(first_new_agent_time, timestamp 'infinity')
                else timestamp 'infinity'
            end,
            case
                when nee_escalation_conservative_flag = 1
                then coalesce(first_nee005_escalation_time, timestamp 'infinity')
                else timestamp 'infinity'
            end,
            coalesce(death_time_12_60, timestamp 'infinity')
        ) as primary_event_time_raw
    from classified
)

select
    subject_id,
    hadm_id,
    stay_id,
    intime,
    outtime,
    landmark12_time,
    window60_time,
    observed_until_time,
    followup_hours_12_60,
    complete60_icu_flag,
    early_sepsis12_main_flag,

    -- Existing outcome and components.
    hd_deterioration_broad_nee005_flag as current_primary_outcome_flag,
    hd_deterioration_broad_nee010_flag as current_nee010_outcome_flag,
    hd_support_initiation_or_count_increase_flag as current_support_component_flag,
    new_support_initiation_flag,
    agent_count_increase_flag,
    new_agent_after_preuse_flag,
    nee_escalation_conservative_flag as current_nee005_component_flag,
    nee_delta_from_premax_ge010_flag as current_nee010_component_flag,
    death_12_60_flag,

    -- Concurrent vasoactive/inotrope audit.
    pre12_agent_count,
    post12_agent_count,
    pre12_max_concurrent_agent_count,
    post12_max_concurrent_agent_count,
    first_post12_support_time,
    first_new_agent_time as first_support_candidate_time,
    support_event_type,
    support_concurrent_escalation_flag,
    support_durable_30min_flag,
    support_durable_60min_flag,
    support_concurrent_durable_30min_flag,
    support_concurrent_durable_60min_flag,
    support_phenylephrine_only_flag,
    post12_phenylephrine_any_flag,
    post12_nonphenylephrine_any_flag,
    new_agent_max_continuous_duration_hours,
    new_agent_total_duration_hours,

    -- NEE persistence audit.
    pre12_nee_max,
    post12_nee_max,
    post12_nee_max - pre12_nee_max as post12_nee_delta_max,
    first_nee005_escalation_time,
    nee005_max_continuous_duration_hours,
    nee005_total_duration_hours,
    nee005_persistent_30min_flag,
    nee005_persistent_60min_flag,
    first_nee010_escalation_time,
    nee010_max_continuous_duration_hours,
    nee010_total_duration_hours,
    nee010_persistent_30min_flag,
    nee010_persistent_60min_flag,

    -- Death and timing audit.
    death_time_12_60,
    death_after_icu_discharge_flag,
    case when primary_event_time_raw = timestamp 'infinity' then null else primary_event_time_raw end
        as current_primary_event_time,
    case
        when primary_event_time_raw = timestamp 'infinity' then null
        else extract(epoch from (primary_event_time_raw - landmark12_time)) / 3600.0
    end as current_primary_event_hour_after_landmark,
    case
        when primary_event_time_raw = timestamp 'infinity' then null
        when primary_event_time_raw = first_new_agent_time then 'support'
        when primary_event_time_raw = first_nee005_escalation_time then 'nee005'
        when primary_event_time_raw = death_time_12_60 then 'death'
        else null
    end as current_primary_event_component_first,

    -- Strict candidate for sensitivity only: true concurrent support escalation
    -- durable >=30 min OR NEE >=0.05 durable >=30 min OR death.
    case
        when support_concurrent_durable_30min_flag = 1
          or nee005_persistent_30min_flag = 1
          or death_12_60_flag = 1
        then 1 else 0
    end as strict_30min_outcome_flag,
    case
        when support_concurrent_durable_60min_flag = 1
          or nee005_persistent_60min_flag = 1
          or death_12_60_flag = 1
        then 1 else 0
    end as strict_60min_outcome_flag,
    case
        when support_concurrent_durable_30min_flag = 1
          or nee010_persistent_30min_flag = 1
          or death_12_60_flag = 1
        then 1 else 0
    end as strict_nee010_30min_outcome_flag

from timed;
