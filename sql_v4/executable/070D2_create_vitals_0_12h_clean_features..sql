-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/070D2_create_vitals_0_12h_clean_features.sql
-- Purpose:
--   Create cleaned 0-12h vital sign features.
--
-- Reason:
--   Raw official vitalsign table still contains implausible extremes
--   such as SBP=7, MAP=1, RR=1, SpO2=29.
--
-- Strategy:
--   1. Apply conservative physiologic plausibility filters.
--   2. Aggregate cleaned values only.
--   3. Use first / last / min / max / mean / count / delta.
--   4. Keep availability flags.
--
-- Predictor window:
--   ICU intime <= charttime < ICU intime + 12h.
-- ============================================================

drop table if exists study_ahf_v4.model_070D_vitals_0_12h_clean_v1 cascade;

create table study_ahf_v4.model_070D_vitals_0_12h_clean_v1 as
with base as (
    select *
    from study_ahf_v4.model_070A_base_index_v1
),

vitals_raw as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        v.charttime,

        -- Conservative cleaning ranges.
        -- Values outside these ranges are treated as missing for modeling.
        case when v.heart_rate between 20 and 250 then v.heart_rate else null end as heart_rate,
        case when v.sbp        between 40 and 300 then v.sbp        else null end as sbp,
        case when v.dbp        between 20 and 200 then v.dbp        else null end as dbp,
        case when v.mbp        between 30 and 250 then v.mbp        else null end as mbp,
        case when v.resp_rate  between 5  and 60  then v.resp_rate  else null end as resp_rate,
        case when v.temperature between 30 and 43 then v.temperature else null end as temperature,
        case when v.spo2       between 50 and 100 then v.spo2       else null end as spo2,
        case when v.glucose    between 20 and 1000 then v.glucose   else null end as glucose

    from base b
    left join mimiciv_derived.vitalsign v
        on b.stay_id = v.stay_id
       and v.charttime >= b.intime
       and v.charttime <  b.landmark12_time
),

vitals_summary as (
    select
        stay_id,

        count(heart_rate) as hr_n,
        avg(heart_rate) as hr_mean,
        min(heart_rate) as hr_min,
        max(heart_rate) as hr_max,

        count(sbp) as sbp_n,
        avg(sbp) as sbp_mean,
        min(sbp) as sbp_min,
        max(sbp) as sbp_max,

        count(dbp) as dbp_n,
        avg(dbp) as dbp_mean,
        min(dbp) as dbp_min,
        max(dbp) as dbp_max,

        count(mbp) as mbp_n,
        avg(mbp) as mbp_mean,
        min(mbp) as mbp_min,
        max(mbp) as mbp_max,

        count(resp_rate) as rr_n,
        avg(resp_rate) as rr_mean,
        min(resp_rate) as rr_min,
        max(resp_rate) as rr_max,

        count(temperature) as temp_n,
        avg(temperature) as temp_mean,
        min(temperature) as temp_min,
        max(temperature) as temp_max,

        count(spo2) as spo2_n,
        avg(spo2) as spo2_mean,
        min(spo2) as spo2_min,
        max(spo2) as spo2_max,

        count(glucose) as vital_glucose_n,
        avg(glucose) as vital_glucose_mean,
        min(glucose) as vital_glucose_min,
        max(glucose) as vital_glucose_max

    from vitals_raw
    group by stay_id
),

