-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/audits/090D_export_compact_feature_qc_v33.sql
-- Purpose:
--   Export QC reports and modeling inputs for 090A-C.
-- ============================================================

\pset format csv
\pset tuples_only off
\pset footer off

\o project_control/runs/20260828_v3_3_compact_features/reports/090_QC1_base_state_counts.csv
select
    final_state,
    event_type,
    early_sepsis12_main_flag,
    count(*) as n_stays,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct_all
from study_ahf_v3_2.model_090A_modeling_base_v33_v1
group by final_state, event_type, early_sepsis12_main_flag
order by final_state, event_type, early_sepsis12_main_flag;
\o

\o project_control/runs/20260828_v3_3_compact_features/reports/090_QC2_uniqueness_and_join.csv
with
base as (
    select
        count(*) as n_rows,
        count(distinct subject_id) as n_subjects,
        count(distinct hadm_id) as n_hadm,
        count(distinct stay_id) as n_stays,
        count(*) - count(distinct stay_id) as duplicate_stay_rows
    from study_ahf_v3_2.model_090A_modeling_base_v33_v1
),
predictors as (
    select
        count(*) as n_rows,
        count(distinct subject_id) as n_subjects,
        count(distinct hadm_id) as n_hadm,
        count(distinct stay_id) as n_stays,
        count(*) - count(distinct stay_id) as duplicate_stay_rows
    from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
),
finegray as (
    select
        count(*) as n_rows,
        count(distinct subject_id) as n_subjects,
        count(distinct hadm_id) as n_hadm,
        count(distinct stay_id) as n_stays,
        count(*) - count(distinct stay_id) as duplicate_stay_rows
    from study_ahf_v3_2.model_090C_finegray_input_v33_v1
),
pp as (
    select
        count(*) as n_rows,
        count(distinct subject_id) as n_subjects,
        count(distinct hadm_id) as n_hadm,
        count(distinct stay_id) as n_stays,
        count(*) - count(distinct stay_id) as duplicate_stay_rows
    from study_ahf_v3_2.model_097_person_period_v33_v2
)
select '090A_base' as object_name, * from base
union all select '090B_predictors', * from predictors
union all select '090C_finegray_input', * from finegray
union all select '097_person_period', * from pp
order by object_name;
\o

\o project_control/runs/20260828_v3_3_compact_features/reports/090_QC3_predictor_blacklist_scan.csv
select
    column_name,
    'blacklist_pattern_match' as issue
from information_schema.columns
where table_schema = 'study_ahf_v3_2'
  and table_name = 'model_090b_compact_predictors_v33_v1'
  and column_name not in ('subject_id', 'hadm_id', 'stay_id')
  and column_name ~* '(final|event|death|deathtime|compete|censor|outcome|label|icd|ahf|sepsis|sofa|infection|pre12_overt|complete60|landmark|window60|intime|outtime|time)'
order by column_name;
\o

\o project_control/runs/20260828_v3_3_compact_features/reports/090_QC4_predictor_manifest_count.csv
with manifest as (
    select count(*) as n_manifest_predictors
    from study_ahf_v3_2.model_090B_predictor_manifest_v33_v1
    where primary_model_flag = 1
),
columns as (
    select count(*) as n_predictor_columns
    from information_schema.columns
    where table_schema = 'study_ahf_v3_2'
      and table_name = 'model_090b_compact_predictors_v33_v1'
      and column_name not in ('subject_id', 'hadm_id', 'stay_id')
)
select
    m.n_manifest_predictors,
    c.n_predictor_columns,
    case when m.n_manifest_predictors = c.n_predictor_columns then 1 else 0 end
        as manifest_matches_table_flag
from manifest m cross join columns c;
\o

