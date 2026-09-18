-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/070G_create_modeling_dataset_v1.sql
-- Purpose:
--   Merge static, vitals, labs, and support features into the
--   final modeling dataset v1.
--
-- Population:
--   AHF + early sepsis by 12h
--   landmark 12h
--   no pre12 overt CS
--
-- Label:
--   primary_outcome_flag
--
-- Predictor window:
--   ICU intime <= feature time < ICU intime +12h.
--
-- Important:
--   The table contains outcome labels and QC variables, but
--   post-12h variables must NOT be used as predictors.
-- ============================================================

drop table if exists study_ahf_v4_2.model_070G_modeling_dataset_v1 cascade;

create table study_ahf_v4_2.model_070G_modeling_dataset_v1 as
select
    -- --------------------------------------------------------
    -- IDs and label
    -- --------------------------------------------------------
    b.subject_id,
    b.hadm_id,
    b.stay_id,

    b.intime,
    b.landmark12_time,
    b.window60_time,

    b.primary_outcome_flag,

    -- secondary labels / QC only, not predictors
    b.hd_support_initiation_or_count_increase_flag as label_support_escalation_flag,
    b.nee_escalation_conservative_flag as label_nee_escalation_flag,
    b.death_12_60_flag as label_death_12_60_flag,
    b.secondary_hd_deterioration_nee010_flag as label_hd_nee010_flag,
    b.secondary_hd_deterioration_no_nee_flag as label_hd_no_nee_flag,
    b.secondary_mixed_shock_proxy_flag as label_mixed_shock_proxy_flag,
    b.secondary_hd_lactate_confirmed_flag as label_hd_lactate_confirmed_flag,

    -- --------------------------------------------------------
    -- 070C static features
    -- --------------------------------------------------------
    c.age,
    c.female,
    c.male,

    c.first_unit_micu_flag,
    c.first_unit_ccu_cicu_flag,
    c.first_unit_sicu_flag,
    c.first_unit_cvicu_flag,

    c.hf_icd_primary_seq,
    c.hf_icd_seq_eq1_flag,
    c.hf_icd_seq_2_5_flag,
    c.acute_hf_icd_flag,
    c.hf_icd_seq_le5,
    c.iv_loop_rx_early12_flag,
    c.ntprobnp_ge300_early12_flag,
    c.ahf_evidence_score_primary_12h,

    c.early_sepsis12_max_sofa_score,
    c.early_sepsis12_suspected_infection_hour,
    c.early_sepsis12_sofa_hour,
    c.suspected_infection_before_icu_flag,
    c.suspected_infection_icu_0_6h_flag,
    c.suspected_infection_icu_6_12h_flag,

    c.charlson_comorbidity_index,
    c.charlson_myocardial_infarct,
    c.charlson_congestive_heart_failure,
    c.charlson_peripheral_vascular_disease,
    c.charlson_cerebrovascular_disease,
    c.charlson_dementia,
    c.charlson_chronic_pulmonary_disease,
    c.charlson_rheumatic_disease,
    c.charlson_peptic_ulcer_disease,
    c.charlson_mild_liver_disease,
    c.charlson_diabetes_without_cc,
    c.charlson_diabetes_with_cc,
    c.charlson_paraplegia,
    c.charlson_renal_disease,
    c.charlson_malignant_cancer,
    c.charlson_severe_liver_disease,
    c.charlson_metastatic_solid_tumor,
    c.charlson_aids,

    -- --------------------------------------------------------
    -- 070D clean vitals
    -- --------------------------------------------------------
    d.hr_n,
    d.hr_first,
    d.hr_last,
    d.hr_mean,
    d.hr_min,
    d.hr_max,
    d.hr_delta,

    d.sbp_n,
    d.sbp_first,
    d.sbp_last,
    d.sbp_mean,
    d.sbp_min,
    d.sbp_max,
    d.sbp_delta,

    d.dbp_n,
    d.dbp_mean,
    d.dbp_min,
    d.dbp_max,

    d.mbp_n,
    d.mbp_first,
    d.mbp_last,
    d.mbp_mean,
    d.mbp_min,
    d.mbp_max,
    d.mbp_delta,

    d.rr_n,
    d.rr_first,
    d.rr_last,
    d.rr_mean,
    d.rr_min,
    d.rr_max,
    d.rr_delta,

    d.temp_n,
    d.temp_first,
    d.temp_last,
    d.temp_mean,
    d.temp_min,
    d.temp_max,
    d.temp_delta,

    d.spo2_n,
    d.spo2_first,
    d.spo2_last,
    d.spo2_mean,
    d.spo2_min,
    d.spo2_max,
    d.spo2_delta,

    d.vital_glucose_n,
    d.vital_glucose_mean,
    d.vital_glucose_min,
    d.vital_glucose_max,

    d.hr_available_flag,
    d.sbp_available_flag,
    d.mbp_available_flag,
    d.rr_available_flag,
    d.temp_available_flag,
    d.spo2_available_flag,

    -- --------------------------------------------------------
    -- 070E labs
    -- --------------------------------------------------------
    e.lactate_n,
    e.lactate_first,
    e.lactate_last,
    e.lactate_min,
    e.lactate_max,
    e.lactate_mean,
    e.lactate_delta,

    e.ph_n,
    e.ph_first,
    e.ph_last,
    e.ph_min,
    e.ph_max,
    e.ph_mean,
    e.ph_delta,

    e.baseexcess_n,
    e.baseexcess_min,
    e.baseexcess_max,
    e.baseexcess_mean,

    e.bg_bicarbonate_n,
    e.bg_bicarbonate_min,
    e.bg_bicarbonate_max,
    e.bg_bicarbonate_mean,

    e.po2_n,
    e.po2_min,
    e.po2_max,
    e.po2_mean,

    e.pco2_n,
    e.pco2_min,
    e.pco2_max,
    e.pco2_mean,

    e.pf_ratio_n,
    e.pf_ratio_min,
    e.pf_ratio_max,
    e.pf_ratio_mean,

    e.creatinine_n,
    e.creatinine_first,
    e.creatinine_last,
    e.creatinine_min,
    e.creatinine_max,
    e.creatinine_mean,
    e.creatinine_delta,

    e.bun_n,
    e.bun_min,
    e.bun_max,
    e.bun_mean,

    e.sodium_n,
    e.sodium_min,
    e.sodium_max,
    e.sodium_mean,

    e.potassium_n,
    e.potassium_min,
    e.potassium_max,
    e.potassium_mean,

    e.chloride_n,
    e.chloride_min,
    e.chloride_max,
    e.chloride_mean,

    e.chem_bicarbonate_n,
    e.chem_bicarbonate_min,
    e.chem_bicarbonate_max,
    e.chem_bicarbonate_mean,

    e.aniongap_n,
    e.aniongap_min,
    e.aniongap_max,
    e.aniongap_mean,

    e.chem_glucose_n,
    e.chem_glucose_min,
    e.chem_glucose_max,
    e.chem_glucose_mean,

    e.albumin_n,
    e.albumin_min,
    e.albumin_max,
    e.albumin_mean,

    e.wbc_n,
    e.wbc_min,
    e.wbc_max,
    e.wbc_mean,

    e.hemoglobin_n,
    e.hemoglobin_min,
    e.hemoglobin_max,
    e.hemoglobin_mean,

    e.platelet_n,
    e.platelet_min,
    e.platelet_max,
    e.platelet_mean,

    e.rdw_n,
    e.rdw_min,
    e.rdw_max,
    e.rdw_mean,

    e.inr_n,
    e.inr_min,
    e.inr_max,
    e.inr_mean,

    e.pt_n,
    e.pt_min,
    e.pt_max,
    e.pt_mean,

    e.ptt_n,
    e.ptt_min,
    e.ptt_max,
    e.ptt_mean,

    e.fibrinogen_n,
    e.fibrinogen_min,
    e.fibrinogen_max,
    e.fibrinogen_mean,

    e.d_dimer_n,
    e.d_dimer_min,
    e.d_dimer_max,
    e.d_dimer_mean,

    e.lactate_available_flag,
    e.ph_available_flag,
    e.creatinine_available_flag,
    e.bun_available_flag,
    e.wbc_available_flag,
    e.platelet_available_flag,
    e.inr_available_flag,

    -- --------------------------------------------------------
    -- 070F support features
    -- --------------------------------------------------------
    f.urineoutput_0_12h_n,
    f.urineoutput_0_12h_total_ml,
    f.urineoutput_0_12h_mean_record_ml,
    f.urineoutput_0_12h_min_record_ml,
    f.urineoutput_0_12h_max_record_ml,
    f.low_urineoutput_0_12h_crude_flag,
    f.urineoutput_available_flag,

    f.gcs_n,
    f.gcs_first,
    f.gcs_last,
    f.gcs_min,
    f.gcs_max,
    f.gcs_mean,
    f.gcs_delta,
    f.gcs_motor_min,
    f.gcs_motor_max,
    f.gcs_verbal_min,
    f.gcs_verbal_max,
    f.gcs_eyes_min,
    f.gcs_eyes_max,
    f.gcs_unable_any_flag,
    f.gcs_available_flag,

    f.ventilation_records_0_12h_n,
    f.invasive_vent_0_12h_flag,
    f.noninvasive_vent_0_12h_flag,
    f.highflow_0_12h_flag,
    f.oxygen_0_12h_flag,
    f.advanced_respiratory_support_0_12h_flag,

    f.vaso_records_0_12h_n,
    f.norepinephrine_0_12h_flag,
    f.epinephrine_0_12h_flag,
    f.dopamine_0_12h_flag,
    f.phenylephrine_0_12h_flag,
    f.vasopressin_0_12h_flag,
    f.dobutamine_0_12h_flag,
    f.milrinone_0_12h_flag,

    f.vasoactive_agent_count_0_12h,
    f.vasopressor_any_0_12h_flag,
    f.inotrope_any_0_12h_flag,

    f.norepinephrine_0_12h_max,
    f.epinephrine_0_12h_max,
    f.dopamine_0_12h_max,
    f.phenylephrine_0_12h_max,
    f.vasopressin_0_12h_max,
    f.dobutamine_0_12h_max,
    f.milrinone_0_12h_max,

    f.nee_0_12h_n,
    f.nee_0_12h_max,
    f.nee_0_12h_min,
    f.nee_0_12h_mean,
    f.nee_0_12h_last,
    f.nee_available_0_12h_flag

