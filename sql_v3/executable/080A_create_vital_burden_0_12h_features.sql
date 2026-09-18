-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/03_features/080A_create_vital_burden_0_12h_features.sql
-- Purpose:
--   Create structured 0-12h vital-sign burden and trend features.
--
-- Main uses:
--   1. Quantify hypotension, tachycardia, tachypnea, and hypoxemia burden.
--   2. Add shock index, modified shock index, and pulse pressure summaries.
--   3. Add simple vital-sign trend slopes during the pre-landmark window.
--
-- Important:
--   This table uses only ICU intime to landmark12_time measurements.
--   Do NOT use post12 variables as predictors.
-- ============================================================

drop table if exists study_ahf_v3.model_080A_vital_burden_0_12h_v1 cascade;

create table study_ahf_v3.model_080A_vital_burden_0_12h_v1 as
with base as (
    select
        subject_id,
        hadm_id,
        stay_id,
        intime,
        landmark12_time,
        primary_outcome_flag
    from study_ahf_v3.model_070g_modeling_dataset_v1
),

vital_raw as (
    select
        b.stay_id,
        v.charttime,
        extract(epoch from (v.charttime - b.intime)) / 3600.0 as hour_from_icu,

        case when v.heart_rate between 20 and 250 then v.heart_rate else null end as hr,
        case when v.sbp between 40 and 300 then v.sbp else null end as sbp,
        case when v.dbp between 20 and 200 then v.dbp else null end as dbp,
        case when v.mbp between 30 and 250 then v.mbp else null end as mbp,
        case when v.resp_rate between 5 and 80 then v.resp_rate else null end as rr,
        case when v.spo2 between 50 and 100 then v.spo2 else null end as spo2,
        case when v.temperature between 25 and 45 then v.temperature else null end as temp

    from base b
    left join mimiciv_derived.vitalsign v
        on b.stay_id = v.stay_id
       and v.charttime >= b.intime
       and v.charttime <  b.landmark12_time
),

paired as (
    select
        *,
        case
            when hr is not null and sbp is not null and sbp > 0
            then hr / sbp
            else null
        end as shock_index,

        case
            when hr is not null and mbp is not null and mbp > 0
            then hr / mbp
            else null
        end as modified_shock_index,

        case
            when sbp is not null and dbp is not null and sbp >= dbp
            then sbp - dbp
            else null
        end as pulse_pressure

    from vital_raw
),

summary as (
    select
        stay_id,

        count(charttime) as vital_records_0_12h_n,

        -- availability
        count(hr) as hr_pair_n,
        count(sbp) as sbp_pair_n,
        count(mbp) as mbp_pair_n,
        count(rr) as rr_pair_n,
        count(spo2) as spo2_pair_n,
        count(temp) as temp_pair_n,

        -- burden proportions
        avg(case when mbp is not null then case when mbp < 65 then 1.0 else 0.0 end else null end) as map_lt65_record_prop,
        avg(case when mbp is not null then case when mbp < 60 then 1.0 else 0.0 end else null end) as map_lt60_record_prop,
        avg(case when sbp is not null then case when sbp < 90 then 1.0 else 0.0 end else null end) as sbp_lt90_record_prop,
        avg(case when sbp is not null then case when sbp < 100 then 1.0 else 0.0 end else null end) as sbp_lt100_record_prop,

        avg(case when hr is not null then case when hr > 110 then 1.0 else 0.0 end else null end) as hr_gt110_record_prop,
        avg(case when hr is not null then case when hr > 120 then 1.0 else 0.0 end else null end) as hr_gt120_record_prop,

        avg(case when rr is not null then case when rr > 24 then 1.0 else 0.0 end else null end) as rr_gt24_record_prop,
        avg(case when rr is not null then case when rr > 30 then 1.0 else 0.0 end else null end) as rr_gt30_record_prop,

        avg(case when spo2 is not null then case when spo2 < 90 then 1.0 else 0.0 end else null end) as spo2_lt90_record_prop,
        avg(case when temp is not null then case when temp < 36 then 1.0 else 0.0 end else null end) as temp_lt36_record_prop,
        avg(case when temp is not null then case when temp > 38 then 1.0 else 0.0 end else null end) as temp_gt38_record_prop,

        -- derived hemodynamics
        avg(shock_index) as shock_index_mean,
        max(shock_index) as shock_index_max,
        min(shock_index) as shock_index_min,

        avg(modified_shock_index) as modified_shock_index_mean,
        max(modified_shock_index) as modified_shock_index_max,
        min(modified_shock_index) as modified_shock_index_min,

        avg(pulse_pressure) as pulse_pressure_mean,
        min(pulse_pressure) as pulse_pressure_min,
        max(pulse_pressure) as pulse_pressure_max,

        -- simple slopes per hour
        regr_slope(sbp, hour_from_icu) filter (where sbp is not null and hour_from_icu is not null) as sbp_slope_per_hour,
        regr_slope(mbp, hour_from_icu) filter (where mbp is not null and hour_from_icu is not null) as mbp_slope_per_hour,
        regr_slope(hr, hour_from_icu) filter (where hr is not null and hour_from_icu is not null) as hr_slope_per_hour,
        regr_slope(rr, hour_from_icu) filter (where rr is not null and hour_from_icu is not null) as rr_slope_per_hour,
        regr_slope(spo2, hour_from_icu) filter (where spo2 is not null and hour_from_icu is not null) as spo2_slope_per_hour,

        -- slope support counts
        count(sbp) filter (where sbp is not null) as sbp_slope_n,
        count(mbp) filter (where mbp is not null) as mbp_slope_n,
        count(hr) filter (where hr is not null) as hr_slope_n,
        count(rr) filter (where rr is not null) as rr_slope_n,
        count(spo2) filter (where spo2 is not null) as spo2_slope_n

    from paired
    group by stay_id
),

