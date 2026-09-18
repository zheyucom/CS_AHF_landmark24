-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/audits/098_reconcile_landmark_eligibility_v33.sql
-- Purpose:
--   Reconcile the strict v3.3 outcome label with the T12 landmark.
--
-- Landmark eligibility requires that the patient is still under
-- observation at T12. Explicitly exclude stays with:
--   1) final_time <= T12;
--   2) ICU outtime <= T12;
--   3) admission death time <= T12.
--
-- The full audit table retains every v3.3 candidate and exclusion
-- reason. The modeling label table contains eligible stays only.
-- ============================================================

drop table if exists study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1 cascade;

create table study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1 as
select
    l.*,

    case
        when l.final_time <= l.landmark12_time then 1 else 0
    end as exclude_final_time_at_or_before_t12_flag,

    case
        when l.outtime <= l.landmark12_time then 1 else 0
    end as exclude_outtime_at_or_before_t12_flag,

    case
        when l.deathtime is not null
         and l.deathtime <= l.landmark12_time
        then 1 else 0
    end as exclude_death_at_or_before_t12_flag,

    case
        when l.final_time <= l.landmark12_time
          or l.outtime <= l.landmark12_time
          or (l.deathtime is not null and l.deathtime <= l.landmark12_time)
        then 1 else 0
    end as landmark_ineligible_flag,

    case
        when l.final_time <= l.landmark12_time
         and l.outtime <= l.landmark12_time
         and l.deathtime is not null
         and l.deathtime <= l.landmark12_time
            then 'final_time_outtime_death_at_or_before_t12'
        when l.final_time <= l.landmark12_time
         and l.outtime <= l.landmark12_time
            then 'final_time_and_outtime_at_or_before_t12'
        when l.final_time <= l.landmark12_time
         and l.deathtime is not null
         and l.deathtime <= l.landmark12_time
            then 'final_time_and_death_at_or_before_t12'
        when l.outtime <= l.landmark12_time
         and l.deathtime is not null
         and l.deathtime <= l.landmark12_time
            then 'outtime_and_death_at_or_before_t12'
        when l.final_time <= l.landmark12_time
            then 'final_time_at_or_before_t12'
        when l.outtime <= l.landmark12_time
            then 'outtime_at_or_before_t12'
        when l.deathtime is not null
         and l.deathtime <= l.landmark12_time
            then 'death_at_or_before_t12'
        else 'eligible_at_t12'
    end as landmark_eligibility_reason
from study_ahf_v3_2.audit_096_strict_main_label_v33_v1 l;

create index if not exists idx_098_landmark_eligibility_stay
    on study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1 (stay_id);

drop table if exists study_ahf_v3_2.model_098_strict_label_v33_v1 cascade;

create table study_ahf_v3_2.model_098_strict_label_v33_v1 as
select *
from study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1
where landmark_ineligible_flag = 0;

create index if not exists idx_098_model_label_stay
    on study_ahf_v3_2.model_098_strict_label_v33_v1 (stay_id);

analyze study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1;
analyze study_ahf_v3_2.model_098_strict_label_v33_v1;

-- QC1: reconciliation summary
select
    count(*) as n_candidate_v33,
    sum(case when landmark_ineligible_flag = 0 then 1 else 0 end) as n_landmark_eligible,
    sum(case when landmark_ineligible_flag = 1 then 1 else 0 end) as n_landmark_ineligible,
    sum(case when landmark_ineligible_flag = 0 and final_state = 'event' then 1 else 0 end) as n_eligible_events,
    sum(case when landmark_ineligible_flag = 0 and final_state = 'compete' then 1 else 0 end) as n_eligible_competes,
    sum(case when landmark_ineligible_flag = 0 and final_state = 'censor' then 1 else 0 end) as n_eligible_censors
from study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1;

-- QC2: exclusion reasons
select
    landmark_eligibility_reason,
    count(*) as n,
    sum(case when final_state = 'event' then 1 else 0 end) as n_event,
    sum(case when final_state = 'compete' then 1 else 0 end) as n_compete,
    sum(case when final_state = 'censor' then 1 else 0 end) as n_censor
from study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1
group by landmark_eligibility_reason
order by landmark_eligibility_reason;

