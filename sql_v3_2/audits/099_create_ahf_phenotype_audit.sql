-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql_v3_2/audits/099_create_ahf_phenotype_audit.sql
-- Purpose:
--   Audit whether the v3.3 landmark risk set represents an
--   operational acute-heart-failure phenotype rather than a
--   BNP-only or discharge-ICD-only cohort.
--
-- Important:
--   This is an audit only. It does not alter the v3.3 cohort,
--   labels, predictors, or model results.
--
-- Design:
--   1) Recompute AHF evidence before T0 from the index admission.
--   2) Separate NT-proBNP measured from NT-proBNP >=300.
--   3) Prefer actual IV loop eMAR over prescription evidence.
--   4) Flag common alternative/concurrent diagnoses for audit only.
--      These diagnoses are not automatically excluded because ACS,
--      CKD, pulmonary disease, and AHF may coexist.
-- ============================================================

drop table if exists study_ahf_v3_2.audit_099_ahf_phenotype_v1 cascade;

create table study_ahf_v3_2.audit_099_ahf_phenotype_v1 as
with riskset as (
    select
        l.stay_id,
        l.subject_id,
        l.hadm_id,
        l.intime,
        l.outtime,
        l.final_state,
        l.event_type,
        case when l.final_state = 'event' then 1 else 0 end as primary_event_flag,
        case when l.final_state = 'compete' then 1 else 0 end as alive_icu_discharge_flag,
        ad.admittime,
        ad.dischtime,
        ad.deathtime
    from study_ahf_v3_2.model_098_strict_label_v33_v1 l
    inner join mimiciv_hosp.admissions ad
        on l.hadm_id = ad.hadm_id
    where l.landmark_ineligible_flag = 0
),

hf_anchor as (
    select
        r.*,
        a.hf_icd_any,
        a.hf_icd_acute_or_acute_on_chronic,
        a.hf_icd_primary_seq,
        a.hf_icd_seq_le5,
        a.hf_icd_codes,
        a.hf_icd_titles
    from riskset r
    inner join study_ahf_v3_2.cohort_061a_ahf_evidence_early_window_12h_v1 a
        on r.stay_id = a.stay_id
),

loop_evidence as (
    select
        b.stay_id,
        min(e.charttime) filter (
            where e.charttime >= b.admittime
              and e.charttime < b.intime
        ) as first_loop_emar_adm_to_t0,
        min(e.charttime) filter (
            where e.charttime >= b.intime - interval '24 hour'
              and e.charttime < b.intime
        ) as first_loop_emar_pre24,
        count(*) filter (
            where e.charttime >= b.admittime
              and e.charttime < b.intime
        ) as loop_emar_n_adm_to_t0
    from hf_anchor b
    inner join mimiciv_hosp.emar e
        on b.subject_id = e.subject_id
       and b.hadm_id = e.hadm_id
    left join mimiciv_hosp.emar_detail ed
        on e.emar_id = ed.emar_id
       and e.emar_seq = ed.emar_seq
    where e.charttime < b.intime
      and e.charttime >= b.admittime
      and (
            lower(coalesce(e.medication, '')) like '%furosemide%'
         or lower(coalesce(e.medication, '')) like '%bumetanide%'
         or lower(coalesce(e.medication, '')) like '%torsemide%'
         or lower(coalesce(e.medication, '')) like '%ethacrynic%'
         or lower(coalesce(ed.product_description, '')) like '%furosemide%'
         or lower(coalesce(ed.product_description, '')) like '%bumetanide%'
         or lower(coalesce(ed.product_description, '')) like '%torsemide%'
         or lower(coalesce(ed.product_description, '')) like '%ethacrynic%'
      )
      and (
            upper(coalesce(ed.route, '')) in ('IV', 'INTRAVENOUS')
         or lower(coalesce(ed.product_description, '')) like '%vial%'
         or lower(coalesce(ed.product_description, '')) like '%syringe%'
         or lower(coalesce(ed.product_description, '')) like '%inject%'
         or lower(coalesce(ed.product_description, '')) like '%infusion%'
         or lower(coalesce(ed.product_description, '')) like '%solution%'
         or lower(coalesce(ed.product_description, '')) like '%bag%'
         or lower(coalesce(ed.product_description, '')) like '%premix%'
         or lower(coalesce(ed.product_description, '')) like '%ampule%'
      )
      and lower(coalesce(e.event_txt, '')) not like '%not given%'
      and lower(coalesce(e.event_txt, '')) not like '%hold%'
      and lower(coalesce(ed.complete_dose_not_given, '')) not in ('yes', 'y', 'true', '1')
    group by b.stay_id
),

