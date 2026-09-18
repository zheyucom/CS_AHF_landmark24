-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/modeling/090A_create_modeling_base_v33.sql
-- Purpose:
--   Create the stay-level Fine-Gray modeling base from the explicit
--   v3.3 landmark-eligible label table.
--
-- Important:
--   This table contains labels, follow-up times, stratum markers, and
--   audit-only baseline support fields. It is not a predictor table.
-- ============================================================

drop table if exists study_ahf_v3_2.model_090A_modeling_base_v33_v1 cascade;

create table study_ahf_v3_2.model_090A_modeling_base_v33_v1 as
select
    l.subject_id,
    l.hadm_id,
    l.stay_id,
    l.intime,
    l.outtime,
    l.landmark12_time,
    l.window60_time,

    l.final_state,
    case
        when l.final_state = 'event' then 1
        when l.final_state = 'compete' then 2
        when l.final_state = 'censor' then 0
        else null
    end as fg_status_code,
    l.final_time,
    extract(epoch from (l.final_time - l.landmark12_time)) / 3600.0
        as followup_hours_from_landmark,

    l.event_type,
    case when l.final_state = 'event' then 1 else 0 end as event_flag,
    case when l.final_state = 'compete' then 1 else 0 end as compete_flag,
    case when l.final_state = 'censor' then 1 else 0 end as admin_censor_flag,

    l.early_sepsis12_main_flag,
    l.complete60_icu_flag,
    l.death_after_exit_flag,

    -- Audit-only fields. They must not be copied into the primary predictor set.
    l.pre12_max_agent_count,
    l.pre12_nee_max,
    l.pre12_nee_last,
    l.pre12_nee_historic

from study_ahf_v3_2.model_098_strict_label_v33_v1 l
where l.landmark_ineligible_flag = 0;

create unique index if not exists idx_090a_modeling_base_v33_stay
    on study_ahf_v3_2.model_090A_modeling_base_v33_v1 (stay_id);

analyze study_ahf_v3_2.model_090A_modeling_base_v33_v1;

insert into study_ahf_v3_2.run_manifest (
    table_name,
    sql_file,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    n_events,
    event_rate,
    time_window,
    version_tag,
    notes
)
select
    'study_ahf_v3_2.model_090A_modeling_base_v33_v1',
    'sql_v3_2/modeling/090A_create_modeling_base_v33.sql',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    sum(event_flag),
    sum(event_flag)::numeric / nullif(count(*), 0),
    'T12 to min(T60, alive index-ICU discharge)',
    '090A_v33',
    'Stay-level Fine-Gray modeling base from v3.3 landmark-eligible label table; labels and audit-only support fields, no predictors.'
from study_ahf_v3_2.model_090A_modeling_base_v33_v1;

