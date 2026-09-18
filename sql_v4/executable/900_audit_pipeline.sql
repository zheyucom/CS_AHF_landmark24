drop table if exists study_ahf_v4.pipeline_audit;

create table study_ahf_v4.pipeline_audit (
    step_order integer primary key,
    table_name text not null,
    n_rows bigint not null,
    n_subjects bigint,
    n_hadm bigint,
    n_stay bigint,
    n_events bigint,
    audited_at timestamp not null default current_timestamp
);

do $$
declare
    item record;
    event_sql text;
begin
    for item in
        select *
        from (values
            (10, 'cohort_010_adult_first_icu_v1', null),
            (20, 'cohort_020_hf_icd_candidate_v1', null),
            (61, 'cohort_061a_ahf_evidence_early_window_12h_v1', null),
            (62, 'cohort_061b_ahf_strict_12h_v1', null),
            (63, 'outcome_061c_pre12_overt_cs_flags_v1', 'pre12_overt_cs_main_flag'),
            (64, 'cohort_061d_landmark12_riskset_main_v1', null),
            (65, 'outcome_061e_post12_overt_cs_future48h_main_v1', 'post12_overt_cs_main_flag'),
            (66, 'outcome_062a_post12_outcome_with_earlysepsis12_v1', 'early_sepsis_admission_present_flag'),
            (67, 'outcome_062b_ahf_earlysepsis12_post12_future48_main_v1', 'post12_overt_cs_main_flag'),
            (68, 'outcome_064_primary_hd_deterioration_v1', 'primary_outcome_flag'),
            (70, 'model_070a_base_index_v1', 'primary_outcome_flag'),
            (71, 'model_070c_static_clinical_features_v1', null),
            (72, 'model_070d_vitals_0_12h_clean_v1', null),
            (73, 'model_070e_labs_0_12h_v1', null),
            (74, 'model_070f_support_0_12h_v1', null),
            (75, 'model_070g_modeling_dataset_v1', 'primary_outcome_flag'),
            (79, 'audit_079_event_timing_components_v1', 'primary_outcome_flag'),
            (80, 'model_080a_vital_burden_0_12h_v1', 'primary_outcome_flag'),
            (81, 'model_080g_modeling_dataset_v2', 'primary_outcome_flag'),
            (82, 'model_081a_structured_echo_screen_0_12h_v1', 'primary_outcome_flag')
        ) as x(step_order, table_name, event_column)
    loop
        event_sql := case
            when item.event_column is null then 'null::bigint'
            else format('sum(%I)::bigint', item.event_column)
        end;

        execute format(
            'insert into study_ahf_v4.pipeline_audit '
            || '(step_order, table_name, n_rows, n_subjects, n_hadm, n_stay, n_events) '
            || 'select %s, %L, count(*), count(distinct subject_id), '
            || 'count(distinct hadm_id), count(distinct stay_id), %s '
            || 'from study_ahf_v4.%I',
            item.step_order, item.table_name, event_sql, item.table_name
        );
    end loop;
end $$;

delete from study_ahf_v4.run_manifest
where version_tag = 'v4_admission_present_20260825';

insert into study_ahf_v4.run_manifest (
    table_name, sql_file, n_rows, n_subjects, n_hadm, n_stay,
    n_events, event_rate, version_tag, notes
)
select
    'study_ahf_v4.' || table_name,
    'sql_v3/executable',
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    n_events,
    case when n_events is not null and n_rows > 0
         then n_events::numeric / n_rows else null end,
    'v4_admission_present_20260825',
    'Rebuilt from archived Navicat SQL; see project_control run manifest for source hashes.'
from study_ahf_v4.pipeline_audit
order by step_order;

select * from study_ahf_v4.pipeline_audit order by step_order;
