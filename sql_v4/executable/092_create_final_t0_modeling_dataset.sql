-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v4/executable/092_create_final_t0_modeling_dataset.sql
-- Purpose:
--   Create the strict T0-compatible modeling dataset by filtering
--   the already-built 0-12h feature dataset to the final broad T0
--   AHF + early-sepsis cohort.
--
-- This is a feasibility / exploratory modeling dataset. The final
-- broad T0 cohort is expected to have few events, so it must not be
-- interpreted as a stable production model without additional data.
-- ============================================================

drop table if exists study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1 cascade;

create table study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1 as
select
    g.*
from study_ahf_v4.model_080g_modeling_dataset_v2 g
inner join study_ahf_v4.audit_092_final_t0_definition_v1 a
    on g.stay_id = a.stay_id
where a.final_t0_ahf_sepsis_broad_flag = 1;

-- Remove variables derived from final ICD/Charlson data or cohort
-- confirmation rules that cannot be treated as real-time predictors.
do $$
declare
    c text;
begin
    for c in
        select column_name
        from information_schema.columns
        where table_schema = 'study_ahf_v4'
          and table_name = 'model_092_t0_ahf_sepsis_strict_v1'
          and (
              lower(column_name) like 'hf_icd%'
           or lower(column_name) like 'charlson%'
           or lower(column_name) like 'acute_hf%'
           or column_name in (
              'iv_loop_rx_early12_flag',
              'ntprobnp_ge300_early12_flag',
              'ahf_evidence_score_primary_12h'
           )
          )
    loop
        execute format(
            'alter table study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1 drop column %I',
            c
        );
    end loop;
end $$;

create index if not exists idx_model_092_t0_strict_stay
    on study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1 (stay_id);

analyze study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1;

-- QC1: row and outcome consistency.
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2) as event_rate_pct
from study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1;

-- QC2: verify that forbidden real-time leakage columns are absent.
select column_name
from information_schema.columns
where table_schema = 'study_ahf_v4'
  and table_name = 'model_092_t0_ahf_sepsis_strict_v1'
  and (
        lower(column_name) like '%hf_icd%'
     or lower(column_name) like '%charlson%'
  )
order by column_name;

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
    'study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1',
    'sql_v4/executable/092_create_final_t0_modeling_dataset.sql',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    sum(primary_outcome_flag),
    sum(primary_outcome_flag)::numeric / nullif(count(*), 0),
    '0-12h predictors; 12-60h primary outcome',
    '092_t0_strict_v1',
    'Strict T0-compatible feasibility dataset: AHF time evidence pre-T0, infection suspected pre-T0, Sepsis-3 operational confirmation by T12, and no pre12 overt-CS proxy.'
from study_ahf_v4.model_092_t0_ahf_sepsis_strict_v1;