first_last as (
    select
        stay_id,

        max(first_value) filter (where var_name = 'hr') as hr_first,
        max(last_value)  filter (where var_name = 'hr') as hr_last,

        max(first_value) filter (where var_name = 'sbp') as sbp_first,
        max(last_value)  filter (where var_name = 'sbp') as sbp_last,

        max(first_value) filter (where var_name = 'mbp') as mbp_first,
        max(last_value)  filter (where var_name = 'mbp') as mbp_last,

        max(first_value) filter (where var_name = 'rr') as rr_first,
        max(last_value)  filter (where var_name = 'rr') as rr_last,

        max(first_value) filter (where var_name = 'temp') as temp_first,
        max(last_value)  filter (where var_name = 'temp') as temp_last,

        max(first_value) filter (where var_name = 'spo2') as spo2_first,
        max(last_value)  filter (where var_name = 'spo2') as spo2_last

    from (
        select stay_id, 'hr' as var_name, first_value, last_value
        from (
            select
                stay_id,
                heart_rate,
                first_value(heart_rate) over (
                    partition by stay_id
                    order by charttime
                    rows between unbounded preceding and unbounded following
                ) as first_value,
                first_value(heart_rate) over (
                    partition by stay_id
                    order by charttime desc
                    rows between unbounded preceding and unbounded following
                ) as last_value,
                row_number() over (partition by stay_id order by charttime) as rn
            from vitals_raw
            where heart_rate is not null
        ) x
        where rn = 1

        union all

        select stay_id, 'sbp', first_value, last_value
        from (
            select
                stay_id,
                sbp,
                first_value(sbp) over (
                    partition by stay_id
                    order by charttime
                    rows between unbounded preceding and unbounded following
                ) as first_value,
                first_value(sbp) over (
                    partition by stay_id
                    order by charttime desc
                    rows between unbounded preceding and unbounded following
                ) as last_value,
                row_number() over (partition by stay_id order by charttime) as rn
            from vitals_raw
            where sbp is not null
        ) x
        where rn = 1

        union all

        select stay_id, 'mbp', first_value, last_value
        from (
            select
                stay_id,
                mbp,
                first_value(mbp) over (
                    partition by stay_id
                    order by charttime
                    rows between unbounded preceding and unbounded following
                ) as first_value,
                first_value(mbp) over (
                    partition by stay_id
                    order by charttime desc
                    rows between unbounded preceding and unbounded following
                ) as last_value,
                row_number() over (partition by stay_id order by charttime) as rn
            from vitals_raw
            where mbp is not null
        ) x
        where rn = 1

        union all

        select stay_id, 'rr', first_value, last_value
        from (
            select
                stay_id,
                resp_rate,
                first_value(resp_rate) over (
                    partition by stay_id
                    order by charttime
                    rows between unbounded preceding and unbounded following
                ) as first_value,
                first_value(resp_rate) over (
                    partition by stay_id
                    order by charttime desc
                    rows between unbounded preceding and unbounded following
                ) as last_value,
                row_number() over (partition by stay_id order by charttime) as rn
            from vitals_raw
            where resp_rate is not null
        ) x
        where rn = 1

        union all

        select stay_id, 'temp', first_value, last_value
        from (
            select
                stay_id,
                temperature,
                first_value(temperature) over (
                    partition by stay_id
                    order by charttime
                    rows between unbounded preceding and unbounded following
                ) as first_value,
                first_value(temperature) over (
                    partition by stay_id
                    order by charttime desc
                    rows between unbounded preceding and unbounded following
                ) as last_value,
                row_number() over (partition by stay_id order by charttime) as rn
            from vitals_raw
            where temperature is not null
        ) x
        where rn = 1

        union all

        select stay_id, 'spo2', first_value, last_value
        from (
            select
                stay_id,
                spo2,
                first_value(spo2) over (
                    partition by stay_id
                    order by charttime
                    rows between unbounded preceding and unbounded following
                ) as first_value,
                first_value(spo2) over (
                    partition by stay_id
                    order by charttime desc
                    rows between unbounded preceding and unbounded following
                ) as last_value,
                row_number() over (partition by stay_id order by charttime) as rn
            from vitals_raw
            where spo2 is not null
        ) x
        where rn = 1
    ) z
    group by stay_id
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.primary_outcome_flag,

    s.hr_n,
    f.hr_first,
    f.hr_last,
    s.hr_mean,
    s.hr_min,
    s.hr_max,
    f.hr_last - f.hr_first as hr_delta,

    s.sbp_n,
    f.sbp_first,
    f.sbp_last,
    s.sbp_mean,
    s.sbp_min,
    s.sbp_max,
    f.sbp_last - f.sbp_first as sbp_delta,

    s.dbp_n,
    s.dbp_mean,
    s.dbp_min,
    s.dbp_max,

    s.mbp_n,
    f.mbp_first,
    f.mbp_last,
    s.mbp_mean,
    s.mbp_min,
    s.mbp_max,
    f.mbp_last - f.mbp_first as mbp_delta,

    s.rr_n,
    f.rr_first,
    f.rr_last,
    s.rr_mean,
    s.rr_min,
    s.rr_max,
    f.rr_last - f.rr_first as rr_delta,

    s.temp_n,
    f.temp_first,
    f.temp_last,
    s.temp_mean,
    s.temp_min,
    s.temp_max,
    f.temp_last - f.temp_first as temp_delta,

    s.spo2_n,
    f.spo2_first,
    f.spo2_last,
    s.spo2_mean,
    s.spo2_min,
    s.spo2_max,
    f.spo2_last - f.spo2_first as spo2_delta,

    s.vital_glucose_n,
    s.vital_glucose_mean,
    s.vital_glucose_min,
    s.vital_glucose_max,

    case when s.hr_n > 0 then 1 else 0 end as hr_available_flag,
    case when s.sbp_n > 0 then 1 else 0 end as sbp_available_flag,
    case when s.mbp_n > 0 then 1 else 0 end as mbp_available_flag,
    case when s.rr_n > 0 then 1 else 0 end as rr_available_flag,
    case when s.temp_n > 0 then 1 else 0 end as temp_available_flag,
    case when s.spo2_n > 0 then 1 else 0 end as spo2_available_flag

from base b
left join vitals_summary s
    on b.stay_id = s.stay_id
left join first_last f
    on b.stay_id = f.stay_id;
		
		
		
-- 		070D2 QC1：clean 表总体
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf_v4.model_070D_vitals_0_12h_clean_v1;




-- 070D2 QC2：clean 后可用率
select
    count(*) as n_total,

    sum(hr_available_flag) as n_hr_available,
    round(sum(hr_available_flag) * 100.0 / count(*), 2) as pct_hr_available,

    sum(sbp_available_flag) as n_sbp_available,
    round(sum(sbp_available_flag) * 100.0 / count(*), 2) as pct_sbp_available,

    sum(mbp_available_flag) as n_mbp_available,
    round(sum(mbp_available_flag) * 100.0 / count(*), 2) as pct_mbp_available,

    sum(rr_available_flag) as n_rr_available,
    round(sum(rr_available_flag) * 100.0 / count(*), 2) as pct_rr_available,

    sum(temp_available_flag) as n_temp_available,
    round(sum(temp_available_flag) * 100.0 / count(*), 2) as pct_temp_available,

    sum(spo2_available_flag) as n_spo2_available,
    round(sum(spo2_available_flag) * 100.0 / count(*), 2) as pct_spo2_available

from study_ahf_v4.model_070D_vitals_0_12h_clean_v1;




-- 070D2 QC3：clean 后范围
select
    count(*) as n_total,

    min(hr_min) as hr_min_min,
    percentile_cont(0.5) within group (order by hr_mean) as hr_mean_median,
    max(hr_max) as hr_max_max,

    min(sbp_min) as sbp_min_min,
    percentile_cont(0.5) within group (order by sbp_mean) as sbp_mean_median,
    max(sbp_max) as sbp_max_max,

    min(mbp_min) as mbp_min_min,
    percentile_cont(0.5) within group (order by mbp_mean) as mbp_mean_median,
    max(mbp_max) as mbp_max_max,

    min(rr_min) as rr_min_min,
    percentile_cont(0.5) within group (order by rr_mean) as rr_mean_median,
    max(rr_max) as rr_max_max,

    min(temp_min) as temp_min_min,
    percentile_cont(0.5) within group (order by temp_mean) as temp_mean_median,
    max(temp_max) as temp_max_max,

    min(spo2_min) as spo2_min_min,
    percentile_cont(0.5) within group (order by spo2_mean) as spo2_mean_median,
    max(spo2_max) as spo2_max_max

from study_ahf_v4.model_070D_vitals_0_12h_clean_v1;




-- 070D2 QC4: cleaned-table availability summary.
select
    'clean' as version,
    count(*) as n_total,
    sum(hr_available_flag) as n_hr_available,
    sum(sbp_available_flag) as n_sbp_available,
    sum(mbp_available_flag) as n_mbp_available,
    sum(rr_available_flag) as n_rr_available,
    sum(temp_available_flag) as n_temp_available,
    sum(spo2_available_flag) as n_spo2_available
from study_ahf_v4.model_070D_vitals_0_12h_clean_v1;



