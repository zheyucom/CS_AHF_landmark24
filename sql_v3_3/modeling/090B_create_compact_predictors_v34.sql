-- Compact 45-predictor table revised to use the raw laboratory contract.
-- Historical v33 remains unchanged. Database execution/QC is still pending.

drop table if exists study_ahf_v3_3.model_090B_lab_episode_match_audit_v34_v1 cascade;
drop table if exists study_ahf_v3_3.model_090B_compact_predictors_v34_v1 cascade;
drop table if exists study_ahf_v3_3.model_090B_predictor_manifest_v34_v1 cascade;

create table study_ahf_v3_3.model_090B_predictor_manifest_v34_v1 (
    predictor_name text primary key,
    feature_group text not null,
    source_table text not null,
    window_rule text not null,
    primary_model_flag integer not null default 1
);

insert into study_ahf_v3_3.model_090B_predictor_manifest_v34_v1
    (predictor_name, feature_group, source_table, window_rule)
values
    ('age', 'demographics', 'mimiciv_hosp.patients', 'baseline'),
    ('female', 'demographics', 'mimiciv_hosp.patients', 'baseline'),
    ('first_unit_micu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline'),
    ('first_unit_ccu_cicu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline'),
    ('first_unit_sicu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline'),
    ('first_unit_cvicu_flag', 'icu_unit', 'mimiciv_icu.icustays', 'baseline'),
    ('hr_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('hr_max', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('mbp_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('mbp_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('sbp_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('rr_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('rr_max', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('spo2_mean', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('spo2_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('temp_max', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('map_lt65_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('sbp_lt90_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('hr_gt110_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('rr_gt24_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('spo2_lt90_record_prop', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('shock_index_max', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('pulse_pressure_min', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('mbp_slope_per_hour', 'vital_trend', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('lactate_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) by availability_time'),
    ('lactate_delta', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) exact numeric only'),
    ('ph_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) by availability_time'),
    ('baseexcess_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) by availability_time'),
    ('dbp_min', 'vitals', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('modified_shock_index_max', 'vital_burden', 'mimiciv_derived.vitalsign', '[T0,T12)'),
    ('creatinine_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) by availability_time'),
    ('creatinine_delta', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) exact numeric only'),
    ('bun_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12) blood only'),
    ('sodium_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('sodium_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('potassium_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('potassium_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('chem_bicarbonate_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('wbc_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('hemoglobin_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('platelet_min', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12)'),
    ('inr_max', 'labs', 'study_ahf_v3_3.lab_eligible_v1', '[T0,T12); dimensionless'),
    ('urineoutput_0_12h_total_ml', 'support', 'mimiciv_derived.urine_output', '[T0,T12)'),
    ('gcs_min', 'support', 'mimiciv_derived.gcs', '[T0,T12)'),
    ('advanced_respiratory_support_0_12h_flag', 'support', 'mimiciv_derived.ventilation', '[T0,T12)');

create table study_ahf_v3_3.model_090B_compact_predictors_v34_v1 as
with base as (
    select *
    from study_ahf_v3_2.model_090A_modeling_base_v33_v1
),
static_features as (
    select
        b.stay_id,
        p.anchor_age as age,
        case when p.gender = 'F' then 1 else 0 end as female,
        case when lower(i.first_careunit) like '%medical%' then 1 else 0 end as first_unit_micu_flag,
        case when lower(i.first_careunit) like '%cardiac%' or lower(i.first_careunit) like '%coronary%' then 1 else 0 end as first_unit_ccu_cicu_flag,
        case when lower(i.first_careunit) like '%surgical%' then 1 else 0 end as first_unit_sicu_flag,
        case when lower(i.first_careunit) like '%cardiac vascular%' or lower(i.first_careunit) like '%cvicu%' then 1 else 0 end as first_unit_cvicu_flag
    from base b
    left join mimiciv_icu.icustays i on b.stay_id = i.stay_id
    left join mimiciv_hosp.patients p on b.subject_id = p.subject_id
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
        case when hr is not null and sbp > 0 then hr / sbp else null end as shock_index,
        case when hr is not null and mbp > 0 then hr / mbp else null end as modified_shock_index,
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
        avg(case when mbp is not null then (mbp < 65)::integer::double precision end) as map_lt65_record_prop,
        avg(case when sbp is not null then (sbp < 90)::integer::double precision end) as sbp_lt90_record_prop,
        avg(case when hr is not null then (hr > 110)::integer::double precision end) as hr_gt110_record_prop,
        avg(case when rr is not null then (rr > 24)::integer::double precision end) as rr_gt24_record_prop,
        avg(case when spo2 is not null then (spo2 < 90)::integer::double precision end) as spo2_lt90_record_prop,
        max(shock_index) as shock_index_max,
        max(modified_shock_index) as modified_shock_index_max,
        min(pulse_pressure) as pulse_pressure_min,
        regr_slope(mbp, hour_from_icu) filter (where mbp is not null and hour_from_icu is not null) as mbp_slope_per_hour
    from vitals_paired
    group by stay_id
),
lab_episode_candidates as (
    select
        b.stay_id,
        le.labevent_id,
        le.concept,
        le.charttime,
        le.availability_time,
        le.analysis_value,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base b
    join study_ahf_v3_3.lab_eligible_v1 le
      on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.charttime >= b.intime
     and le.charttime < b.landmark12_time
     and le.availability_time >= b.intime
     and le.availability_time < b.landmark12_time
     and le.analysis_value is not null
),
lab_valid as (
    select *
    from lab_episode_candidates
    where episode_match_count = 1
),
lab_ranked as (
    select
        l.*,
        row_number() over (partition by stay_id, concept order by charttime, labevent_id) as rn_first,
        row_number() over (partition by stay_id, concept order by charttime desc, labevent_id desc) as rn_last
    from lab_valid l
),
lab_summary as (
    select
        stay_id,
        max(analysis_value) filter (where concept = 'lactate') as lactate_max,
        min(analysis_value) filter (where concept = 'ph') as ph_min,
        min(analysis_value) filter (where concept = 'base_excess') as baseexcess_min,
        max(analysis_value) filter (where concept = 'creatinine') as creatinine_max,
        max(analysis_value) filter (where concept = 'bun') as bun_max,
        min(analysis_value) filter (where concept = 'sodium') as sodium_min,
        max(analysis_value) filter (where concept = 'sodium') as sodium_max,
        min(analysis_value) filter (where concept = 'potassium') as potassium_min,
        max(analysis_value) filter (where concept = 'potassium') as potassium_max,
        min(analysis_value) filter (where concept = 'bicarbonate') as chem_bicarbonate_min,
        max(analysis_value) filter (where concept = 'wbc') as wbc_max,
        min(analysis_value) filter (where concept = 'hemoglobin') as hemoglobin_min,
        min(analysis_value) filter (where concept = 'platelet') as platelet_min,
        max(analysis_value) filter (where concept = 'inr') as inr_max,
        max(analysis_value) filter (where concept = 'lactate' and rn_first = 1) as lactate_first,
        max(analysis_value) filter (where concept = 'lactate' and rn_last = 1) as lactate_last,
        max(analysis_value) filter (where concept = 'creatinine' and rn_first = 1) as creatinine_first,
        max(analysis_value) filter (where concept = 'creatinine' and rn_last = 1) as creatinine_last
    from lab_ranked
    group by stay_id
),
lab_episode_audit as (
    select
        stay_id,
        count(*) filter (where episode_match_count > 1) as ambiguous_episode_match_n
    from lab_episode_candidates
    group by stay_id
),
uo_summary as (
    select b.stay_id, sum(uo.urineoutput) filter (where uo.urineoutput between 0 and 10000) as urineoutput_0_12h_total_ml
    from base b
    left join mimiciv_derived.urine_output uo
      on b.stay_id = uo.stay_id
     and uo.charttime >= b.intime
     and uo.charttime < b.landmark12_time
    group by b.stay_id
),
gcs_summary as (
    select b.stay_id, min(g.gcs) filter (where g.gcs between 3 and 15) as gcs_min
    from base b
    left join mimiciv_derived.gcs g
      on b.stay_id = g.stay_id
     and g.charttime >= b.intime
     and g.charttime < b.landmark12_time
    group by b.stay_id
),
vent_summary as (
    select
        b.stay_id,
        max(case
            when lower(coalesce(v.ventilation_status, '')) like '%invasive%'
             and lower(coalesce(v.ventilation_status, '')) not like '%non%' then 1
            when lower(coalesce(v.ventilation_status, '')) like any (array['%noninvasive%', '%non-invasive%', '%niv%', '%high flow%', '%highflow%', '%hfnc%']) then 1
            else 0
        end) as advanced_respiratory_support_0_12h_flag
    from base b
    left join mimiciv_derived.ventilation v
      on b.stay_id = v.stay_id
     and v.starttime < b.landmark12_time
     and coalesce(v.endtime, v.starttime + interval '1 minute') > b.intime
    group by b.stay_id
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
    ls.lactate_last - ls.lactate_first as lactate_delta,
    ls.ph_min,
    ls.baseexcess_min,
    ls.creatinine_max,
    ls.creatinine_last - ls.creatinine_first as creatinine_delta,
    ls.bun_max,
    ls.sodium_min,
    ls.sodium_max,
    ls.potassium_min,
    ls.potassium_max,
    ls.chem_bicarbonate_min,
    ls.wbc_max,
    ls.hemoglobin_min,
    ls.platelet_min,
    ls.inr_max,
    uo.urineoutput_0_12h_total_ml,
    gcs.gcs_min,
    coalesce(vent.advanced_respiratory_support_0_12h_flag, 0) as advanced_respiratory_support_0_12h_flag
from base b
left join static_features sf on b.stay_id = sf.stay_id
left join vitals_summary vs on b.stay_id = vs.stay_id
left join lab_summary ls on b.stay_id = ls.stay_id
left join uo_summary uo on b.stay_id = uo.stay_id
left join gcs_summary gcs on b.stay_id = gcs.stay_id
left join vent_summary vent on b.stay_id = vent.stay_id;

create unique index model_090b_compact_predictors_v34_stay_idx
    on study_ahf_v3_3.model_090B_compact_predictors_v34_v1 (stay_id);

create table study_ahf_v3_3.model_090B_lab_episode_match_audit_v34_v1 as
with base as (
    select * from study_ahf_v3_2.model_090A_modeling_base_v33_v1
),
episode_matches as (
    select
        b.stay_id,
        le.labevent_id,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base b
    join study_ahf_v3_3.lab_eligible_v1 le
      on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.charttime >= b.intime
     and le.charttime < b.landmark12_time
     and le.availability_time >= b.intime
     and le.availability_time < b.landmark12_time
)
select
    stay_id,
    count(*) filter (where episode_match_count > 1) as ambiguous_episode_match_n,
    case when count(*) filter (where episode_match_count > 1) > 0 then 1 else 0 end as ambiguous_episode_match
from episode_matches
group by stay_id;

-- Promotion QC: row count must equal the modeling base; ambiguity must be zero.
select
    (select count(*) from study_ahf_v3_3.model_090B_compact_predictors_v34_v1) as predictor_rows,
    (select count(*) from study_ahf_v3_2.model_090A_modeling_base_v33_v1) as base_rows,
    (select coalesce(sum(ambiguous_episode_match), 0)
       from study_ahf_v3_3.model_090B_lab_episode_match_audit_v34_v1) as ambiguous_episode_match_n;
