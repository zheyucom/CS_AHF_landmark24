-- Export artifacts for the 099 AHF phenotype audit.
\set ON_ERROR_STOP on

\o project_control/runs/20260828_ahf_phenotype_audit/reports/099_QC1_evidence_patterns.csv
select
    evidence_pattern,
    count(*) as n_stays,
    sum(primary_event_flag) as n_events,
    round(avg(primary_event_flag::numeric) * 100, 2) as event_rate_pct
from (
    select
        case
            when strict_ahf_pre_t0_admission_flag = 0
             and hf_icd_acute_or_acute_on_chronic = 1
                then '00_acute_hf_icd_no_pre_t0_objective_evidence'
            when strict_ahf_pre_t0_admission_flag = 0
             and hf_icd_acute_or_acute_on_chronic = 0
                then '01_nonacute_or_other_hf_anchor'
            when actual_iv_loop_emar_pre_t0_flag = 1
             and ntprobnp_ge300_pre_t0_flag = 1
                then '02_loop_emar_plus_ntprobnp_ge300'
            when actual_iv_loop_emar_pre_t0_flag = 1
                then '03_loop_emar_only'
            when ntprobnp_ge300_pre_t0_flag = 1
                then '04_ntprobnp_ge300_only'
            else '05_other_pre_t0_pattern'
        end as evidence_pattern,
        primary_event_flag
    from study_ahf_v3_2.audit_099_ahf_phenotype_v1
) x
group by evidence_pattern
order by evidence_pattern;
\o

\o project_control/runs/20260828_ahf_phenotype_audit/reports/099_QC2_biomarker_and_loop_cross_tab.csv
select
    strict_ahf_pre_t0_admission_flag,
    ntprobnp_measured_pre_t0_flag,
    ntprobnp_ge300_pre_t0_flag,
    actual_iv_loop_emar_pre_t0_flag,
    count(*) as n_stays,
    sum(primary_event_flag) as n_events,
    round(avg(primary_event_flag::numeric) * 100, 2) as event_rate_pct
from study_ahf_v3_2.audit_099_ahf_phenotype_v1
group by 1, 2, 3, 4
order by 1, 2, 3, 4;
\o

\o project_control/runs/20260828_ahf_phenotype_audit/reports/099_QC3_diagnosis_strata.csv
select
    diagnosis_stratum,
    count(*) as n_stays,
    sum(primary_event_flag) as n_events,
    round(avg(primary_event_flag::numeric) * 100, 2) as event_rate_pct,
    sum(strict_ahf_pre_t0_admission_flag) as n_strict_pre_t0_ahf,
    sum(strict_ahf_bnponly_pre_t0_flag) as n_bnponly
from (
    select
        case
            when acute_coronary_syndrome_flag = 1 then '01_ACS_or_AMI'
            when pulmonary_embolism_flag = 1 then '02_pulmonary_embolism'
            when renal_disease_flag = 1 then '03_AKI_CKD_or_dialysis'
            when pneumonia_or_ards_flag = 1 then '04_pneumonia_or_ARDS'
            when copd_asthma_flag = 1 then '05_COPD_or_asthma'
            when liver_disease_or_cirrhosis_flag = 1 then '06_liver_disease_or_cirrhosis'
            else '00_none_of_screened_diagnoses'
        end as diagnosis_stratum,
        primary_event_flag,
        strict_ahf_pre_t0_admission_flag,
        strict_ahf_bnponly_pre_t0_flag
    from study_ahf_v3_2.audit_099_ahf_phenotype_v1
) x
group by diagnosis_stratum
order by diagnosis_stratum;
\o

\o project_control/runs/20260828_ahf_phenotype_audit/reports/099_QC4_candidate_cohorts.csv
select
    'recommended_pre_t0_admission_to_t0' as cohort,
    count(*) as n_stays,
    sum(primary_event_flag) as n_events,
    sum(acute_coronary_syndrome_flag) as n_acs,
    sum(renal_disease_flag) as n_renal,
    sum(pulmonary_embolism_flag) as n_pe,
    sum(pneumonia_or_ards_flag) as n_pneumonia_ards,
    sum(copd_asthma_flag) as n_copd_asthma,
    sum(liver_disease_or_cirrhosis_flag) as n_liver,
    sum(strict_ahf_bnponly_pre_t0_flag) as n_bnponly
from study_ahf_v3_2.audit_099_ahf_phenotype_v1
where strict_ahf_pre_t0_admission_flag = 1
union all
select
    'strict_pre_t0_24h_sensitivity',
    count(*),
    sum(primary_event_flag),
    sum(acute_coronary_syndrome_flag),
    sum(renal_disease_flag),
    sum(pulmonary_embolism_flag),
    sum(pneumonia_or_ards_flag),
    sum(copd_asthma_flag),
    sum(liver_disease_or_cirrhosis_flag),
    sum(strict_ahf_bnponly_pre_t0_flag)
from study_ahf_v3_2.audit_099_ahf_phenotype_v1
where strict_ahf_pre_t0_24h_flag = 1;
\o

\o project_control/runs/20260828_ahf_phenotype_audit/data/099_stay_level_ahf_phenotype_audit.csv
select *
from study_ahf_v3_2.audit_099_ahf_phenotype_v1
order by stay_id;
\o