\o project_control/runs/20260828_v3_3_compact_features/reports/090_QC5_missingness_by_predictor.csv
with long_missing as (
    select 'age' as predictor_name, count(*) filter (where age is null) as n_missing from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'female', count(*) filter (where female is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'first_unit_micu_flag', count(*) filter (where first_unit_micu_flag is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'first_unit_ccu_cicu_flag', count(*) filter (where first_unit_ccu_cicu_flag is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'first_unit_sicu_flag', count(*) filter (where first_unit_sicu_flag is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'first_unit_cvicu_flag', count(*) filter (where first_unit_cvicu_flag is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'hr_mean', count(*) filter (where hr_mean is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'hr_max', count(*) filter (where hr_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'mbp_mean', count(*) filter (where mbp_mean is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'mbp_min', count(*) filter (where mbp_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'sbp_min', count(*) filter (where sbp_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'dbp_min', count(*) filter (where dbp_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'rr_mean', count(*) filter (where rr_mean is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'rr_max', count(*) filter (where rr_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'spo2_mean', count(*) filter (where spo2_mean is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'spo2_min', count(*) filter (where spo2_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'temp_max', count(*) filter (where temp_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'map_lt65_record_prop', count(*) filter (where map_lt65_record_prop is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'sbp_lt90_record_prop', count(*) filter (where sbp_lt90_record_prop is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'hr_gt110_record_prop', count(*) filter (where hr_gt110_record_prop is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'rr_gt24_record_prop', count(*) filter (where rr_gt24_record_prop is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'spo2_lt90_record_prop', count(*) filter (where spo2_lt90_record_prop is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'shock_index_max', count(*) filter (where shock_index_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'modified_shock_index_max', count(*) filter (where modified_shock_index_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'pulse_pressure_min', count(*) filter (where pulse_pressure_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'mbp_slope_per_hour', count(*) filter (where mbp_slope_per_hour is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'lactate_max', count(*) filter (where lactate_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'lactate_delta', count(*) filter (where lactate_delta is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'ph_min', count(*) filter (where ph_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'baseexcess_min', count(*) filter (where baseexcess_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'creatinine_max', count(*) filter (where creatinine_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'creatinine_delta', count(*) filter (where creatinine_delta is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'bun_max', count(*) filter (where bun_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'sodium_min', count(*) filter (where sodium_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'sodium_max', count(*) filter (where sodium_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'potassium_min', count(*) filter (where potassium_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'potassium_max', count(*) filter (where potassium_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'chem_bicarbonate_min', count(*) filter (where chem_bicarbonate_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'wbc_max', count(*) filter (where wbc_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'hemoglobin_min', count(*) filter (where hemoglobin_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'platelet_min', count(*) filter (where platelet_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'inr_max', count(*) filter (where inr_max is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'urineoutput_0_12h_total_ml', count(*) filter (where urineoutput_0_12h_total_ml is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'gcs_min', count(*) filter (where gcs_min is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
    union all select 'advanced_respiratory_support_0_12h_flag', count(*) filter (where advanced_respiratory_support_0_12h_flag is null) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
),
denom as (
    select count(*) as n_total
    from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
)
select
    m.predictor_name,
    f.feature_group,
    m.n_missing,
    d.n_total,
    round(m.n_missing * 100.0 / d.n_total, 2) as pct_missing
from long_missing m
left join study_ahf_v3_2.model_090B_predictor_manifest_v33_v1 f
    on m.predictor_name = f.predictor_name
cross join denom d
order by pct_missing desc, predictor_name;
\o

\o project_control/runs/20260828_v3_3_compact_features/reports/090_QC6_three_table_connection.csv
with pp_terminal as (
    select
        stay_id,
        sum(event_period_flag) as n_event_terminal_rows,
        sum(compete_period_flag) as n_compete_terminal_rows,
        sum(censor_period_flag) as n_censor_terminal_rows,
        count(*) as n_period_rows
    from study_ahf_v3_2.model_097_person_period_v33_v2
    group by stay_id
),
joined as (
    select
        b.stay_id,
        b.final_state,
        b.event_flag,
        b.compete_flag,
        b.admin_censor_flag,
        case when p.stay_id is not null then 1 else 0 end as has_predictors,
        case when pp.stay_id is not null then 1 else 0 end as has_person_period,
        pp.n_event_terminal_rows,
        pp.n_compete_terminal_rows,
        pp.n_censor_terminal_rows,
        pp.n_period_rows
    from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
    left join study_ahf_v3_2.model_090B_compact_predictors_v33_v1 p
        on b.stay_id = p.stay_id
    left join pp_terminal pp
        on b.stay_id = pp.stay_id
)
select
    final_state,
    count(*) as n_stays,
    sum(has_predictors) as n_with_predictors,
    sum(has_person_period) as n_with_person_period,
    sum(coalesce(n_event_terminal_rows, 0)) as n_event_terminal_rows,
    sum(coalesce(n_compete_terminal_rows, 0)) as n_compete_terminal_rows,
    sum(coalesce(n_censor_terminal_rows, 0)) as n_censor_terminal_rows,
    min(n_period_rows) as min_period_rows,
    max(n_period_rows) as max_period_rows
from joined
group by final_state
order by final_state;
\o

\o project_control/runs/20260828_v3_3_compact_features/reports/090_predictor_manifest.csv
select *
from study_ahf_v3_2.model_090B_predictor_manifest_v33_v1
order by feature_group, predictor_name;
\o

\o project_control/runs/20260828_v3_3_compact_features/data/090C_finegray_input_v33.csv
select *
from study_ahf_v3_2.model_090C_finegray_input_v33_v1
order by stay_id;
\o

\o project_control/runs/20260828_v3_3_compact_features/data/090B_compact_predictors_v33.csv
select *
from study_ahf_v3_2.model_090B_compact_predictors_v33_v1
order by stay_id;
\o

\pset format aligned
\pset footer on
