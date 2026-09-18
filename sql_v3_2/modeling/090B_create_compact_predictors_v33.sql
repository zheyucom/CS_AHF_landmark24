-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- File: sql_v3_2/modeling/090B_create_compact_predictors_v33.sql
-- Purpose:
--   Build the prespecified compact no-leakage predictor set for the
--   primary Fine-Gray model.
--
-- Base:
--   study_ahf_v3_2.model_090A_modeling_base_v33_v1, n = 5,555.
--
-- Contract:
--   - 45 prespecified predictors.
--   - No AHF qualification variables.
--   - No sepsis/SOFA qualification variables.
--   - No pre12 overt-CS qualification variables.
--   - No label/follow-up/final-state/time-to-event fields.
--   - No outcome-derived baseline support aggregates.
--   - Lactate uses raw labevents itemid 50813. Audit 114 found 550
--     valid ICU 0-12 h raw lactate records absent from derived.bg.
-- ============================================================

drop table if exists study_ahf_v3_2.model_090B_compact_predictors_v33_v1 cascade;
drop table if exists study_ahf_v3_2.model_090B_predictor_manifest_v33_v1 cascade;

create table study_ahf_v3_2.model_090B_predictor_manifest_v33_v1 (
    predictor_name text primary key,
    feature_group text not null,
    source_table text not null,
    window_rule text not null,
    clinical_meaning text not null,
    primary_model_flag integer not null default 1
);

