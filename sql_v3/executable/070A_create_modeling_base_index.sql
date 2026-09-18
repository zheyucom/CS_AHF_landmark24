-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/070A_create_modeling_base_index.sql
-- Purpose:
--   Create modeling base index table for primary analysis.
--
-- Population:
--   AHF + early sepsis by 12h
--   reached 12h landmark
--   no pre12 overt CS
--
-- Primary outcome:
--   12-60h hemodynamic deterioration:
--     support initiation,
--     increased vasoactive/inotrope agent count,
--     NEE increase >=0.05,
--     or death within 12-60h.
--
-- Predictor window:
--   ICU intime to ICU intime +12h only.
-- ============================================================

drop table if exists study_ahf_v3.model_070A_base_index_v1 cascade;

create table study_ahf_v3.model_070A_base_index_v1 as
select
    o.subject_id,
    o.hadm_id,
    o.stay_id,

    c.first_careunit,
    c.last_careunit,
    c.intime,
    c.outtime,
    c.icu_los_hours,

    c.gender,
    c.anchor_age,

    c.hf_icd_primary_seq,
    c.hf_icd_acute_or_acute_on_chronic,
    c.hf_icd_seq_le5,
    c.iv_loop_rx_early12_flag,
    c.ntprobnp_ge300_early12_flag,
    c.ahf_evidence_score_primary_12h,

    o.early_sepsis12_main_flag,
    o.early_sepsis12_first_suspected_infection_time,
    o.early_sepsis12_first_sofa_time,
    o.early_sepsis12_max_sofa_score,

    extract(
        epoch from (o.early_sepsis12_first_suspected_infection_time - c.intime)
    ) / 3600.0 as early_sepsis12_suspected_infection_hour,

    extract(
        epoch from (o.early_sepsis12_first_sofa_time - c.intime)
    ) / 3600.0 as early_sepsis12_sofa_hour,

    c.intime + interval '12 hour' as landmark12_time,
    c.intime + interval '60 hour' as window60_time,

    -- Outcome variables.
    -- These are labels or QC variables, not predictors.
    o.primary_outcome_flag,
    o.primary_outcome_definition,

    o.hd_support_initiation_or_count_increase_flag,
    o.nee_escalation_conservative_flag,
    o.death_12_60_flag,

    o.secondary_hd_deterioration_nee010_flag,
    o.secondary_hd_deterioration_no_nee_flag,
    o.secondary_mixed_shock_proxy_flag,
    o.secondary_hd_lactate_confirmed_flag,

    o.complete60_icu_flag,
    o.followup_hours_12_60

from study_ahf_v3.outcome_064_primary_hd_deterioration_v1 o
inner join study_ahf_v3.cohort_061B_ahf_strict_12h_v1 c
    on o.subject_id = c.subject_id
   and o.hadm_id = c.hadm_id
   and o.stay_id = c.stay_id;
	 
	 
	 
	 
-- 	 070A QC1：基础表人数和事件率
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,

    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate,

    min(anchor_age) as min_age,
    max(anchor_age) as max_age,
    sum(case when gender = 'F' then 1 else 0 end) as n_female,
    round(sum(case when gender = 'F' then 1 else 0 end) * 100.0 / count(*), 2) as pct_female

from study_ahf_v3.model_070A_base_index_v1;




-- 070A QC2：检查是否有重复
select
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay
from study_ahf_v3.model_070A_base_index_v1;





