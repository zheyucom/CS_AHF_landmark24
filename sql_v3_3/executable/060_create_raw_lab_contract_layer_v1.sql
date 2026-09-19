-- ============================================================
-- Project: CS_AHF_landmark24 v3.3
-- Purpose: Versioned, patient-level raw MIMIC-IV laboratory contract layer.
-- Status: database_qc pending; this file must not be promoted to ACTIVE yet.
-- Evidence: mimic-code commit 303d26c623dcc9c49cc0f204468d4acc2f063797.
--
-- Design invariants:
--   * raw labevents and exact d_labitems metadata are authoritative;
--   * availability_time is max(charttime, storetime), never charttime alone;
--   * original values and censored bounds remain available for audit;
--   * only exact numeric values inside the cited official analysis range
--     populate analysis_value;
--   * wrong fluid, unknown unit, reversed times, missing specimen and
--     specimen_id x itemid duplicates are quarantined, never silently dropped.
-- ============================================================

create schema if not exists study_ahf_v3_3;

drop table if exists study_ahf_v3_3.lab_eligible_v1 cascade;
drop table if exists study_ahf_v3_3.lab_event_classified_v1 cascade;
drop table if exists study_ahf_v3_3.lab_quarantine_item_v1 cascade;
drop table if exists study_ahf_v3_3.lab_contract_v1 cascade;

create table study_ahf_v3_3.lab_contract_v1 (
    concept text primary key,
    itemid integer unique not null,
    expected_label text not null,
    expected_fluid text not null,
    expected_category text not null,
    unit_policy text not null check (unit_policy in ('exact_allowlist', 'dimensionless_null')),
    allowed_units text[] not null,
    official_lower double precision,
    official_lower_inclusive boolean,
    official_upper double precision,
    official_upper_inclusive boolean,
    range_source text,
    contract_version text not null
);

insert into study_ahf_v3_3.lab_contract_v1 values
    ('base_excess', 50802, 'Base Excess', 'Blood', 'Blood Gas', 'exact_allowlist', array['mEq/L'], null, null, null, null, 'mimic-code bg.sql: no range', '1.1.0'),
    ('lactate', 50813, 'Lactate', 'Blood', 'Blood Gas', 'exact_allowlist', array['mmol/L'], null, null, 10000, true, 'mimic-code bg.sql', '1.1.0'),
    ('ph', 50820, 'pH', 'Blood', 'Blood Gas', 'exact_allowlist', array['units'], null, null, null, null, 'mimic-code bg.sql: no range', '1.1.0'),
    ('bicarbonate', 50882, 'Bicarbonate', 'Blood', 'Chemistry', 'exact_allowlist', array['mEq/L'], 0, false, 10000, true, 'mimic-code chemistry.sql', '1.1.0'),
    ('creatinine', 50912, 'Creatinine', 'Blood', 'Chemistry', 'exact_allowlist', array['mg/dL'], 0, false, 150, true, 'mimic-code chemistry.sql', '1.1.0'),
    ('ntprobnp', 50963, 'NTproBNP', 'Blood', 'Chemistry', 'exact_allowlist', array['pg/mL'], null, null, null, null, 'project semantic contract: no range', '1.1.0'),
    ('potassium', 50971, 'Potassium', 'Blood', 'Chemistry', 'exact_allowlist', array['mEq/L'], 0, false, 30, true, 'mimic-code chemistry.sql', '1.1.0'),
    ('sodium', 50983, 'Sodium', 'Blood', 'Chemistry', 'exact_allowlist', array['mEq/L'], 0, false, 200, true, 'mimic-code chemistry.sql', '1.1.0'),
    ('troponin_t', 51003, 'Troponin T', 'Blood', 'Chemistry', 'exact_allowlist', array['ng/mL'], null, null, null, null, 'project semantic contract: no range', '1.1.0'),
    ('bun', 51006, 'Urea Nitrogen', 'Blood', 'Chemistry', 'exact_allowlist', array['mg/dL'], 0, false, 300, true, 'mimic-code chemistry.sql', '1.1.0'),
    ('hemoglobin', 51222, 'Hemoglobin', 'Blood', 'Hematology', 'exact_allowlist', array['g/dL'], 0, false, null, null, 'mimic-code complete_blood_count.sql', '1.1.0'),
    ('inr', 51237, 'INR(PT)', 'Blood', 'Hematology', 'dimensionless_null', array[]::text[], null, null, null, null, 'mimic-code coagulation.sql: no range', '1.1.0'),
    ('platelet', 51265, 'Platelet Count', 'Blood', 'Hematology', 'exact_allowlist', array['K/uL'], 0, false, null, null, 'mimic-code complete_blood_count.sql', '1.1.0'),
    ('wbc', 51301, 'White Blood Cells', 'Blood', 'Hematology', 'exact_allowlist', array['K/uL'], 0, false, null, null, 'mimic-code complete_blood_count.sql', '1.1.0');

