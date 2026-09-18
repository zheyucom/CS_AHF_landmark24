-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/01_cohort/061B_create_ahf_strict_12h.sql
-- Purpose:
--   Create strict AHF cohort for 12h landmark analysis.
--
-- Definition:
--   HF ICD seq <=5
--   AND at least one of: retrospective acute-HF phenotype confirmation,
--   or time-stamped clinical evidence available by T12.
-- Final ICD fields are phenotype anchors only and will be excluded from
-- model predictors. The time-evidence-only subgroup will be reported.
-- ============================================================

drop table if exists study_ahf_v4.cohort_061B_ahf_strict_12h_v1 cascade;

create table study_ahf_v4.cohort_061B_ahf_strict_12h_v1 as
select
    *,
    'strict_ahf_12h'::text as ahf_cohort_definition_12h
from study_ahf_v4.cohort_061A_ahf_evidence_early_window_12h_v1
where hf_icd_seq_le5 = 1
  and (
        hf_icd_acute_or_acute_on_chronic = 1
     or ahf_time_evidence_by_t12_flag = 1
  );
	
	
	
	
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
from study_ahf_v4.cohort_061B_ahf_strict_12h_v1;




select
    count(*) as n_total,
    sum(case when icu_los_hours >= 12 then 1 else 0 end) as n_icu_los_ge12h,
    round(sum(case when icu_los_hours >= 12 then 1 else 0 end) * 100.0 / count(*), 2) as pct_icu_los_ge12h,
    sum(case when icu_los_hours < 12 then 1 else 0 end) as n_icu_los_lt12h,
    round(sum(case when icu_los_hours < 12 then 1 else 0 end) * 100.0 / count(*), 2) as pct_icu_los_lt12h,
    sum(case when icu_los_hours is null then 1 else 0 end) as n_icu_los_missing
from study_ahf_v4.cohort_061B_ahf_strict_12h_v1;