loop_prescription as (
    select
        b.stay_id,
        min(p.starttime) as first_loop_rx_adm_to_t0,
        count(*) as loop_rx_n_adm_to_t0
    from hf_anchor b
    inner join mimiciv_hosp.prescriptions p
        on b.subject_id = p.subject_id
       and b.hadm_id = p.hadm_id
    where p.starttime >= b.admittime
      and p.starttime < b.intime
      and (
            lower(p.drug) like '%furosemide%'
         or lower(p.drug) like '%bumetanide%'
         or lower(p.drug) like '%torsemide%'
         or lower(p.drug) like '%ethacrynic%'
      )
      and (
            upper(coalesce(p.route, '')) like '%IV%'
         or upper(coalesce(p.route, '')) like '%INTRAVENOUS%'
         or upper(coalesce(p.route, '')) like '%INJ%'
      )
    group by b.stay_id
),

ntprobnp_evidence as (
    select
        b.stay_id,
        count(*) filter (
            where le.charttime >= b.admittime
              and le.charttime < b.intime
        ) as ntprobnp_n_adm_to_t0,
        min(le.charttime) filter (
            where le.charttime >= b.admittime
              and le.charttime < b.intime
        ) as first_ntprobnp_adm_to_t0,
        max(le.valuenum) filter (
            where le.charttime >= b.admittime
              and le.charttime < b.intime
        ) as ntprobnp_max_adm_to_t0,
        count(*) filter (
            where le.charttime >= b.intime - interval '24 hour'
              and le.charttime < b.intime
        ) as ntprobnp_n_pre24,
        max(le.valuenum) filter (
            where le.charttime >= b.intime - interval '24 hour'
              and le.charttime < b.intime
        ) as ntprobnp_max_pre24
    from hf_anchor b
    inner join mimiciv_hosp.labevents le
        on b.subject_id = le.subject_id
       and b.hadm_id = le.hadm_id
    where le.itemid = 50963
      and le.valuenum is not null
      and le.charttime >= b.admittime
      and le.charttime < b.intime
    group by b.stay_id
),

dx_flags as (
    select
        b.stay_id,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') in
                 ('410','4100','41000','41001','41002','4101','41010','41011','41012',
                  '4102','41020','41021','41022','4103','41030','41031','41032',
                  '4104','41040','41041','41042','4105','41050','41051','41052',
                  '4106','41060','41061','41062','4107','41070','41071','41072',
                  '4108','41080','41081','41082','4109','41090','41091','41092')
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'I21%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'I22%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'I23%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'I24%'
                then 1
            else 0
        end) as acute_coronary_syndrome_flag,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '585%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'N17%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'N18%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) = 'Z992'
                then 1
            else 0
        end) as renal_disease_flag,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '4151%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'I26%'
                then 1
            else 0
        end) as pulmonary_embolism_flag,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '491%'
                then 1
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '492%'
                then 1
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '493%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'J44%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'J45%'
                then 1
            else 0
        end) as copd_asthma_flag,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '48%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'J1%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'J80%'
                then 1
            else 0
        end) as pneumonia_or_ards_flag,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '571%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'K72%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'K74%'
                then 1
            else 0
        end) as liver_disease_or_cirrhosis_flag,
        max(case
            when d.icd_version = 9
             and regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g') like '42731%'
                then 1
            when d.icd_version = 10
             and upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) like 'I48%'
                then 1
            else 0
        end) as atrial_fibrillation_flag
    from hf_anchor b
    left join mimiciv_hosp.diagnoses_icd d
        on b.hadm_id = d.hadm_id
    group by b.stay_id
),

