-- ============================================================
-- Project: CS_AHF_landmark12_earlysepsis
-- File: sql/02_outcome/062A_create_early_sepsis12_flags.sql
-- Purpose:
--   Add early sepsis flags to the 12h landmark AHF risk set.
--
-- Input:
--   study_ahf.outcome_061E_post12_overt_cs_future48h_main_v1
--
-- Main early sepsis definition:
--   sepsis3 = true
--   AND suspected_infection_time within ICU intime -24h to +12h
--   AND sofa_time within ICU intime -24h to +12h
--
-- This avoids using sepsis information occurring after the 12h landmark.
-- ============================================================

drop table if exists study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1 cascade;

create table study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1 as
with base as (
    select
        *,
        intime + interval '12 hour' as landmark12_time_for_sepsis
    from study_ahf.outcome_061E_post12_overt_cs_future48h_main_v1
),

sepsis_raw as (
    select
        b.stay_id,

        s.suspected_infection_time,
        s.sofa_time,
        s.sofa_score,

        case
            when lower(coalesce(s.sepsis3::text, '')) in ('true', 't', '1', 'yes')
            then 1 else 0
        end as sepsis3_flag,

        case
            when s.suspected_infection_time >= b.intime - interval '24 hour'
             and s.suspected_infection_time <  b.intime + interval '12 hour'
            then 1 else 0
        end as suspected_infection_by12_flag,

        case
            when s.sofa_time >= b.intime - interval '24 hour'
             and s.sofa_time <  b.intime + interval '12 hour'
            then 1 else 0
        end as sofa_by12_flag,

        case
            when s.suspected_infection_time is not null
            then extract(epoch from (s.suspected_infection_time - b.intime)) / 3600.0
            else null
        end as suspected_infection_hour_from_icu,

        case
            when s.sofa_time is not null
            then extract(epoch from (s.sofa_time - b.intime)) / 3600.0
            else null
        end as sofa_hour_from_icu

    from base b
    left join mimiciv_derived.sepsis3 s
        on b.stay_id = s.stay_id
),

sepsis_by_stay as (
    select
        stay_id,

        max(sepsis3_flag) as sepsis3_any_icu_flag,

        max(
            case
                when sepsis3_flag = 1
                 and suspected_infection_by12_flag = 1
                 and sofa_by12_flag = 1
                then 1 else 0
            end
        ) as early_sepsis12_main_flag,

        max(
            case
                when sepsis3_flag = 1
                 and suspected_infection_by12_flag = 1
                then 1 else 0
            end
        ) as early_sepsis12_suspected_infection_only_flag,

        max(
            case
                when sepsis3_flag = 1
                 and (
                        suspected_infection_by12_flag = 1
                     or sofa_by12_flag = 1
                 )
                then 1 else 0
            end
        ) as early_sepsis12_broad_flag,

        min(suspected_infection_time) filter (
            where sepsis3_flag = 1
              and suspected_infection_by12_flag = 1
        ) as early_sepsis12_first_suspected_infection_time,

        min(sofa_time) filter (
            where sepsis3_flag = 1
              and sofa_by12_flag = 1
        ) as early_sepsis12_first_sofa_time,

        max(sofa_score) filter (
            where sepsis3_flag = 1
              and (
                    suspected_infection_by12_flag = 1
                 or sofa_by12_flag = 1
              )
        ) as early_sepsis12_max_sofa_score,

        min(suspected_infection_hour_from_icu) filter (
            where sepsis3_flag = 1
              and suspected_infection_by12_flag = 1
        ) as early_sepsis12_first_suspected_infection_hour,

        min(sofa_hour_from_icu) filter (
            where sepsis3_flag = 1
              and sofa_by12_flag = 1
        ) as early_sepsis12_first_sofa_hour

    from sepsis_raw
    group by stay_id
)

