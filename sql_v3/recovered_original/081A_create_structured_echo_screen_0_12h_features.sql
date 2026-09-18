-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/081A_create_structured_echo_screen_0_12h_features.sql
-- Purpose:
--   Create a structured echo / LVEF / CO / CI availability table
--   using only currently installed structured MIMIC-IV tables.
--
-- Important:
--   1. This is NOT a full echocardiography text extraction table.
--   2. The current local DB has no mimiciv_note schema or echo report
--      text table, so LVEF / RV dysfunction from reports cannot be
--      extracted here.
--   3. All candidate predictors are restricted to time before
--      landmark12_time. Do NOT use post12 variables as predictors.
-- ============================================================

drop table if exists study_ahf.model_081A_structured_echo_screen_0_12h_v1 cascade;

create table study_ahf.model_081A_structured_echo_screen_0_12h_v1 as
with base as (
    select
        subject_id,
        hadm_id,
        stay_id,
        intime,
        landmark12_time,
        primary_outcome_flag
    from study_ahf.model_080G_modeling_dataset_v2
),

-- ------------------------------------------------------------
-- Echo procedure occurrence, not echo result text.
-- TTE itemid 225432; TEE itemid 221255.
-- A -24h to landmark lookback is kept for feasibility auditing
-- because ICU procedures can be charted around transfer time.
-- ------------------------------------------------------------
echo_procedure_rows as (
    select
        b.stay_id,
        pe.itemid,
        pe.starttime,
        pe.endtime,
        extract(epoch from (pe.starttime - b.intime)) / 3600.0 as hour_from_icu
    from base b
    join mimiciv_icu.procedureevents pe
        on b.stay_id = pe.stay_id
       and pe.itemid in (221255, 225432)
       and pe.starttime < b.landmark12_time
       and coalesce(pe.endtime, pe.starttime) >= b.intime - interval '24 hour'
),

echo_procedure_summary as (
    select
        stay_id,

        count(*) as echo_procedure_pre12_n,
        count(*) filter (where itemid = 225432) as tte_procedure_pre12_n,
        count(*) filter (where itemid = 221255) as tee_procedure_pre12_n,

        max(case when itemid = 225432 then 1 else 0 end) as tte_procedure_pre12_flag,
        max(case when itemid = 221255 then 1 else 0 end) as tee_procedure_pre12_flag,
        1 as echo_any_procedure_pre12_flag,

        max(case when hour_from_icu >= 0 and hour_from_icu < 12 then 1 else 0 end)
            as echo_any_procedure_0_12h_flag,
        max(case when itemid = 225432 and hour_from_icu >= 0 and hour_from_icu < 12 then 1 else 0 end)
            as tte_procedure_0_12h_flag,
        max(case when itemid = 221255 and hour_from_icu >= 0 and hour_from_icu < 12 then 1 else 0 end)
            as tee_procedure_0_12h_flag,

        min(starttime) as first_echo_procedure_pre12_time,
        max(starttime) as last_echo_procedure_pre12_time,
        min(hour_from_icu) as first_echo_procedure_hour_from_icu,
        max(hour_from_icu) as last_echo_procedure_hour_from_icu

    from echo_procedure_rows
    group by stay_id
),

-- ------------------------------------------------------------
-- Structured APACHE ejection fraction if present.
-- In the current local DB audit, d_items has itemid 227008 but
-- chartevents contains no rows; keep logic for reproducibility.
-- ------------------------------------------------------------
lvef_rows as (
    select
        b.stay_id,
        ce.charttime,
        extract(epoch from (ce.charttime - b.intime)) / 3600.0 as hour_from_icu,
        ce.valuenum as lvef_value
    from base b
    join mimiciv_icu.chartevents ce
        on b.stay_id = ce.stay_id
       and ce.itemid = 227008
       and ce.charttime >= b.intime - interval '7 day'
       and ce.charttime <  b.landmark12_time
       and ce.valuenum between 5 and 90
),

lvef_summary as (
    select
        stay_id,
        count(*) as structured_lvef_pre12_n,
        min(lvef_value) as structured_lvef_pre12_min,
        max(lvef_value) as structured_lvef_pre12_max,
        avg(lvef_value) as structured_lvef_pre12_mean,
        min(charttime) as first_structured_lvef_pre12_time,
        max(charttime) as last_structured_lvef_pre12_time,
        min(hour_from_icu) as first_structured_lvef_hour_from_icu,
        max(hour_from_icu) as last_structured_lvef_hour_from_icu
    from lvef_rows
    group by stay_id
),

lvef_last as (
    select distinct on (stay_id)
        stay_id,
        lvef_value as structured_lvef_pre12_last
    from lvef_rows
    order by stay_id, charttime desc
),

