-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v3_2/audits/096_create_strict_main_label_v33.sql
-- Purpose:
--   Rewrite the strict main outcome label for v3.3 under the
--   competing-risk estimand:
--
--     ICU-level hemodynamic deterioration between T12 and
--     min(T60, alive ICU discharge); alive ICU discharge is the
--     competing event.
--
--   Event = a true concurrent-support level ABOVE the pre-T12
--   baseline, with the elevated state itself lasting >=30 min
--   continuously; OR NEE > pre-T12 baseline + 0.05 sustained
--   >=30 min; OR in-ICU death. Death after ICU discharge is NOT
--   a main event (flagged separately).
--
--   Support level is measured per minute-resolution segment:
--   number of DISTINCT vasoactive/inotrope drug classes active
--   at that time (real concurrency, not infusion-record count).
--
--   Event time anchor: start of the elevated run + 30 min
--   (i.e., the moment the escalation is confirmed).
--
--   Three-state label:
--     state='event'   time = min(escalation_confirm, in_icu_death)
--     state='compete' time = outtime (alive ICU discharge first)
--     state='censor'  time = T60 (still in ICU, no event)
-- ============================================================

drop table if exists study_ahf_v3_2.audit_096_strict_main_label_v33_v1 cascade;

create table study_ahf_v3_2.audit_096_strict_main_label_v33_v1 as
with base as (
    select
        o.stay_id, o.subject_id, o.hadm_id, o.intime, o.outtime,
        o.intime + interval '12 hour' as landmark12_time,
        o.intime + interval '60 hour' as window60_time,
        o.observed_until_time,
        e.deathtime,
        o.complete60_icu_flag, o.early_sepsis12_main_flag
    from study_ahf_v3_2.outcome_063c_candidate_hd_outcomes_with_nee_v1 o
    left join study_ahf_v3_2.outcome_061e_post12_overt_cs_future48h_main_v1 e
        on o.stay_id = e.stay_id
),

-- ------------------------------------------------------------
-- Expand vasoactive_agent into per-drug intervals (dose > 0)
-- ------------------------------------------------------------
drug_iv as (
    select stay_id, 'dopamine'::text as drug, starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(dopamine, 0) > 0
    union all
    select stay_id, 'epinephrine', starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(epinephrine, 0) > 0
    union all
    select stay_id, 'norepinephrine', starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(norepinephrine, 0) > 0
    union all
    select stay_id, 'phenylephrine', starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(phenylephrine, 0) > 0
    union all
    select stay_id, 'vasopressin', starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(vasopressin, 0) > 0
    union all
    select stay_id, 'dobutamine', starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(dobutamine, 0) > 0
    union all
    select stay_id, 'milrinone', starttime, endtime
    from mimiciv_derived.vasoactive_agent where coalesce(milrinone, 0) > 0
),

-- Keep only intervals overlapping [T0, min(T60, outtime))
iv_in_window as (
    select
        b.stay_id, d.drug,
        greatest(d.starttime, b.intime) as starttime,
        least(d.endtime, least(b.window60_time, b.outtime)) as endtime
    from base b
    join drug_iv d on b.stay_id = d.stay_id
    where d.starttime < least(b.window60_time, b.outtime)
      and d.endtime > b.intime
),

-- ------------------------------------------------------------
-- Build all segment breakpoints per stay from drug starts/ends
-- plus T0, T12, T60, outtime
-- ------------------------------------------------------------
breakpoints as (
    select stay_id, ts from (
        select stay_id, starttime ts from iv_in_window
        union
        select stay_id, endtime ts from iv_in_window
        union
        select stay_id, intime from base
        union
        select stay_id, landmark12_time from base
        union
        select stay_id, window60_time from base
        union
        select stay_id, outtime from base
    ) t
    where ts is not null
),
segments as (
    select
        stay_id,
        ts as seg_start,
        lead(ts) over (partition by stay_id order by ts) as seg_end
    from breakpoints
),
seg_trimmed as (
    select
        s.stay_id,
        s.seg_start,
        s.seg_end,
        b.landmark12_time,
        b.window60_time,
        b.outtime
    from segments s
    join base b on s.stay_id = b.stay_id
    where s.seg_end is not null and s.seg_end > s.seg_start
),

-- ------------------------------------------------------------
-- Per segment: distinct active drug count and max NEE
-- ------------------------------------------------------------
seg_agent as (
    select
        s.stay_id,
        s.seg_start,
        s.seg_end,
        count(distinct i.drug) as n_active_drugs
    from seg_trimmed s
    join iv_in_window i
        on s.stay_id = i.stay_id
       and i.starttime < s.seg_end
       and i.endtime > s.seg_start
    group by s.stay_id, s.seg_start, s.seg_end
),
seg_nee as (
    select
        s.stay_id,
        s.seg_start,
        s.seg_end,
        max(ne.norepinephrine_equivalent_dose) as nee_max
    from seg_trimmed s
    left join mimiciv_derived.norepinephrine_equivalent_dose ne
        on s.stay_id = ne.stay_id
       and ne.starttime < s.seg_end
       and ne.endtime > s.seg_start
    group by s.stay_id, s.seg_start, s.seg_end
),
seg_all as (
    select
        s.*,
        coalesce(a.n_active_drugs, 0) as n_active_drugs,
        coalesce(n.nee_max, 0) as nee_max
    from seg_trimmed s
    left join seg_agent a using (stay_id, seg_start, seg_end)
    left join seg_nee n using (stay_id, seg_start, seg_end)
),

