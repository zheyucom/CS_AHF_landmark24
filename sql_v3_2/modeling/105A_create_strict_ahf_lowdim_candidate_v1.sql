-- Create the candidate low-dimensional modeling input for the
-- 650-stay pragmatic strict pre-T0 operational AHF cohort.
-- Candidate status: pending investigator confirmation.
-- Qualification fields remain in the cohort/audit table only.

drop table if exists study_ahf_v3_2.model_105a_strict_ahf_lowdim_candidate_v1 cascade;

create table study_ahf_v3_2.model_105a_strict_ahf_lowdim_candidate_v1 as
select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.intime,
    b.landmark12_time,
    b.window60_time,
    b.final_state,
    b.fg_status_code,
    b.final_time,
    b.followup_hours_from_landmark,
    b.event_type,
    b.event_flag,
    b.compete_flag,
    b.admin_censor_flag,
    b.early_sepsis12_main_flag,
    b.complete60_icu_flag,

    p.age,
    p.map_lt65_record_prop,
    p.lactate_max,
    p.creatinine_max,
    p.urineoutput_0_12h_total_ml,
    p.advanced_respiratory_support_0_12h_flag
from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
inner join study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1 c
    on c.stay_id = b.stay_id
inner join study_ahf_v3_2.model_090B_compact_predictors_v33_v1 p
    on p.stay_id = b.stay_id;

create unique index idx_105a_strict_ahf_lowdim_stay
    on study_ahf_v3_2.model_105a_strict_ahf_lowdim_candidate_v1 (stay_id);

analyze study_ahf_v3_2.model_105a_strict_ahf_lowdim_candidate_v1;

select
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(event_flag) as n_events,
    sum(compete_flag) as n_compete,
    sum(admin_censor_flag) as n_censor,
    count(*) filter (where age is null) as age_missing,
    count(*) filter (where map_lt65_record_prop is null) as map_burden_missing,
    count(*) filter (where lactate_max is null) as lactate_missing,
    count(*) filter (where creatinine_max is null) as creatinine_missing,
    count(*) filter (where urineoutput_0_12h_total_ml is null) as urine_missing,
    count(*) filter (where advanced_respiratory_support_0_12h_flag is null) as respiratory_support_missing
from study_ahf_v3_2.model_105a_strict_ahf_lowdim_candidate_v1;