-- ------------------------------------------------------------
-- Sparse invasive/NICOM cardiac output and cardiac index values.
-- These are hemodynamic measurements, not echo LVEF.
-- ------------------------------------------------------------
co_ci_rows as (
    select
        b.stay_id,
        ce.itemid,
        ce.charttime,
        extract(epoch from (ce.charttime - b.intime)) / 3600.0 as hour_from_icu,
        ce.valuenum
    from base b
    join mimiciv_icu.chartevents ce
        on b.stay_id = ce.stay_id
       and ce.itemid in (220088, 224842, 228368, 228369)
       and ce.charttime >= b.intime
       and ce.charttime <  b.landmark12_time
       and ce.valuenum is not null
),

co_ci_clean as (
    select
        stay_id,
        itemid,
        charttime,
        hour_from_icu,
        case
            when itemid in (220088, 224842, 228369)
             and valuenum between 0.5 and 20
            then valuenum
            else null
        end as cardiac_output_value,
        case
            when itemid = 228368
             and valuenum between 0.5 and 10
            then valuenum
            else null
        end as cardiac_index_value
    from co_ci_rows
),

co_ci_summary as (
    select
        stay_id,

        count(cardiac_output_value) as cardiac_output_0_12h_n,
        min(cardiac_output_value) as cardiac_output_0_12h_min,
        max(cardiac_output_value) as cardiac_output_0_12h_max,
        avg(cardiac_output_value) as cardiac_output_0_12h_mean,

        count(cardiac_index_value) as cardiac_index_0_12h_n,
        min(cardiac_index_value) as cardiac_index_0_12h_min,
        max(cardiac_index_value) as cardiac_index_0_12h_max,
        avg(cardiac_index_value) as cardiac_index_0_12h_mean

    from co_ci_clean
    group by stay_id
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.primary_outcome_flag,

    coalesce(e.echo_procedure_pre12_n, 0) as echo_procedure_pre12_n,
    coalesce(e.tte_procedure_pre12_n, 0) as tte_procedure_pre12_n,
    coalesce(e.tee_procedure_pre12_n, 0) as tee_procedure_pre12_n,
    coalesce(e.echo_any_procedure_pre12_flag, 0) as echo_any_procedure_pre12_flag,
    coalesce(e.tte_procedure_pre12_flag, 0) as tte_procedure_pre12_flag,
    coalesce(e.tee_procedure_pre12_flag, 0) as tee_procedure_pre12_flag,
    coalesce(e.echo_any_procedure_0_12h_flag, 0) as echo_any_procedure_0_12h_flag,
    coalesce(e.tte_procedure_0_12h_flag, 0) as tte_procedure_0_12h_flag,
    coalesce(e.tee_procedure_0_12h_flag, 0) as tee_procedure_0_12h_flag,
    e.first_echo_procedure_pre12_time,
    e.last_echo_procedure_pre12_time,
    e.first_echo_procedure_hour_from_icu,
    e.last_echo_procedure_hour_from_icu,

    coalesce(l.structured_lvef_pre12_n, 0) as structured_lvef_pre12_n,
    case when coalesce(l.structured_lvef_pre12_n, 0) > 0 then 1 else 0 end
        as structured_lvef_pre12_available_flag,
    l.structured_lvef_pre12_min,
    l.structured_lvef_pre12_max,
    l.structured_lvef_pre12_mean,
    ll.structured_lvef_pre12_last,
    case when ll.structured_lvef_pre12_last < 40 then 1 else 0 end
        as structured_lvef_last_lt40_flag,
    case when ll.structured_lvef_pre12_last < 50 then 1 else 0 end
        as structured_lvef_last_lt50_flag,
    l.first_structured_lvef_pre12_time,
    l.last_structured_lvef_pre12_time,
    l.first_structured_lvef_hour_from_icu,
    l.last_structured_lvef_hour_from_icu,

    coalesce(c.cardiac_output_0_12h_n, 0) as cardiac_output_0_12h_n,
    case when coalesce(c.cardiac_output_0_12h_n, 0) > 0 then 1 else 0 end
        as cardiac_output_0_12h_available_flag,
    c.cardiac_output_0_12h_min,
    c.cardiac_output_0_12h_max,
    c.cardiac_output_0_12h_mean,

    coalesce(c.cardiac_index_0_12h_n, 0) as cardiac_index_0_12h_n,
    case when coalesce(c.cardiac_index_0_12h_n, 0) > 0 then 1 else 0 end
        as cardiac_index_0_12h_available_flag,
    c.cardiac_index_0_12h_min,
    c.cardiac_index_0_12h_max,
    c.cardiac_index_0_12h_mean

from base b
left join echo_procedure_summary e
    on b.stay_id = e.stay_id
left join lvef_summary l
    on b.stay_id = l.stay_id
left join lvef_last ll
    on b.stay_id = ll.stay_id
left join co_ci_summary c
    on b.stay_id = c.stay_id;