-- ------------------------------------------------------------
-- Pre-T12 baseline: max concurrent drug count and max NEE over
-- [T0, T12); plus NEE last-active at/near T12 (sensitivity)
-- ------------------------------------------------------------
pre12_base as (
    select
        stay_id,
        max(n_active_drugs) as pre12_max_agent_count,
        max(nee_max) as pre12_nee_max
    from seg_all
    where seg_end <= landmark12_time
    group by stay_id
),

-- NEE active AT T12 (infusion covering T12) = primary "last" definition;
-- 0 if no active infusion at T12. Historic nearest dose = sensitivity only.
pre12_nee_at_t12 as (
    select
        stay_id,
        max(nee_max) as pre12_nee_at_t12
    from seg_all
    where seg_start < landmark12_time
      and seg_end > landmark12_time
      and nee_max > 0
    group by stay_id
),
pre12_nee_historic as (
    select stay_id, nee_max as pre12_nee_historic
    from (
        select stay_id, seg_end, nee_max,
               row_number() over (
                   partition by stay_id order by seg_end desc
               ) as rn
        from seg_all
        where seg_start < landmark12_time
          and nee_max > 0
    ) x
    where rn = 1
),

-- ------------------------------------------------------------
-- Escalation segments in [T12, min(T60, outtime))
-- ------------------------------------------------------------
esc_segs as (
    select
        s.*,
        p.pre12_max_agent_count,
        p.pre12_nee_max,
        case when (
            s.n_active_drugs > p.pre12_max_agent_count
         or s.nee_max > coalesce(p.pre12_nee_max, 0) + 0.05
        ) then 1 else 0 end as esc_flag
    from seg_all s
    left join pre12_base p using (stay_id)
    where s.seg_start >= s.landmark12_time
      and s.seg_end <= least(s.window60_time, s.outtime)
),

-- ------------------------------------------------------------
-- Run detection: consecutive escalation segments summing to
-- >= 30 min. Event time = run start + 30 min.
-- ------------------------------------------------------------
esc_runs as (
    select
        stay_id,
        seg_start,
        seg_end,
        esc_flag,
        extract(epoch from (seg_end - seg_start)) / 60.0 as seg_min
    from esc_segs
),
-- Strict run id: ANY non-escalation segment breaks the run (0 min gap).
-- Bridge-5 run id: a non-escalation segment <= 5 min does NOT break the
-- run (MIMIC infusion-record gaps may create spurious interruptions);
-- used only as the prespecified sensitivity definition.
run_flagged as (
    select
        *,
        sum(case when esc_flag = 0 then 1 else 0 end) over (
            partition by stay_id order by seg_start
        ) as run_id_strict,
        sum(case when esc_flag = 0 and seg_min > 5 then 1 else 0 end) over (
            partition by stay_id order by seg_start
        ) as run_id_bridge5
    from esc_runs
),
run_agg as (
    select
        stay_id,
        run_id_strict as run_id,
        min(seg_start) as run_start,
        sum(seg_min) as run_min
    from run_flagged
    where esc_flag = 1
    group by stay_id, run_id_strict
),
run_agg_bridge5 as (
    select
        stay_id,
        run_id_bridge5 as run_id,
        min(seg_start) as run_start,
        sum(seg_min) as run_min
    from run_flagged
    where esc_flag = 1
    group by stay_id, run_id_bridge5
),
run_confirmed as (
    select
        stay_id,
        min(run_start + interval '30 minute') as esc_confirm_time
    from run_agg
    where run_min >= 30
    group by stay_id
),
run_confirmed_bridge5 as (
    select
        stay_id,
        min(run_start + interval '30 minute') as esc_confirm_time_bridge5
    from run_agg_bridge5
    where run_min >= 30
    group by stay_id
),

-- ------------------------------------------------------------
-- In-ICU death and post-exit death
-- ------------------------------------------------------------
death_flags as (
    select
        stay_id,
        case when deathtime is not null
              and deathtime < outtime
              and deathtime < window60_time
             then deathtime end as in_icu_death_time,
        case when deathtime is not null
              and deathtime > outtime
              and deathtime <= window60_time
             then 1 else 0 end as death_after_exit_flag
    from base
),

