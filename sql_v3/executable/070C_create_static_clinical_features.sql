-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/070C_create_static_clinical_features.sql
-- Purpose:
--   Create static clinical features for primary modeling cohort.
--
-- Population:
--   AHF + early sepsis by 12h
--   landmark 12h
--   primary outcome: 12-60h hemodynamic deterioration
--
-- Feature groups:
--   1. demographics
--   2. ICU admission unit
--   3. AHF evidence by 12h
--   4. early sepsis timing/severity by 12h
--   5. Charlson comorbidities
--
-- Leakage control:
--   No post-12h variables are included as predictors.
-- ============================================================

drop table if exists study_ahf_v3.model_070C_static_clinical_features_v1 cascade;

create table study_ahf_v3.model_070C_static_clinical_features_v1 as
with base as (
    select *
    from study_ahf_v3.model_070A_base_index_v1
),

charlson as (
    select *
    from mimiciv_derived.charlson
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,

    -- label
    b.primary_outcome_flag,

    -- --------------------------------------------------------
    -- Demographics
    -- --------------------------------------------------------
    b.anchor_age as age,

    case
        when b.gender = 'F' then 1
        else 0
    end as female,

    case
        when b.gender = 'M' then 1
        else 0
    end as male,

    -- --------------------------------------------------------
    -- ICU admission unit
    -- --------------------------------------------------------
    b.first_careunit,
    b.last_careunit,

    case
        when lower(b.first_careunit) like '%medical%' then 1
        else 0
    end as first_unit_micu_flag,

    case
        when lower(b.first_careunit) like '%cardiac%'
          or lower(b.first_careunit) like '%coronary%'
        then 1 else 0
    end as first_unit_ccu_cicu_flag,

    case
        when lower(b.first_careunit) like '%surgical%' then 1
        else 0
    end as first_unit_sicu_flag,

    case
        when lower(b.first_careunit) like '%cardiac vascular%'
          or lower(b.first_careunit) like '%cvicu%'
        then 1 else 0
    end as first_unit_cvicu_flag,

    -- --------------------------------------------------------
    -- AHF evidence available by 12h
    -- --------------------------------------------------------
    b.hf_icd_primary_seq,

    case
        when b.hf_icd_primary_seq = 1 then 1
        else 0
    end as hf_icd_seq_eq1_flag,

    case
        when b.hf_icd_primary_seq between 2 and 5 then 1
        else 0
    end as hf_icd_seq_2_5_flag,

    b.hf_icd_acute_or_acute_on_chronic as acute_hf_icd_flag,
    b.hf_icd_seq_le5,
    b.iv_loop_rx_early12_flag,
    b.ntprobnp_ge300_early12_flag,
    b.ahf_evidence_score_primary_12h,

    -- --------------------------------------------------------
    -- Early sepsis evidence by 12h
    -- These are allowed because early sepsis was defined using
    -- evidence available before the 12h landmark.
    -- --------------------------------------------------------
    b.early_sepsis12_main_flag,
    b.early_sepsis12_max_sofa_score,

    b.early_sepsis12_suspected_infection_hour,
    b.early_sepsis12_sofa_hour,

    case
        when b.early_sepsis12_suspected_infection_hour < 0 then 1
        else 0
    end as suspected_infection_before_icu_flag,

    case
        when b.early_sepsis12_suspected_infection_hour >= 0
         and b.early_sepsis12_suspected_infection_hour < 6
        then 1 else 0
    end as suspected_infection_icu_0_6h_flag,

    case
        when b.early_sepsis12_suspected_infection_hour >= 6
         and b.early_sepsis12_suspected_infection_hour < 12
        then 1 else 0
    end as suspected_infection_icu_6_12h_flag,

    -- --------------------------------------------------------
    -- Charlson comorbidity index and components
    -- --------------------------------------------------------
    coalesce(c.charlson_comorbidity_index, 0) as charlson_comorbidity_index,

    coalesce(c.myocardial_infarct, 0) as charlson_myocardial_infarct,
    coalesce(c.congestive_heart_failure, 0) as charlson_congestive_heart_failure,
    coalesce(c.peripheral_vascular_disease, 0) as charlson_peripheral_vascular_disease,
    coalesce(c.cerebrovascular_disease, 0) as charlson_cerebrovascular_disease,
    coalesce(c.dementia, 0) as charlson_dementia,
    coalesce(c.chronic_pulmonary_disease, 0) as charlson_chronic_pulmonary_disease,
    coalesce(c.rheumatic_disease, 0) as charlson_rheumatic_disease,
    coalesce(c.peptic_ulcer_disease, 0) as charlson_peptic_ulcer_disease,
    coalesce(c.mild_liver_disease, 0) as charlson_mild_liver_disease,
    coalesce(c.diabetes_without_cc, 0) as charlson_diabetes_without_cc,
    coalesce(c.diabetes_with_cc, 0) as charlson_diabetes_with_cc,
    coalesce(c.paraplegia, 0) as charlson_paraplegia,
    coalesce(c.renal_disease, 0) as charlson_renal_disease,
    coalesce(c.malignant_cancer, 0) as charlson_malignant_cancer,
    coalesce(c.severe_liver_disease, 0) as charlson_severe_liver_disease,
    coalesce(c.metastatic_solid_tumor, 0) as charlson_metastatic_solid_tumor,
    coalesce(c.aids, 0) as charlson_aids,

    case
        when c.hadm_id is not null then 1
        else 0
    end as charlson_available_flag

from base b
left join charlson c
    on b.subject_id = c.subject_id
   and b.hadm_id = c.hadm_id;
	 
	 
	 
	 
-- 	 070C QC1：总体人数和事件率
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,

    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate,

    min(age) as min_age,
    percentile_cont(0.5) within group (order by age) as median_age,
    max(age) as max_age,

    sum(female) as n_female,
    round(sum(female) * 100.0 / count(*), 2) as pct_female,

    sum(charlson_available_flag) as n_charlson_available,
    round(sum(charlson_available_flag) * 100.0 / count(*), 2) as pct_charlson_available

from study_ahf_v3.model_070C_static_clinical_features_v1;



-- 070C QC2：主要静态变量缺失情况
select
    count(*) as n_total,

    sum(case when age is null then 1 else 0 end) as miss_age,
    sum(case when female is null then 1 else 0 end) as miss_female,
    sum(case when hf_icd_primary_seq is null then 1 else 0 end) as miss_hf_icd_primary_seq,
    sum(case when ahf_evidence_score_primary_12h is null then 1 else 0 end) as miss_ahf_evidence_score,
    sum(case when early_sepsis12_max_sofa_score is null then 1 else 0 end) as miss_early_sepsis12_max_sofa,
    sum(case when early_sepsis12_suspected_infection_hour is null then 1 else 0 end) as miss_suspected_infection_hour,
    sum(case when early_sepsis12_sofa_hour is null then 1 else 0 end) as miss_sofa_hour,
    sum(case when charlson_comorbidity_index is null then 1 else 0 end) as miss_charlson_index

from study_ahf_v3.model_070C_static_clinical_features_v1;




-- 070C QC3：事件率按 early sepsis SOFA 分层
select
    case
        when early_sepsis12_max_sofa_score is null then '00_missing'
        when early_sepsis12_max_sofa_score < 4 then '01_sofa_lt4'
        when early_sepsis12_max_sofa_score between 4 and 7 then '02_sofa_4_7'
        when early_sepsis12_max_sofa_score between 8 and 11 then '03_sofa_8_11'
        when early_sepsis12_max_sofa_score >= 12 then '04_sofa_ge12'
        else '99_other'
    end as early_sofa_group,

    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate

from study_ahf_v3.model_070C_static_clinical_features_v1
group by
    case
        when early_sepsis12_max_sofa_score is null then '00_missing'
        when early_sepsis12_max_sofa_score < 4 then '01_sofa_lt4'
        when early_sepsis12_max_sofa_score between 4 and 7 then '02_sofa_4_7'
        when early_sepsis12_max_sofa_score between 8 and 11 then '03_sofa_8_11'
        when early_sepsis12_max_sofa_score >= 12 then '04_sofa_ge12'
        else '99_other'
    end
order by early_sofa_group;




-- 070C QC4：事件率按 Charlson 分层
select
    case
        when charlson_comorbidity_index < 3 then '01_charlson_lt3'
        when charlson_comorbidity_index between 3 and 5 then '02_charlson_3_5'
        when charlson_comorbidity_index between 6 and 8 then '03_charlson_6_8'
        when charlson_comorbidity_index >= 9 then '04_charlson_ge9'
        else '99_other'
    end as charlson_group,

    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate

from study_ahf_v3.model_070C_static_clinical_features_v1
group by
    case
        when charlson_comorbidity_index < 3 then '01_charlson_lt3'
        when charlson_comorbidity_index between 3 and 5 then '02_charlson_3_5'
        when charlson_comorbidity_index between 6 and 8 then '03_charlson_6_8'
        when charlson_comorbidity_index >= 9 then '04_charlson_ge9'
        else '99_other'
    end
order by charlson_group;




-- 070C QC5：ICU 单元分布
select
    first_careunit,
    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf_v3.model_070C_static_clinical_features_v1
group by first_careunit
order by n desc;




