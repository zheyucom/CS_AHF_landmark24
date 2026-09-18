-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/03_features/080G_create_modeling_dataset_v2.sql
-- Purpose:
--   Merge 080A 0-12h dynamic vital burden features into the
--   v1 modeling dataset to create v2.
--
-- Inputs:
--   study_ahf_v4.model_070g_modeling_dataset_v1
--   study_ahf_v4.model_080A_vital_burden_0_12h_v1
--
-- Output:
--   study_ahf_v4.model_080G_modeling_dataset_v2
--
-- Important:
--   080A features are pre-landmark predictors only.
-- ============================================================

drop table if exists study_ahf_v4.model_080G_modeling_dataset_v2 cascade;

create table study_ahf_v4.model_080G_modeling_dataset_v2 as
select
    g.*,

    -- 080A vital burden features
    a.vital_burden_records_0_12h_n,

    a.hr_pair_n,
    a.sbp_pair_n,
    a.mbp_pair_n,
    a.rr_pair_n,
    a.spo2_pair_n,
    a.temp_pair_n,

    a.map_lt65_record_prop,
    a.map_lt60_record_prop,
    a.sbp_lt90_record_prop,
    a.sbp_lt100_record_prop,
    a.hr_gt110_record_prop,
    a.hr_gt120_record_prop,
    a.rr_gt24_record_prop,
    a.rr_gt30_record_prop,
    a.spo2_lt90_record_prop,
    a.temp_lt36_record_prop,
    a.temp_gt38_record_prop,

    a.shock_index_mean,
    a.shock_index_max,
    a.shock_index_min,
    a.shock_index_last,

    a.modified_shock_index_mean,
    a.modified_shock_index_max,
    a.modified_shock_index_min,
    a.modified_shock_index_last,

    a.pulse_pressure_mean,
    a.pulse_pressure_min,
    a.pulse_pressure_max,
    a.pulse_pressure_last,

    a.sbp_slope_per_hour,
    a.mbp_slope_per_hour,
    a.hr_slope_per_hour,
    a.rr_slope_per_hour,
    a.spo2_slope_per_hour,

    a.sbp_slope_n,
    a.mbp_slope_n,
    a.hr_slope_n,
    a.rr_slope_n,
    a.spo2_slope_n,

    a.vital_burden_available_flag

from study_ahf_v4.model_070G_modeling_dataset_v1 g
left join study_ahf_v4.model_080A_vital_burden_0_12h_v1 a
    on g.stay_id = a.stay_id;

create index if not exists idx_model_080g_modeling_dataset_v2_stay
    on study_ahf_v4.model_080G_modeling_dataset_v2 (stay_id);

analyze study_ahf_v4.model_080G_modeling_dataset_v2;

insert into study_ahf_v4.run_manifest (
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
    'study_ahf_v4.model_080G_modeling_dataset_v2' as table_name,
    'sql/03_features/080G_create_modeling_dataset_v2.sql' as sql_file,
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    sum(primary_outcome_flag)::numeric / nullif(count(*), 0) as event_rate,
    '0-12h predictors; 12-60h primary outcome' as time_window,
    '080G_v2' as version_tag,
    'Modeling dataset v2: v1 plus 080A structured dynamic vital burden, shock index, pulse pressure, and trend features.' as notes
from study_ahf_v4.model_080G_modeling_dataset_v2;