insert into study_ahf_v3_2.model_090B_predictor_manifest_v33_v1 (
    predictor_name, feature_group, source_table, window_rule, clinical_meaning
)
values
    ('age', 'demographics', 'mimiciv_hosp.patients', 'baseline at ICU admission', 'Age at index ICU admission'),
    ('female', 'demographics', 'mimiciv_hosp.patients', 'baseline at ICU admission', 'Female sex'),
    ('first_unit_micu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline at ICU admission', 'First ICU care unit is medical ICU'),
    ('first_unit_ccu_cicu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline at ICU admission', 'First ICU care unit is cardiac/coronary ICU'),
    ('first_unit_sicu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline at ICU admission', 'First ICU care unit is surgical ICU'),
    ('first_unit_cvicu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline at ICU admission', 'First ICU care unit is cardiac vascular ICU'),
    ('hr_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Mean heart rate'),
    ('hr_max', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Maximum heart rate'),
    ('mbp_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Mean arterial pressure'),
    ('mbp_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Minimum arterial pressure'),
    ('sbp_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Minimum systolic blood pressure'),
    ('rr_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Mean respiratory rate'),
    ('rr_max', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Maximum respiratory rate'),
    ('spo2_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Mean oxygen saturation'),
    ('spo2_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Minimum oxygen saturation'),
    ('temp_max', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Maximum temperature'),
    ('map_lt65_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Proportion of valid MAP records below 65 mmHg'),
    ('sbp_lt90_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Proportion of valid SBP records below 90 mmHg'),
    ('hr_gt110_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Proportion of valid HR records above 110 bpm'),
    ('rr_gt24_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Proportion of valid RR records above 24/min'),
    ('spo2_lt90_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Proportion of valid SpO2 records below 90%'),
    ('shock_index_max', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Maximum heart rate divided by systolic blood pressure'),
    ('pulse_pressure_min', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Minimum systolic minus diastolic pressure'),
    ('mbp_slope_per_hour', 'vital_trend', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Linear MAP slope per hour'),
    ('lactate_max', 'labs', 'mimiciv_hosp.labevents itemid 50813', '[T0,T12)', 'Maximum lactate'),
    ('lactate_delta', 'labs', 'mimiciv_hosp.labevents itemid 50813', '[T0,T12)', 'Last minus first lactate'),
    ('ph_min', 'labs', 'mimiciv_derived.bg', '[T0,T12)', 'Minimum pH'),
    ('baseexcess_min', 'labs', 'mimiciv_derived.bg', '[T0,T12)', 'Minimum base excess'),
    ('dbp_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Minimum diastolic blood pressure'),
    ('modified_shock_index_max', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)', 'Maximum heart rate divided by mean arterial pressure'),
    ('creatinine_max', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Maximum creatinine'),
    ('creatinine_delta', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Last minus first creatinine'),
    ('bun_max', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Maximum blood urea nitrogen'),
    ('sodium_min', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Minimum sodium'),
    ('sodium_max', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Maximum sodium'),
    ('potassium_min', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Minimum potassium'),
    ('potassium_max', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Maximum potassium'),
    ('chem_bicarbonate_min', 'labs', 'mimiciv_derived.chemistry', '[T0,T12)', 'Minimum chemistry bicarbonate'),
    ('wbc_max', 'labs', 'mimiciv_derived.complete_blood_count', '[T0,T12)', 'Maximum white blood cell count'),
    ('hemoglobin_min', 'labs', 'mimiciv_derived.complete_blood_count', '[T0,T12)', 'Minimum hemoglobin'),
    ('platelet_min', 'labs', 'mimiciv_derived.complete_blood_count', '[T0,T12)', 'Minimum platelet count'),
    ('inr_max', 'labs', 'mimiciv_derived.coagulation', '[T0,T12)', 'Maximum INR'),
    ('urineoutput_0_12h_total_ml', 'support', 'mimiciv_derived.urine_output', '[T0,T12)', 'Total urine output in first 12 ICU hours'),
    ('gcs_min', 'support', 'mimiciv_derived.gcs', '[T0,T12)', 'Minimum Glasgow Coma Scale'),
    ('advanced_respiratory_support_0_12h_flag', 'support', 'mimiciv_derived.ventilation', '[T0,T12)', 'Invasive ventilation, noninvasive ventilation, or high-flow oxygen in first 12 ICU hours');

create table study_ahf_v3_2.model_090B_compact_predictors_v33_v1 as
with base as (
    select b.*
    from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
),

static_features as (
    select
        b.stay_id,
        p.anchor_age as age,
        case when p.gender = 'F' then 1 else 0 end as female,
        case when lower(i.first_careunit) like '%medical%' then 1 else 0 end as first_unit_micu_flag,
        case
            when lower(i.first_careunit) like '%cardiac%'
              or lower(i.first_careunit) like '%coronary%'
            then 1 else 0
        end as first_unit_ccu_cicu_flag,
        case when lower(i.first_careunit) like '%surgical%' then 1 else 0 end as first_unit_sicu_flag,
        case
            when lower(i.first_careunit) like '%cardiac vascular%'
              or lower(i.first_careunit) like '%cvicu%'
            then 1 else 0
        end as first_unit_cvicu_flag
    from base b
    left join mimiciv_icu.icustays i
        on b.stay_id = i.stay_id
    left join mimiciv_hosp.patients p
        on b.subject_id = p.subject_id
),

vitals_raw as (
    select
        b.stay_id,
        v.charttime,
        extract(epoch from (v.charttime - b.intime)) / 3600.0 as hour_from_icu,
        case when v.heart_rate between 20 and 250 then v.heart_rate else null end as hr,
        case when v.sbp between 40 and 300 then v.sbp else null end as sbp,
        case when v.dbp between 20 and 200 then v.dbp else null end as dbp,
        case when v.mbp between 30 and 250 then v.mbp else null end as mbp,
        case when v.resp_rate between 5 and 80 then v.resp_rate else null end as rr,
        case when v.temperature between 25 and 45 then v.temperature::double precision else null end as temp,
        case when v.spo2 between 50 and 100 then v.spo2 else null end as spo2
    from base b
    left join mimiciv_derived.vitalsign v
        on b.stay_id = v.stay_id
       and v.charttime >= b.intime
       and v.charttime < b.landmark12_time
),

vitals_paired as (
    select
        *,
        case when hr is not null and sbp is not null and sbp > 0 then hr / sbp else null end as shock_index,
        case when hr is not null and mbp is not null and mbp > 0 then hr / mbp else null end as modified_shock_index,
        case when sbp is not null and dbp is not null and sbp >= dbp then sbp - dbp else null end as pulse_pressure
    from vitals_raw
),

vitals_summary as (
    select
        stay_id,
        avg(hr) as hr_mean,
        max(hr) as hr_max,
        avg(mbp) as mbp_mean,
        min(mbp) as mbp_min,
        min(sbp) as sbp_min,
        min(dbp) as dbp_min,
        avg(rr) as rr_mean,
        max(rr) as rr_max,
        avg(spo2) as spo2_mean,
        min(spo2) as spo2_min,
        max(temp) as temp_max,
        avg(case when mbp is not null then case when mbp < 65 then 1.0 else 0.0 end else null end) as map_lt65_record_prop,
        avg(case when sbp is not null then case when sbp < 90 then 1.0 else 0.0 end else null end) as sbp_lt90_record_prop,
        avg(case when hr is not null then case when hr > 110 then 1.0 else 0.0 end else null end) as hr_gt110_record_prop,
        avg(case when rr is not null then case when rr > 24 then 1.0 else 0.0 end else null end) as rr_gt24_record_prop,
        avg(case when spo2 is not null then case when spo2 < 90 then 1.0 else 0.0 end else null end) as spo2_lt90_record_prop,
        max(shock_index) as shock_index_max,
        max(modified_shock_index) as modified_shock_index_max,
        min(pulse_pressure) as pulse_pressure_min,
        regr_slope(mbp, hour_from_icu) filter (where mbp is not null and hour_from_icu is not null) as mbp_slope_per_hour
    from vitals_paired
    group by stay_id
),

bg_raw as (
    select
        b.stay_id,
        bg.charttime,
        case when bg.ph between 6.8 and 7.8 then bg.ph else null end as ph,
        case when bg.baseexcess between -50 and 50 then bg.baseexcess else null end as baseexcess,
        case when bg.bicarbonate between 0 and 60 then bg.bicarbonate else null end as bg_bicarbonate,
        case when bg.pao2fio2ratio between 20 and 800 then bg.pao2fio2ratio else null end as pf_ratio
    from base b
    left join mimiciv_derived.bg bg
        on b.subject_id = bg.subject_id
       and b.hadm_id = bg.hadm_id
       and bg.charttime >= b.intime
       and bg.charttime < b.landmark12_time
),

bg_summary as (
    select
        stay_id,
        min(ph) as ph_min,
        min(baseexcess) as baseexcess_min,
        min(bg_bicarbonate) as bg_bicarbonate_min,
        min(pf_ratio) as pf_ratio_min
    from bg_raw
    group by stay_id
),

raw_lactate as (
    select
        b.stay_id,
        le.charttime,
        case when le.valuenum between 0 and 30 then le.valuenum else null end as lactate
    from base b
    join mimiciv_hosp.labevents le
        on le.subject_id = b.subject_id
       and le.hadm_id = b.hadm_id
       and le.charttime >= b.intime
       and le.charttime < b.landmark12_time
       and le.itemid = 50813
),

lactate_summary as (
    select stay_id, max(lactate) as lactate_max
    from raw_lactate
    group by stay_id
),

lactate_first as (
    select distinct on (stay_id)
        stay_id,
        lactate as lactate_first
    from raw_lactate
    where lactate is not null
    order by stay_id, charttime
),

lactate_last as (
    select distinct on (stay_id)
        stay_id,
        lactate as lactate_last
    from raw_lactate
    where lactate is not null
    order by stay_id, charttime desc
),

chem_raw as (
    select
        b.stay_id,
        ch.charttime,
        case when ch.creatinine between 0.1 and 20 then ch.creatinine else null end as creatinine,
        case when ch.bun between 1 and 200 then ch.bun else null end as bun,
        case when ch.sodium between 100 and 180 then ch.sodium else null end as sodium,
        case when ch.potassium between 1.5 and 8 then ch.potassium else null end as potassium,
        case when ch.bicarbonate between 5 and 60 then ch.bicarbonate else null end as chem_bicarbonate
    from base b
    left join mimiciv_derived.chemistry ch
        on b.subject_id = ch.subject_id
       and b.hadm_id = ch.hadm_id
       and ch.charttime >= b.intime
       and ch.charttime < b.landmark12_time
),

chem_summary as (
    select
        stay_id,
        max(creatinine) as creatinine_max,
        max(bun) as bun_max,
        min(sodium) as sodium_min,
        max(sodium) as sodium_max,
        min(potassium) as potassium_min,
        max(potassium) as potassium_max,
        min(chem_bicarbonate) as chem_bicarbonate_min
    from chem_raw
    group by stay_id
),

creatinine_first as (
    select distinct on (stay_id)
        stay_id,
        creatinine as creatinine_first
    from chem_raw
    where creatinine is not null
    order by stay_id, charttime
),

creatinine_last as (
    select distinct on (stay_id)
        stay_id,
        creatinine as creatinine_last
    from chem_raw
    where creatinine is not null
    order by stay_id, charttime desc
),

cbc_raw as (
    select
        b.stay_id,
        case when cbc.wbc between 0.1 and 200 then cbc.wbc else null end as wbc,
        case when cbc.hemoglobin between 3 and 25 then cbc.hemoglobin else null end as hemoglobin,
        case when cbc.platelet between 1 and 2000 then cbc.platelet else null end as platelet
    from base b
    left join mimiciv_derived.complete_blood_count cbc
        on b.subject_id = cbc.subject_id
       and b.hadm_id = cbc.hadm_id
       and cbc.charttime >= b.intime
       and cbc.charttime < b.landmark12_time
),

cbc_summary as (
    select
        stay_id,
        max(wbc) as wbc_max,
        min(hemoglobin) as hemoglobin_min,
        min(platelet) as platelet_min
    from cbc_raw
    group by stay_id
),

coag_raw as (
    select
        b.stay_id,
        case when co.inr between 0.5 and 20 then co.inr else null end as inr
    from base b
    left join mimiciv_derived.coagulation co
        on b.subject_id = co.subject_id
       and b.hadm_id = co.hadm_id
       and co.charttime >= b.intime
       and co.charttime < b.landmark12_time
),

coag_summary as (
    select
        stay_id,
        max(inr) as inr_max
    from coag_raw
    group by stay_id
),

uo_raw as (
    select
        b.stay_id,
        case when uo.urineoutput between 0 and 10000 then uo.urineoutput else null end as urineoutput
    from base b
    left join mimiciv_derived.urine_output uo
        on b.stay_id = uo.stay_id
       and uo.charttime >= b.intime
       and uo.charttime < b.landmark12_time
),

uo_summary as (
    select
        stay_id,
        sum(urineoutput) as urineoutput_0_12h_total_ml
    from uo_raw
    group by stay_id
),

gcs_raw as (
    select
        b.stay_id,
        case when g.gcs between 3 and 15 then g.gcs else null end as gcs
    from base b
    left join mimiciv_derived.gcs g
        on b.stay_id = g.stay_id
       and g.charttime >= b.intime
       and g.charttime < b.landmark12_time
),

gcs_summary as (
    select
        stay_id,
        min(gcs) as gcs_min
    from gcs_raw
    group by stay_id
),

vent_raw as (
    select
        b.stay_id,
        lower(coalesce(v.ventilation_status, '')) as ventilation_status
    from base b
    left join mimiciv_derived.ventilation v
        on b.stay_id = v.stay_id
       and v.starttime < b.landmark12_time
       and coalesce(v.endtime, v.starttime + interval '1 minute') > b.intime
),

vent_summary as (
    select
        stay_id,
        max(
            case
                when ventilation_status like '%invasive%'
                 and ventilation_status not like '%non%'
                then 1
                when ventilation_status like '%noninvasive%'
                  or ventilation_status like '%non-invasive%'
                  or ventilation_status like '%niv%'
                then 1
                when ventilation_status like '%high flow%'
                  or ventilation_status like '%highflow%'
                  or ventilation_status like '%hfnc%'
                then 1
                else 0
            end
        ) as advanced_respiratory_support_0_12h_flag
    from vent_raw
    group by stay_id
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,

    sf.age,
    sf.female,
    sf.first_unit_micu_flag,
    sf.first_unit_ccu_cicu_flag,
    sf.first_unit_sicu_flag,
    sf.first_unit_cvicu_flag,

    vs.hr_mean,
    vs.hr_max,
    vs.mbp_mean,
    vs.mbp_min,
    vs.sbp_min,
    vs.dbp_min,
    vs.rr_mean,
    vs.rr_max,
    vs.spo2_mean,
    vs.spo2_min,
    vs.temp_max,
    vs.map_lt65_record_prop,
    vs.sbp_lt90_record_prop,
    vs.hr_gt110_record_prop,
    vs.rr_gt24_record_prop,
    vs.spo2_lt90_record_prop,
    vs.shock_index_max,
    vs.modified_shock_index_max,
    vs.pulse_pressure_min,
    vs.mbp_slope_per_hour,

    ls.lactate_max,
    ll.lactate_last - lf.lactate_first as lactate_delta,
    bg.ph_min,
    bg.baseexcess_min,
    cs.creatinine_max,
    cl.creatinine_last - cf.creatinine_first as creatinine_delta,
    cs.bun_max,
    cs.sodium_min,
    cs.sodium_max,
    cs.potassium_min,
    cs.potassium_max,
    cs.chem_bicarbonate_min,
    cbc.wbc_max,
    cbc.hemoglobin_min,
    cbc.platelet_min,
    co.inr_max,

    uo.urineoutput_0_12h_total_ml,
    gcs.gcs_min,
    coalesce(vent.advanced_respiratory_support_0_12h_flag, 0)
        as advanced_respiratory_support_0_12h_flag

from base b
left join static_features sf on b.stay_id = sf.stay_id
left join vitals_summary vs on b.stay_id = vs.stay_id
left join bg_summary bg on b.stay_id = bg.stay_id
left join lactate_summary ls on b.stay_id = ls.stay_id
left join lactate_first lf on b.stay_id = lf.stay_id
left join lactate_last ll on b.stay_id = ll.stay_id
left join chem_summary cs on b.stay_id = cs.stay_id
left join creatinine_first cf on b.stay_id = cf.stay_id
left join creatinine_last cl on b.stay_id = cl.stay_id
left join cbc_summary cbc on b.stay_id = cbc.stay_id
left join coag_summary co on b.stay_id = co.stay_id
left join uo_summary uo on b.stay_id = uo.stay_id
left join gcs_summary gcs on b.stay_id = gcs.stay_id
left join vent_summary vent on b.stay_id = vent.stay_id;

create unique index if not exists idx_090b_compact_predictors_v33_stay
    on study_ahf_v3_2.model_090B_compact_predictors_v33_v1 (stay_id);

analyze study_ahf_v3_2.model_090B_compact_predictors_v33_v1;

insert into study_ahf_v3_2.run_manifest (
    table_name,
    sql_file,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    n_events,
    event_rate,
    time_window,
    version_tag,
    notes
)
select
    'study_ahf_v3_2.model_090B_compact_predictors_v33_v1',
    'sql_v3_2/modeling/090B_create_compact_predictors_v33.sql',
    count(*),
    count(distinct subject_id),
    count(distinct hadm_id),
    count(distinct stay_id),
    null,
    null,
    'Predictors from baseline or [T0,T12), labels physically separated',
    '090B_v33',
    'Prespecified compact 45-predictor feature table for primary Fine-Gray model. No AHF/sepsis/pre12-overt-CS qualification variables or post-landmark outcome fields.'
from study_ahf_v3_2.model_090B_compact_predictors_v33_v1;