from study_ahf_v4_2.model_070a_base_index_ahf_only_v1 b
left join study_ahf_v4_2.model_070C_static_clinical_features_v1 c
    on b.stay_id = c.stay_id
left join study_ahf_v4_2.model_070D_vitals_0_12h_clean_v1 d
    on b.stay_id = d.stay_id
left join study_ahf_v4_2.model_070E_labs_0_12h_v1 e
    on b.stay_id = e.stay_id
left join study_ahf_v4_2.model_070F_support_0_12h_v1 f
    on b.stay_id = f.stay_id;
		
		
		
		
		
-- 		070G QC1：总体人数和事件率
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf_v4_2.model_070G_modeling_dataset_v1;




-- 070G QC2：重复检查
select
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay
from study_ahf_v4_2.model_070G_modeling_dataset_v1;




-- 070G QC3：关键变量缺失率
select
    count(*) as n_total,

    sum(case when age is null then 1 else 0 end) as miss_age,
    round(sum(case when age is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_age,

    sum(case when early_sepsis12_max_sofa_score is null then 1 else 0 end) as miss_early_sofa,
    round(sum(case when early_sepsis12_max_sofa_score is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_early_sofa,

    sum(case when mbp_min is null then 1 else 0 end) as miss_mbp_min,
    round(sum(case when mbp_min is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_mbp_min,

    sum(case when hr_max is null then 1 else 0 end) as miss_hr_max,
    round(sum(case when hr_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_hr_max,

    sum(case when lactate_max is null then 1 else 0 end) as miss_lactate_max,
    round(sum(case when lactate_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_lactate_max,

    sum(case when ph_min is null then 1 else 0 end) as miss_ph_min,
    round(sum(case when ph_min is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_ph_min,

    sum(case when creatinine_max is null then 1 else 0 end) as miss_creatinine_max,
    round(sum(case when creatinine_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_creatinine_max,

    sum(case when wbc_max is null then 1 else 0 end) as miss_wbc_max,
    round(sum(case when wbc_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_wbc_max,

    sum(case when platelet_min is null then 1 else 0 end) as miss_platelet_min,
    round(sum(case when platelet_min is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_platelet_min,

    sum(case when urineoutput_0_12h_total_ml is null then 1 else 0 end) as miss_urineoutput,
    round(sum(case when urineoutput_0_12h_total_ml is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_urineoutput,

    sum(case when gcs_min is null then 1 else 0 end) as miss_gcs_min,
    round(sum(case when gcs_min is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_gcs_min,

    sum(case when nee_0_12h_max is null then 1 else 0 end) as miss_nee_max,
    round(sum(case when nee_0_12h_max is null then 1 else 0 end) * 100.0 / count(*), 2) as pct_miss_nee_max

from study_ahf_v4_2.model_070G_modeling_dataset_v1;





-- 070G QC4：是否有 post12 泄露变量名
select
    column_name
from information_schema.columns
where table_schema = 'study_ahf_v4'
  and table_name = 'model_070g_modeling_dataset_v1'
  and (
        lower(column_name) like '%post12%'
     or lower(column_name) like '%death_12_60%'
     or lower(column_name) like '%complete60%'
     or lower(column_name) like '%followup%'
     or lower(column_name) like '%observed_until%'
     or lower(column_name) like '%outcome_definition%'
     or lower(column_name) like '%secondary%'
  )
order by column_name;




-- 070G QC5：导出变量列数
select
    count(*) as n_columns
from information_schema.columns
where table_schema = 'study_ahf_v4'
  and table_name = 'model_070g_modeling_dataset_v1';
	
	
	
	