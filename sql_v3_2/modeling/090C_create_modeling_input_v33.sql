-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/modeling/090C_create_modeling_input_v33.sql
-- Purpose:
--   Join the v3.3 Fine-Gray label base to the compact no-leakage
--   predictor table. This is the stay-level modeling input.
-- ============================================================

drop table if exists study_ahf_v3_2.model_090C_finegray_input_v33_v1 cascade;

create table study_ahf_v3_2.model_090C_finegray_input_v33_v1 as
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
    b.death_after_exit_flag,

    p.age,
    p.female,
    p.first_unit_micu_flag,
    p.first_unit_ccu_cicu_flag,
    p.first_unit_sicu_flag,
    p.first_unit_cvicu_flag,
    p.hr_mean,
    p.hr_max,
    p.mbp_mean,
    p.mbp_min,
    p.sbp_min,
    p.dbp_min,
    p.rr_mean,
    p.rr_max,
    p.spo2_mean,
    p.spo2_min,
    p.temp_max,
    p.map_lt65_record_prop,
    p.sbp_lt90_record_prop,
    p.hr_gt110_record_prop,
    p.rr_gt24_record_prop,
    p.spo2_lt90_record_prop,
    p.shock_index_max,
    p.modified_shock_index_max,
    p.pulse_pressure_min,
    p.mbp_slope_per_hour,
    p.lactate_max,
    p.lactate_delta,
    p.ph_min,
    p.baseexcess_min,
    p.creatinine_max,
    p.creatinine_delta,
    p.bun_max,
    p.sodium_min,
    p.sodium_max,
    p.potassium_min,
    p.potassium_max,
    p.chem_bicarbonate_min,
    p.wbc_max,
    p.hemoglobin_min,
    p.platelet_min,
    p.inr_max,
    p.urineoutput_0_12h_total_ml,
    p.gcs_min,
    p.advanced_respiratory_support_0_12h_flag

from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
inner join study_ahf_v3_2.model_090B_compact_predictors_v33_v1 p
    on b.stay_id = p.stay_id;

create unique index if not exists idx_090c_finegray_input_v33_stay
    on study_ahf_v3_2.model_090C_finegray_input_v33_v1 (stay_id);

analyze study_ahf_v3_2.model_090C_finegray_input_v33_v1;

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
    'study_ahf_v3_2.model_090C_finegray_input_v33_v1',
    'sql_v3_2/modeling/090C_create_modeling_input_v33.sql',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    sum(event_flag),
    sum(event_flag)::numeric / nullif(count(*), 0),
    'T12 to min(T60, alive index-ICU discharge); predictors baseline/[T0,T12)',
    '090C_v33',
    'Stay-level Fine-Gray modeling input: v3.3 labels plus 45 compact no-leakage predictors.'
from study_ahf_v3_2.model_090C_finegray_input_v33_v1;
