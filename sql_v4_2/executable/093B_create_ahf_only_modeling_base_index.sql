-- ============================================================
-- Project: CS_AHF_landmark24
-- Version: v4.2 AHF-only, strict pre-T0 AHF
-- Purpose: expose the same base-index contract used by 070C-080G.
-- ============================================================

drop table if exists study_ahf_v4_2.model_070a_base_index_ahf_only_v1 cascade;

create table study_ahf_v4_2.model_070a_base_index_ahf_only_v1 as
select
    subject_id,
    hadm_id,
    stay_id,
    first_careunit,
    last_careunit,
    intime,
    outtime,
    icu_los_hours,
    gender,
    anchor_age,
    hf_icd_primary_seq,
    hf_icd_acute_or_acute_on_chronic,
    hf_icd_seq_le5,
    iv_loop_rx_early12_flag,
    ntprobnp_ge300_early12_flag,
    ahf_evidence_score_primary_12h,
    early_sepsis12_main_flag,
    early_sepsis_admission_present_flag,
    early_sepsis12_first_suspected_infection_time,
    early_sepsis12_first_sofa_time,
    early_sepsis12_first_antibiotic_time,
    early_sepsis12_first_culture_time,
    early_sepsis12_max_sofa_score,
    intime + interval '12 hour' as landmark12_time,
    intime + interval '60 hour' as window60_time,
    hd_deterioration_broad_nee005_flag as primary_outcome_flag,
    'hd_deterioration_broad_nee005'::text as primary_outcome_definition,
    hd_support_initiation_or_count_increase_flag,
    nee_escalation_conservative_flag,
    death_12_60_flag,
    hd_deterioration_broad_nee010_flag as secondary_hd_deterioration_nee010_flag,
    hd_deterioration_broad_flag as secondary_hd_deterioration_no_nee_flag,
    current_mixed_shock_proxy_flag as secondary_mixed_shock_proxy_flag,
    hd_deterioration_lac_confirmed_nee005_flag as secondary_hd_lactate_confirmed_flag,
    complete60_icu_flag,
    followup_hours_12_60,
    strict_pre_t0_ahf_flag
from study_ahf_v4_2.cohort_093a_strict_pre_t0_ahf_only_v1;

create index if not exists idx_093b_base_ahf_only_stay
    on study_ahf_v4_2.model_070a_base_index_ahf_only_v1 (stay_id);

analyze study_ahf_v4_2.model_070a_base_index_ahf_only_v1;

select
    count(*) as n_total,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / nullif(count(*), 0), 2) as event_rate_pct
from study_ahf_v4_2.model_070a_base_index_ahf_only_v1;
