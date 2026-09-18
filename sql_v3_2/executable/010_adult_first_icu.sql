-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/01_cohort/010_adult_first_icu.sql
-- Purpose:
--   Define adult first ICU stay PER HOSPITALIZATION cohort (v3.2).
--
-- Important (v3.2 analysis-unit change):
--   The analysis unit is now "first ICU stay within each index
--   hospitalization". This base table keeps the first ICU stay of
--   EVERY hospitalization (no subject-level dedup). Subject-level
--   "index hospitalization" dedup happens downstream in 061B, after
--   the AHF phenotype is applied.
-- ============================================================

drop table if exists study_ahf_v3_2.cohort_010_adult_first_icu_v1 cascade;

create table study_ahf_v3_2.cohort_010_adult_first_icu_v1 as
with icu_ranked as (
    select
        i.subject_id,
        i.hadm_id,
        i.stay_id,
        i.first_careunit,
        i.last_careunit,
        i.intime,
        i.outtime,
        extract(epoch from (i.outtime - i.intime)) / 3600.0 as icu_los_hours,
        p.gender,
        p.anchor_age,
        p.anchor_year,
        p.anchor_year_group,
        ad.admittime,
        row_number() over (
            partition by i.hadm_id
            order by i.intime, i.stay_id
        ) as rn_first_icu_hadm
    from mimiciv_icu.icustays i
    inner join mimiciv_hosp.patients p
        on i.subject_id = p.subject_id
    inner join mimiciv_hosp.admissions ad
        on i.hadm_id = ad.hadm_id
)
select
    subject_id,
    hadm_id,
    stay_id,
    first_careunit,
    last_careunit,
    intime,
    outtime,
    icu_los_hours,
    admittime,
    gender,
    anchor_age,
    anchor_year,
    anchor_year_group
from icu_ranked
where anchor_age >= 18
  and rn_first_icu_hadm = 1;
	
	
-- 	QC
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
from study_ahf_v3_2.cohort_010_adult_first_icu_v1;




-- flow 表
insert into study_ahf_v3_2.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    10 as step_id,
    'adult_first_icu' as step_name,
    'study_ahf_v3_2.cohort_010_adult_first_icu_v1' as table_name,
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    null as excluded_from_prior,
    'Adult patients, first ICU stay per hospitalization (no subject dedup; index dedup in 061B).' as notes
from study_ahf_v3_2.cohort_010_adult_first_icu_v1;