-- ------------------------------------------------------------
-- Three-state label
-- ------------------------------------------------------------
labeled as (
    select
        b.*,
        r.esc_confirm_time,
        rb.esc_confirm_time_bridge5,
        d.in_icu_death_time,
        d.death_after_exit_flag,
        least(
            r.esc_confirm_time,
            d.in_icu_death_time
        ) as event_time,
        b.outtime as compete_time,
        b.window60_time as censor_time,
        p.pre12_max_agent_count,
        p.pre12_nee_max,
        coalesce(nt.pre12_nee_at_t12, 0) as pre12_nee_last,
        coalesce(nh.pre12_nee_historic, 0) as pre12_nee_historic
    from base b
    left join run_confirmed r using (stay_id)
    left join run_confirmed_bridge5 rb using (stay_id)
    left join death_flags d using (stay_id)
    left join pre12_base p using (stay_id)
    left join pre12_nee_at_t12 nt using (stay_id)
    left join pre12_nee_historic nh using (stay_id)
),
final_label as (
    select
        l.*,
        -- Priority rule: only event_time STRICTLY before outtime counts as
        -- an interest event; event_time == outtime is assigned to compete.
        case
            when l.event_time is not null
             and (l.compete_time is null or l.event_time < l.compete_time)
            then 'event'
            when l.compete_time is not null
             and l.compete_time < l.window60_time
            then 'compete'
            else 'censor'
        end as final_state,
        case
            when l.event_time is not null
             and (l.compete_time is null or l.event_time < l.compete_time)
            then l.event_time
            when l.compete_time is not null
             and l.compete_time < l.window60_time
            then l.compete_time
            else l.window60_time
        end as final_time,
        case
            when l.event_time is not null
             and (l.compete_time is null or l.event_time < l.compete_time)
             and l.esc_confirm_time is not null
             and (l.in_icu_death_time is null or l.esc_confirm_time <= l.in_icu_death_time)
            then 'escalation'
            when l.event_time is not null
             and (l.compete_time is null or l.event_time < l.compete_time)
            then 'in_icu_death'
            else null
        end as event_type
    from labeled l
)
select * from final_label;

create index if not exists idx_096_strict_label_stay
    on study_ahf_v3_2.audit_096_strict_main_label_v33_v1 (stay_id);

analyze study_ahf_v3_2.audit_096_strict_main_label_v33_v1;

-- ============================================================
-- QC1: three-state distribution + event rate (main estimand)
-- ============================================================
select
    final_state,
    count(*) as n,
    sum(case when early_sepsis12_main_flag = 1 then 1 else 0 end) as n_sepsis
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
group by final_state
order by final_state;

-- ============================================================
-- QC2: main event rate overall and by sepsis stratum
-- ============================================================
select
    '01_overall'::text as stratum,
    count(*) as n,
    sum(case when final_state = 'event' then 1 else 0 end) as n_events,
    round(avg((final_state = 'event')::int) * 100.0, 2) as event_rate_pct
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
union all
select
    '02_sepsis',
    count(*),
    sum(case when final_state = 'event' then 1 else 0 end),
    round(avg((final_state = 'event')::int) * 100.0, 2)
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
where early_sepsis12_main_flag = 1
union all
select
    '03_no_sepsis',
    count(*),
    sum(case when final_state = 'event' then 1 else 0 end),
    round(avg((final_state = 'event')::int) * 100.0, 2)
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
where early_sepsis12_main_flag = 0;

-- ============================================================
-- QC3: event type composition
-- ============================================================
select
    event_type,
    count(*) as n
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
where final_state = 'event'
group by event_type
order by event_type;

-- ============================================================
-- QC4: death after ICU exit (should equal 15 from 095 audit)
-- ============================================================
select
    count(*) as n_death_after_exit,
    sum(case when final_state = 'compete' then 1 else 0 end) as n_compete_with_postexit_death
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
where death_after_exit_flag = 1;

-- ============================================================
-- QC5: pre-T12 baseline distributions
-- ============================================================
select
    count(*) as n,
    round(avg(pre12_max_agent_count), 2) as mean_pre12_agent,
    round(avg(pre12_nee_max), 3) as mean_pre12_nee_max,
    round(avg(pre12_nee_last), 3) as mean_pre12_nee_last,
    round(avg(pre12_nee_historic), 3) as mean_pre12_nee_historic,
    sum(case when pre12_max_agent_count is null then 1 else 0 end) as n_missing_baseline
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1;

-- ============================================================
-- QC6: boundary test - event_time == outtime cases (must be compete)
-- ============================================================
select
    count(*) as n_event_time_eq_outtime,
    sum(case when final_state = 'event' then 1 else 0 end) as n_still_event,
    sum(case when final_state = 'compete' then 1 else 0 end) as n_compete
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
where event_time is not null
  and compete_time is not null
  and event_time = compete_time;

-- ============================================================
-- QC7: bridge-5 sensitivity - additional events gained vs strict
-- ============================================================
select
    count(*) as n_total,
    sum(case when final_state = 'event' then 1 else 0 end) as n_events_strict,
    sum(case when esc_confirm_time_bridge5 is not null
              and (in_icu_death_time is null or esc_confirm_time_bridge5 < in_icu_death_time)
              and (outtime is null or esc_confirm_time_bridge5 < outtime)
             then 1 else 0 end) as n_events_bridge5
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1;

-- ============================================================
-- QC8: escalation-only events (any-cause death excluded)
-- ============================================================
select
    count(*) as n_escalation_only_events
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1
where final_state = 'event' and event_type = 'escalation';
