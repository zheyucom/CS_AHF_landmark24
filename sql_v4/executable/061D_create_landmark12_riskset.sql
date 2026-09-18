-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/02_outcome/061D_create_landmark12_riskset.sql
-- Purpose:
--   Create 12h landmark at-risk cohort.
--
-- Main risk set:
--   strict AHF 12h cohort
--   AND ICU LOS >=12h
--   AND no pre12 overt CS by main definition.
-- ============================================================

drop table if exists study_ahf_v4.cohort_061D_landmark12_riskset_main_v1 cascade;

create table study_ahf_v4.cohort_061D_landmark12_riskset_main_v1 as
select
    *,
    'landmark12_no_pre12_cs_main_future48h'::text as riskset_definition
from study_ahf_v4.outcome_061C_pre12_overt_cs_flags_v1
where reached_12h_landmark_flag = 1
  and pre12_overt_cs_main_flag = 0;


drop table if exists study_ahf_v4.cohort_061D_landmark12_riskset_broad_v1 cascade;

create table study_ahf_v4.cohort_061D_landmark12_riskset_broad_v1 as
select
    *,
    'landmark12_no_pre12_cs_broad_future48h'::text as riskset_definition
from study_ahf_v4.outcome_061C_pre12_overt_cs_flags_v1
where reached_12h_landmark_flag = 1
  and pre12_overt_cs_broad_flag = 0;
	
	
	
	
-- 	质控
select
    'ahf_strict_12h_original' as cohort,
    count(*) as n
from study_ahf_v4.cohort_061B_ahf_strict_12h_v1

union all

select
    'reached_12h_landmark' as cohort,
    count(*) as n
from study_ahf_v4.outcome_061C_pre12_overt_cs_flags_v1
where reached_12h_landmark_flag = 1

union all

select
    'pre12_overt_cs_main_excluded_among_reached12' as cohort,
    count(*) as n
from study_ahf_v4.outcome_061C_pre12_overt_cs_flags_v1
where reached_12h_landmark_flag = 1
  and pre12_overt_cs_main_flag = 1

union all

select
    'landmark12_riskset_main' as cohort,
    count(*) as n
from study_ahf_v4.cohort_061D_landmark12_riskset_main_v1

union all

select
    'pre12_overt_cs_broad_excluded_among_reached12' as cohort,
    count(*) as n
from study_ahf_v4.outcome_061C_pre12_overt_cs_flags_v1
where reached_12h_landmark_flag = 1
  and pre12_overt_cs_broad_flag = 1

union all

select
    'landmark12_riskset_broad' as cohort,
    count(*) as n
from study_ahf_v4.cohort_061D_landmark12_riskset_broad_v1;




select
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay
from study_ahf_v4.cohort_061D_landmark12_riskset_main_v1;