flags as (
    select
        h.*,
        coalesce(le.first_loop_emar_adm_to_t0 is not null, false)::int
            as actual_iv_loop_emar_pre_t0_flag,
        coalesce(le.first_loop_emar_pre24 is not null, false)::int
            as actual_iv_loop_emar_pre24_flag,
        coalesce(lr.first_loop_rx_adm_to_t0 is not null, false)::int
            as iv_loop_prescription_pre_t0_flag,
        coalesce(ne.ntprobnp_n_adm_to_t0, 0)::bigint
            as ntprobnp_n_adm_to_t0,
        coalesce(ne.ntprobnp_n_pre24, 0)::bigint
            as ntprobnp_n_pre24,
        ne.first_ntprobnp_adm_to_t0,
        ne.ntprobnp_max_adm_to_t0,
        ne.ntprobnp_max_pre24,
        case when coalesce(ne.ntprobnp_n_adm_to_t0, 0) > 0 then 1 else 0 end
            as ntprobnp_measured_pre_t0_flag,
        case when ne.ntprobnp_max_adm_to_t0 >= 300 then 1 else 0 end
            as ntprobnp_ge300_pre_t0_flag,
        case when ne.ntprobnp_max_pre24 >= 300 then 1 else 0 end
            as ntprobnp_ge300_pre24_flag,
        case
            when h.hf_icd_acute_or_acute_on_chronic = 1
             and h.hf_icd_seq_le5 = 1
             and (
                    le.first_loop_emar_adm_to_t0 is not null
                 or ne.ntprobnp_max_adm_to_t0 >= 300
             )
            then 1 else 0
        end as strict_ahf_pre_t0_admission_flag,
        case
            when h.hf_icd_acute_or_acute_on_chronic = 1
             and h.hf_icd_seq_le5 = 1
             and (
                    le.first_loop_emar_pre24 is not null
                 or ne.ntprobnp_max_pre24 >= 300
             )
            then 1 else 0
        end as strict_ahf_pre_t0_24h_flag
    from hf_anchor h
    left join loop_evidence le on h.stay_id = le.stay_id
    left join loop_prescription lr on h.stay_id = lr.stay_id
    left join ntprobnp_evidence ne on h.stay_id = ne.stay_id
)

select
    f.*,
    coalesce(d.acute_coronary_syndrome_flag, 0) as acute_coronary_syndrome_flag,
    coalesce(d.renal_disease_flag, 0) as renal_disease_flag,
    coalesce(d.pulmonary_embolism_flag, 0) as pulmonary_embolism_flag,
    coalesce(d.copd_asthma_flag, 0) as copd_asthma_flag,
    coalesce(d.pneumonia_or_ards_flag, 0) as pneumonia_or_ards_flag,
    coalesce(d.liver_disease_or_cirrhosis_flag, 0) as liver_disease_or_cirrhosis_flag,
    coalesce(d.atrial_fibrillation_flag, 0) as atrial_fibrillation_flag,
    case
        when f.strict_ahf_pre_t0_admission_flag = 1
         and f.actual_iv_loop_emar_pre_t0_flag = 0
         and f.ntprobnp_ge300_pre_t0_flag = 1
        then 1 else 0
    end as strict_ahf_bnponly_pre_t0_flag
from flags f
left join dx_flags d on f.stay_id = d.stay_id;

create index if not exists idx_099_ahf_phenotype_stay
    on study_ahf_v3_2.audit_099_ahf_phenotype_v1 (stay_id);

analyze study_ahf_v3_2.audit_099_ahf_phenotype_v1;

-- QC1: evidence combinations and event rates.
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
                then '00_acute_hf_icd_no_legal_pre_t0_objective_evidence'
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

-- QC2: comparison of measured NT-proBNP versus thresholded NT-proBNP.
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

-- QC3: common concurrent/alternative diagnoses. These are audit strata,
-- not automatic exclusions.
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

-- QC4: cross-tab of screened diagnoses among the recommended candidate
-- pre-T0 AHF cohort.
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
