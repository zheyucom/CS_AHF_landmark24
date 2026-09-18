-- ============================================================
-- Project: CS_AHF_landmark24
-- Purpose: Extract auditable pre-T0 radiology support for AHF.
--
-- This is phenotype validation only. It does not alter the cohort,
-- outcome labels, or predictor tables. The report must be charted
-- after hospital admission and before ICU intime.
-- ============================================================

drop table if exists study_ahf_v3_2.audit_101_pre_t0_radiology_ahf_evidence_v1 cascade;

create table study_ahf_v3_2.audit_101_pre_t0_radiology_ahf_evidence_v1 as
with eligible as (
    select
        l.stay_id,
        l.subject_id,
        l.hadm_id,
        l.intime,
        a.admittime
    from study_ahf_v3_2.model_098_strict_label_v33_v1 l
    join mimiciv_hosp.admissions a on a.hadm_id = l.hadm_id
    where l.landmark_ineligible_flag = 0
),
source as (
    select
        e.stay_id,
        e.subject_id,
        e.hadm_id,
        r.note_id,
        r.note_type,
        r.note_seq,
        r.charttime,
        r.storetime,
        r.text,
        regexp_replace(lower(coalesce(r.text, '')), '[^a-z0-9]+', ' ', 'g') as normalized_text
    from eligible e
    join mimiciv_note.radiology r
      on r.subject_id = e.subject_id
     and r.hadm_id = e.hadm_id
     and r.charttime >= e.admittime
     and r.charttime < e.intime
),
hits as (
    select
        s.*,
        (s.normalized_text ~ '(pulmonary edema|interstitial edema|interstitial pulmonary edema|alveolar edema)')::int as pulmonary_edema_hit,
        (s.normalized_text ~ '(vascular congestion|pulmonary vascular congestion|cephalization|vascular engorgement)')::int as vascular_congestion_hit,
        (s.normalized_text ~ '(pleural effusion|pleural fluid|bilateral effusions)')::int as pleural_effusion_hit,
        (s.normalized_text ~ '(cardiomegaly|enlarged cardiac silhouette|enlarged heart)')::int as cardiomegaly_hit,
        (s.normalized_text ~ '(no pulmonary edema|without pulmonary edema|no evidence of edema|no edema)')::int as pulmonary_edema_negation_hit,
        (s.normalized_text ~ '(no vascular congestion|without vascular congestion)')::int as vascular_congestion_negation_hit,
        (s.normalized_text ~ '(no pleural effusion|without pleural effusion)')::int as pleural_effusion_negation_hit,
        (s.normalized_text ~ '(no cardiomegaly|without cardiomegaly)')::int as cardiomegaly_negation_hit,
        (s.normalized_text ~ '(possible|probable|cannot exclude|may represent|suggestive of|question of)')::int as uncertainty_hit
    from source s
)
select
    h.stay_id,
    h.subject_id,
    h.hadm_id,
    h.note_id,
    h.note_type,
    h.note_seq,
    h.charttime,
    h.storetime,
    h.text,
    h.pulmonary_edema_hit,
    h.vascular_congestion_hit,
    h.pleural_effusion_hit,
    h.cardiomegaly_hit,
    case when h.pulmonary_edema_negation_hit = 1
                or h.vascular_congestion_negation_hit = 1
              then 1 else 0 end as explicit_negation_hit,
    h.uncertainty_hit,
    case when (h.pulmonary_edema_hit = 1 and h.pulmonary_edema_negation_hit = 0)
                 or (h.vascular_congestion_hit = 1 and h.vascular_congestion_negation_hit = 0)
              then 1 else 0 end as positive_congestion_evidence_flag,
    'radiology_regex_v1; pre_t0=admittime<=charttime<intime'::text as rule_version
from hits h;

create index if not exists idx_101_radiology_stay
    on study_ahf_v3_2.audit_101_pre_t0_radiology_ahf_evidence_v1 (stay_id);

analyze study_ahf_v3_2.audit_101_pre_t0_radiology_ahf_evidence_v1;

select
    count(*) as n_radiology_reports,
    count(distinct stay_id) as n_stays_with_report,
    count(distinct stay_id) filter (where positive_congestion_evidence_flag = 1) as n_stays_with_positive_congestion,
    count(distinct stay_id) filter (where explicit_negation_hit = 1) as n_stays_with_explicit_negation
from study_ahf_v3_2.audit_101_pre_t0_radiology_ahf_evidence_v1;
