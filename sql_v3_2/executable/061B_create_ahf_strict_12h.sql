-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/01_cohort/061B_create_ahf_strict_12h.sql
-- Purpose:
--   Create strict AHF cohort for 12h landmark analysis.
--
-- Definition (v3.2):
--   Retrospective AHF anchor: HF ICD seq <=5 in final coding
--   AND time-confirmed AHF: >=1 timestamped evidence
--       (IV loop eMAR / IV loop Rx / NT-proBNP) inside [T0-24h, T12).
--   The v3 ICD-only patients are excluded from the MAIN cohort.
--   Analysis unit (v3.2): index hospitalization per patient. After the
--   AHF phenotype is applied, keep only the earliest qualifying
--   hospitalization (by admittime, then intime) per subject, so each
--   patient contributes exactly one ICU stay.
-- ============================================================

drop table if exists study_ahf_v3_2.cohort_061B_ahf_strict_12h_v1 cascade;

create table study_ahf_v3_2.cohort_061B_ahf_strict_12h_v1 as
with ahf_strict as (
    select
        a.*,
        coalesce(ad.admittime, a.intime) as index_adm_time
    from study_ahf_v3_2.cohort_061A_ahf_evidence_early_window_12h_v1 a
    left join mimiciv_hosp.admissions ad
        on a.hadm_id = ad.hadm_id
    where a.hf_icd_seq_le5 = 1
      and a.ahf_retro_confirmed_flag = 1
      and a.ahf_time_confirmed_by_t12_flag = 1
),
index_ranked as (
    select
        *,
        row_number() over (
            partition by subject_id
            order by index_adm_time, intime, stay_id
        ) as rn_index_adm
    from ahf_strict
)
select
    *,
    'strict_ahf_12h_time_confirmed_index_adm'::text as ahf_cohort_definition_12h
from index_ranked
where rn_index_adm = 1;
	
	
	
	
-- 	质控：
select
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    min(anchor_age) as min_age,
    max(anchor_age) as max_age,
    min(icu_los_hours) as min_icu_los_hours,
    percentile_cont(0.5) within group (order by icu_los_hours) as median_icu_los_hours,
    max(icu_los_hours) as max_icu_los_hours
from study_ahf_v3_2.cohort_061B_ahf_strict_12h_v1;




select
    count(*) as n_total,
    sum(case when icu_los_hours >= 12 then 1 else 0 end) as n_icu_los_ge12h,
    round(sum(case when icu_los_hours >= 12 then 1 else 0 end) * 100.0 / count(*), 2) as pct_icu_los_ge12h,
    sum(case when icu_los_hours < 12 then 1 else 0 end) as n_icu_los_lt12h,
    round(sum(case when icu_los_hours < 12 then 1 else 0 end) * 100.0 / count(*), 2) as pct_icu_los_lt12h,
    sum(case when icu_los_hours is null then 1 else 0 end) as n_icu_los_missing
from study_ahf_v3_2.cohort_061B_ahf_strict_12h_v1;