create table study_ahf_v3_3.lab_quarantine_item_v1 (
    itemid integer primary key,
    concept text not null,
    quarantine_reason text not null,
    contract_version text not null
);

insert into study_ahf_v3_3.lab_quarantine_item_v1 values
    (51104, 'bun', 'wrong_fluid_urine', '1.1.0'),
    (51045, 'bun', 'wrong_fluid_other_body_fluid', '1.1.0'),
    (50851, 'bun', 'wrong_fluid_ascites', '1.1.0'),
    (51804, 'bun', 'wrong_fluid_csf', '1.1.0'),
    (51825, 'bun', 'wrong_fluid_joint_fluid', '1.1.0'),
    (51842, 'bun', 'wrong_fluid_other_body_fluid', '1.1.0'),
    (51922, 'bun', 'wrong_fluid_pleural', '1.1.0'),
    (51951, 'bun', 'wrong_fluid_stool', '1.1.0');

create table study_ahf_v3_3.lab_event_classified_v1 as
with source_rows as (
    select
        le.labevent_id,
        le.specimen_id,
        le.subject_id,
        le.hadm_id,
        le.itemid,
        di.label,
        di.fluid,
        di.category,
        le.charttime,
        le.storetime,
        case when le.storetime < le.charttime then 1 else 0 end as storetime_before_charttime_flag,
        greatest(le.charttime, coalesce(le.storetime, le.charttime)) as availability_time,
        le.value,
        le.valuenum,
        le.valueuom,
        le.ref_range_lower,
        le.ref_range_upper,
        le.flag,
        le.priority,
        le.comments,
        lc.concept,
        lc.expected_label,
        lc.expected_fluid,
        lc.expected_category,
        lc.unit_policy,
        lc.allowed_units,
        lc.official_lower,
        lc.official_lower_inclusive,
        lc.official_upper,
        lc.official_upper_inclusive,
        qi.quarantine_reason as known_quarantine_reason,
        count(*) over (partition by le.specimen_id, le.itemid) as specimen_itemid_count
    from mimiciv_hosp.labevents le
    left join mimiciv_hosp.d_labitems di
        on le.itemid = di.itemid
    left join study_ahf_v3_3.lab_contract_v1 lc
        on le.itemid = lc.itemid
    left join study_ahf_v3_3.lab_quarantine_item_v1 qi
        on le.itemid = qi.itemid
    where le.itemid in (
        50802, 50813, 50820, 50882, 50912, 50963, 50971,
        50983, 51003, 51006, 51222, 51237, 51265, 51301,
        51104, 51045, 50851, 51804, 51825, 51842, 51922, 51951
    )
),
parsed as (
    select
        s.*,
        case
            when trim(coalesce(s.value, '')) ~ '^>\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*$' then 'right_censored'
            when trim(coalesce(s.value, '')) ~ '^<\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*$' then 'left_censored'
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*(?:-|to)\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$' then 'interval_censored'
            when s.valuenum is not null then 'exact_numeric'
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$' then 'exact_numeric'
            when nullif(trim(coalesce(s.value, '')), '') is null then 'missing_result'
            else 'non_numeric_text'
        end as result_class,
        case
            when trim(coalesce(s.value, '')) like '>%' then 'right'
            when trim(coalesce(s.value, '')) like '<%' then 'left'
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*(?:-|to)\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$' then 'interval'
            else null
        end as censor_type,
        case
            when trim(coalesce(s.value, '')) ~ '^>\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*$'
                then substring(trim(s.value) from '^>\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*$')::double precision
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*(?:-|to)\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$'
                then substring(trim(s.value) from '^\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*(?:-|to)')::double precision
            when s.valuenum is not null then s.valuenum
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$' then trim(s.value)::double precision
            else null
        end as lower_bound,
        case
            when trim(coalesce(s.value, '')) ~ '^<\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*$'
                then substring(trim(s.value) from '^<\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*$')::double precision
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\s*(?:-|to)\s*[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$'
                then substring(trim(s.value) from '(?:-|to)\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\s*$')::double precision
            when s.valuenum is not null then s.valuenum
            when trim(coalesce(s.value, '')) ~ '^[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$' then trim(s.value)::double precision
            else null
        end as upper_bound
    from source_rows s
),
classified as (
    select
        p.*,
        case
            when p.known_quarantine_reason is not null then p.known_quarantine_reason
            when p.concept is null then 'unregistered_itemid'
            when p.label is distinct from p.expected_label then 'label_mismatch'
            when p.fluid is distinct from p.expected_fluid then 'fluid_mismatch'
            when p.category is distinct from p.expected_category then 'category_mismatch'
            when p.charttime is null then 'missing_charttime'
            when p.storetime_before_charttime_flag = 1 then 'storetime_before_charttime'
            when p.specimen_id is null then 'missing_specimen_id'
            when p.specimen_itemid_count > 1 then 'duplicate_specimen_itemid'
            when p.unit_policy = 'dimensionless_null'
             and (p.valueuom is null or trim(p.valueuom) = '') then null
            when p.unit_policy = 'exact_allowlist'
             and exists (
                select 1
                from unnest(p.allowed_units) allowed_unit
                where lower(trim(p.valueuom)) = lower(trim(allowed_unit))
             ) then null
            else 'unknown_unit'
        end as quarantine_reason,
        case
            when p.result_class <> 'exact_numeric' then 0
            when p.lower_bound is null then 0
            when p.official_lower is not null
             and (
                    (p.official_lower_inclusive and p.lower_bound < p.official_lower)
                 or (not p.official_lower_inclusive and p.lower_bound <= p.official_lower)
             ) then 1
            when p.official_upper is not null
             and (
                    (p.official_upper_inclusive and p.lower_bound > p.official_upper)
                 or (not p.official_upper_inclusive and p.lower_bound >= p.official_upper)
             ) then 1
            else 0
        end as official_range_outlier_flag
    from parsed p
)
select
    c.labevent_id,
    c.specimen_id,
    c.subject_id,
    c.hadm_id,
    c.itemid,
    c.concept,
    c.label,
    c.fluid,
    c.category,
    c.charttime,
    c.storetime,
    c.availability_time,
    c.value,
    c.valuenum,
    c.valueuom,
    c.ref_range_lower,
    c.ref_range_upper,
    c.flag,
    c.priority,
    c.comments,
    c.result_class,
    c.censor_type,
    c.lower_bound,
    c.upper_bound,
    c.specimen_itemid_count,
    c.official_range_outlier_flag,
    case
        when c.quarantine_reason is not null then 'quarantined:' || c.quarantine_reason
        when c.result_class in ('right_censored', 'left_censored', 'interval_censored') then 'censored_not_exact'
        when c.result_class <> 'exact_numeric' then 'result_not_exact_numeric'
        when c.official_range_outlier_flag = 1 then 'outside_official_analysis_range'
        else null
    end as analysis_exclusion_reason,
    case
        when c.quarantine_reason is null
         and c.result_class = 'exact_numeric'
         and c.official_range_outlier_flag = 0
        then c.lower_bound
        else null
    end as analysis_value,
    c.quarantine_reason
from classified c;

create index lab_event_classified_subject_hadm_time_idx
    on study_ahf_v3_3.lab_event_classified_v1
    (subject_id, hadm_id, availability_time, itemid);

create index lab_event_classified_quarantine_idx
    on study_ahf_v3_3.lab_event_classified_v1
    (quarantine_reason, analysis_exclusion_reason, itemid);

create table study_ahf_v3_3.lab_eligible_v1 as
select
    labevent_id,
    specimen_id,
    subject_id,
    hadm_id,
    itemid,
    concept,
    label,
    fluid,
    category,
    charttime,
    storetime,
    availability_time,
    value,
    valuenum,
    valueuom,
    ref_range_lower,
    ref_range_upper,
    flag,
    priority,
    comments,
    result_class,
    censor_type,
    lower_bound,
    upper_bound,
    specimen_itemid_count,
    official_range_outlier_flag,
    analysis_exclusion_reason,
    analysis_value,
    quarantine_reason
from study_ahf_v3_3.lab_event_classified_v1
where quarantine_reason is null;

create index lab_eligible_subject_hadm_time_idx
    on study_ahf_v3_3.lab_eligible_v1
    (subject_id, hadm_id, availability_time, concept);

-- Aggregate-only QC. A zero in the first three columns is required before promotion.
select
    count(*) filter (where quarantine_reason is null and specimen_id is null) as eligible_missing_specimen_n,
    count(*) filter (where quarantine_reason is null and specimen_itemid_count > 1) as eligible_duplicate_specimen_itemid_n,
    count(*) filter (where quarantine_reason is null and storetime < charttime) as eligible_reversed_time_n,
    count(*) filter (
        where quarantine_reason in (
            'wrong_fluid_urine',
            'wrong_fluid_other_body_fluid',
            'wrong_fluid_ascites',
            'wrong_fluid_csf',
            'wrong_fluid_joint_fluid',
            'wrong_fluid_pleural',
            'wrong_fluid_stool'
        )
    ) as wrong_fluid_quarantine_n,
    count(*) filter (where quarantine_reason = 'unknown_unit') as unknown_unit_quarantine_n,
    count(*) filter (where analysis_exclusion_reason = 'outside_official_analysis_range') as official_range_outlier_n,
    count(*) filter (where result_class in ('right_censored', 'left_censored', 'interval_censored')) as censored_result_n
from study_ahf_v3_3.lab_event_classified_v1;