select
    b.*,

    coalesce(s.sepsis3_any_icu_flag, 0) as sepsis3_any_icu_flag,
    coalesce(s.early_sepsis12_main_flag, 0) as early_sepsis12_main_flag,
    coalesce(s.early_sepsis12_suspected_infection_only_flag, 0) as early_sepsis12_suspected_infection_only_flag,
    coalesce(s.early_sepsis12_broad_flag, 0) as early_sepsis12_broad_flag,

    s.early_sepsis12_first_suspected_infection_time,
    s.early_sepsis12_first_sofa_time,
    s.early_sepsis12_max_sofa_score,
    s.early_sepsis12_first_suspected_infection_hour,
    s.early_sepsis12_first_sofa_hour

from base b
left join sepsis_by_stay s
    on b.stay_id = s.stay_id;
		
		
		
		
		
-- 		062A 质控 1：early sepsis12 分布
select
    count(*) as n_total,

    sum(sepsis3_any_icu_flag) as n_sepsis3_any_icu,
    round(sum(sepsis3_any_icu_flag) * 100.0 / count(*), 2) as pct_sepsis3_any_icu,

    sum(early_sepsis12_main_flag) as n_early_sepsis12_main,
    round(sum(early_sepsis12_main_flag) * 100.0 / count(*), 2) as pct_early_sepsis12_main,

    sum(early_sepsis12_suspected_infection_only_flag) as n_early_sepsis12_suspected_infection_only,
    round(sum(early_sepsis12_suspected_infection_only_flag) * 100.0 / count(*), 2) as pct_early_sepsis12_suspected_infection_only,

    sum(early_sepsis12_broad_flag) as n_early_sepsis12_broad,
    round(sum(early_sepsis12_broad_flag) * 100.0 / count(*), 2) as pct_early_sepsis12_broad

from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1;





-- 062A 质控 2：early sepsis12 与事件率
select
    early_sepsis12_main_flag,
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate,
    sum(post12_overt_cs_lac4_flag) as n_lac4_events,
    round(sum(post12_overt_cs_lac4_flag) * 100.0 / count(*), 2) as lac4_event_rate,
    sum(complete60_icu_flag) as n_complete60,
    round(sum(complete60_icu_flag) * 100.0 / count(*), 2) as pct_complete60,
    sum(death_12_60_flag) as n_death_12_60,
    round(sum(death_12_60_flag) * 100.0 / count(*), 2) as pct_death_12_60
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
group by early_sepsis12_main_flag
order by early_sepsis12_main_flag;




-- 062A 质控 3：不同 sepsis 定义下事件率
select
    'overall_ahf12_riskset' as cohort,
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1

union all

select
    'sepsis3_any_icu',
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
where sepsis3_any_icu_flag = 1

union all

select
    'early_sepsis12_main',
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_main_flag = 1

union all

select
    'early_sepsis12_suspected_infection_only',
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_suspected_infection_only_flag = 1

union all

select
    'early_sepsis12_broad',
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_broad_flag = 1

union all

select
    'no_early_sepsis12_main',
    count(*) as n,
    sum(post12_overt_cs_main_flag) as n_events,
    round(sum(post12_overt_cs_main_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_main_flag = 0;





-- 062A 质控 4：early sepsis 发生时间分布
select
    case
        when early_sepsis12_first_suspected_infection_hour < -12 then '00_before_icu_12_24h'
        when early_sepsis12_first_suspected_infection_hour < 0 then '01_before_icu_0_12h'
        when early_sepsis12_first_suspected_infection_hour < 6 then '02_icu_0_6h'
        when early_sepsis12_first_suspected_infection_hour < 12 then '03_icu_6_12h'
        else '99_missing_or_other'
    end as suspected_infection_time_bin,
    count(*) as n,
    round(count(*) * 100.0 / sum(count(*)) over (), 2) as pct
from study_ahf.outcome_062A_post12_outcome_with_earlysepsis12_v1
where early_sepsis12_main_flag = 1
group by
    case
        when early_sepsis12_first_suspected_infection_hour < -12 then '00_before_icu_12_24h'
        when early_sepsis12_first_suspected_infection_hour < 0 then '01_before_icu_0_12h'
        when early_sepsis12_first_suspected_infection_hour < 6 then '02_icu_0_6h'
        when early_sepsis12_first_suspected_infection_hour < 12 then '03_icu_6_12h'
        else '99_missing_or_other'
    end
order by suspected_infection_time_bin;