last_values as (
    select
        stay_id,
        (array_agg(shock_index order by charttime desc) filter (where shock_index is not null))[1] as shock_index_last,
        (array_agg(modified_shock_index order by charttime desc) filter (where modified_shock_index is not null))[1] as modified_shock_index_last,
        (array_agg(pulse_pressure order by charttime desc) filter (where pulse_pressure is not null))[1] as pulse_pressure_last
    from paired
    group by stay_id
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.primary_outcome_flag,

    coalesce(s.vital_records_0_12h_n, 0) as vital_burden_records_0_12h_n,

    s.hr_pair_n,
    s.sbp_pair_n,
    s.mbp_pair_n,
    s.rr_pair_n,
    s.spo2_pair_n,
    s.temp_pair_n,

    s.map_lt65_record_prop,
    s.map_lt60_record_prop,
    s.sbp_lt90_record_prop,
    s.sbp_lt100_record_prop,
    s.hr_gt110_record_prop,
    s.hr_gt120_record_prop,
    s.rr_gt24_record_prop,
    s.rr_gt30_record_prop,
    s.spo2_lt90_record_prop,
    s.temp_lt36_record_prop,
    s.temp_gt38_record_prop,

    s.shock_index_mean,
    s.shock_index_max,
    s.shock_index_min,
    l.shock_index_last,

    s.modified_shock_index_mean,
    s.modified_shock_index_max,
    s.modified_shock_index_min,
    l.modified_shock_index_last,

    s.pulse_pressure_mean,
    s.pulse_pressure_min,
    s.pulse_pressure_max,
    l.pulse_pressure_last,

    s.sbp_slope_per_hour,
    s.mbp_slope_per_hour,
    s.hr_slope_per_hour,
    s.rr_slope_per_hour,
    s.spo2_slope_per_hour,

    s.sbp_slope_n,
    s.mbp_slope_n,
    s.hr_slope_n,
    s.rr_slope_n,
    s.spo2_slope_n,

    case when coalesce(s.vital_records_0_12h_n, 0) > 0 then 1 else 0 end as vital_burden_available_flag

from base b
left join summary s
    on b.stay_id = s.stay_id
left join last_values l
    on b.stay_id = l.stay_id;

create index if not exists idx_model_080a_vital_burden_stay
    on study_ahf_v3.model_080A_vital_burden_0_12h_v1 (stay_id);

analyze study_ahf_v3.model_080A_vital_burden_0_12h_v1;

insert into study_ahf_v3.run_manifest (
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
    'study_ahf_v3.model_080A_vital_burden_0_12h_v1' as table_name,
    'sql/03_features/080A_create_vital_burden_0_12h_features.sql' as sql_file,
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    sum(primary_outcome_flag)::numeric / nullif(count(*), 0) as event_rate,
    '0-12h after ICU admission; predictors only' as time_window,
    '080A_v1' as version_tag,
    'Structured vital burden, shock index, pulse pressure, and vital trend features from the 0-12h pre-landmark window.' as notes
from study_ahf_v3.model_080A_vital_burden_0_12h_v1;
