-- ============================================================
-- Project: CS_AHF_landmark24
-- Purpose: Create the strict pre-T0 AHF sensitivity cohort.
--
-- This table is independent of the broad v3.3 modeling input.
-- It requires:
--   1) acute or acute-on-chronic HF discharge ICD;
--   2) HF ICD minimum sequence <= 5;
--   3) actual IV loop eMAR OR NT-proBNP >= 300;
--   4) evidence between hospital admission and ICU intime.
--
-- Final diagnosis codes are retrospective phenotype anchors only.
-- None of these qualification fields may enter the predictor set.
-- ============================================================

drop table if exists study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1 cascade;

create table study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1 as
select
    a.*,
    'strict_pre_t0_ahf_admission_to_icu'::text as ahf_cohort_definition
from study_ahf_v3_2.audit_099_ahf_phenotype_v1 a
where a.strict_ahf_pre_t0_admission_flag = 1;

create unique index idx_099_strict_pre_t0_ahf_stay
    on study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1 (stay_id);

analyze study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1;

select
    count(*) as n_stays,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    sum(primary_event_flag) as n_events,
    sum(alive_icu_discharge_flag) as n_compete,
    sum(case when final_state = 'censor' then 1 else 0 end) as n_censor,
    sum(strict_ahf_bnponly_pre_t0_flag) as n_bnponly,
    sum(actual_iv_loop_emar_pre_t0_flag) as n_loop_emar,
    sum(ntprobnp_ge300_pre_t0_flag) as n_ntprobnp_ge300
from study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1;
