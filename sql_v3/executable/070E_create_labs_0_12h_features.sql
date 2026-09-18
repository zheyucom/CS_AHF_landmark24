-- ============================================================
-- Project: CS_AHF_earlysepsis12
-- File: sql/03_features/070E_create_labs_0_12h_features.sql
-- Purpose:
--   Create 0-12h laboratory and blood gas features using
--   official mimiciv_derived tables.
--
-- Source tables:
--   mimiciv_derived.bg
--   mimiciv_derived.chemistry
--   mimiciv_derived.complete_blood_count
--   mimiciv_derived.coagulation
--
-- Predictor window:
--   ICU intime <= charttime < ICU intime + 12h.
--
-- Leakage control:
--   No lab after the 12h landmark is used.
-- ============================================================

drop table if exists study_ahf_v3.model_070E_labs_0_12h_v1 cascade;

create table study_ahf_v3.model_070E_labs_0_12h_v1 as
with base as (
    select *
    from study_ahf_v3.model_070A_base_index_v1
),

-- ------------------------------------------------------------
-- Blood gas features
-- ------------------------------------------------------------
bg_raw as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        bg.charttime,

        case when bg.lactate     between 0 and 30 then bg.lactate     else null end as lactate,
        case when bg.ph          between 6.8 and 7.8 then bg.ph       else null end as ph,
        case when bg.baseexcess  between -50 and 50 then bg.baseexcess else null end as baseexcess,
        case when bg.bicarbonate between 0 and 60 then bg.bicarbonate else null end as bg_bicarbonate,
        case when bg.po2         between 10 and 600 then bg.po2       else null end as po2,
        case when bg.pco2        between 10 and 150 then bg.pco2      else null end as pco2,
        case when bg.pao2fio2ratio between 20 and 800 then bg.pao2fio2ratio else null end as pao2fio2ratio,
        case when bg.so2         between 0 and 100 then bg.so2        else null end as bg_so2,
        case when bg.glucose     between 20 and 1000 then bg.glucose  else null end as bg_glucose

    from base b
    left join mimiciv_derived.bg bg
        on b.subject_id = bg.subject_id
       and b.hadm_id = bg.hadm_id
       and bg.charttime >= b.intime
       and bg.charttime <  b.landmark12_time
),

bg_summary as (
    select
        stay_id,

        count(lactate) as lactate_n,
        min(lactate) as lactate_min,
        max(lactate) as lactate_max,
        avg(lactate) as lactate_mean,

        count(ph) as ph_n,
        min(ph) as ph_min,
        max(ph) as ph_max,
        avg(ph) as ph_mean,

        count(baseexcess) as baseexcess_n,
        min(baseexcess) as baseexcess_min,
        max(baseexcess) as baseexcess_max,
        avg(baseexcess) as baseexcess_mean,

        count(bg_bicarbonate) as bg_bicarbonate_n,
        min(bg_bicarbonate) as bg_bicarbonate_min,
        max(bg_bicarbonate) as bg_bicarbonate_max,
        avg(bg_bicarbonate) as bg_bicarbonate_mean,

        count(po2) as po2_n,
        min(po2) as po2_min,
        max(po2) as po2_max,
        avg(po2) as po2_mean,

        count(pco2) as pco2_n,
        min(pco2) as pco2_min,
        max(pco2) as pco2_max,
        avg(pco2) as pco2_mean,

        count(pao2fio2ratio) as pf_ratio_n,
        min(pao2fio2ratio) as pf_ratio_min,
        max(pao2fio2ratio) as pf_ratio_max,
        avg(pao2fio2ratio) as pf_ratio_mean,

        count(bg_so2) as bg_so2_n,
        min(bg_so2) as bg_so2_min,
        max(bg_so2) as bg_so2_max,
        avg(bg_so2) as bg_so2_mean,

        count(bg_glucose) as bg_glucose_n,
        min(bg_glucose) as bg_glucose_min,
        max(bg_glucose) as bg_glucose_max,
        avg(bg_glucose) as bg_glucose_mean

    from bg_raw
    group by stay_id
),

lactate_first as (
    select distinct on (stay_id)
        stay_id,
        charttime as lactate_first_time,
        lactate as lactate_first
    from bg_raw
    where lactate is not null
    order by stay_id, charttime
),

lactate_last as (
    select distinct on (stay_id)
        stay_id,
        charttime as lactate_last_time,
        lactate as lactate_last
    from bg_raw
    where lactate is not null
    order by stay_id, charttime desc
),

ph_first as (
    select distinct on (stay_id)
        stay_id,
        ph as ph_first
    from bg_raw
    where ph is not null
    order by stay_id, charttime
),

ph_last as (
    select distinct on (stay_id)
        stay_id,
        ph as ph_last
    from bg_raw
    where ph is not null
    order by stay_id, charttime desc
),

-- ------------------------------------------------------------
-- Chemistry features
-- ------------------------------------------------------------
chem_raw as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        ch.charttime,

        case when ch.creatinine between 0.1 and 20 then ch.creatinine else null end as creatinine,
        case when ch.bun        between 1 and 200 then ch.bun        else null end as bun,
        case when ch.sodium     between 100 and 180 then ch.sodium   else null end as sodium,
        case when ch.potassium  between 1.5 and 8 then ch.potassium  else null end as potassium,
        case when ch.chloride   between 70 and 140 then ch.chloride  else null end as chloride,
        case when ch.bicarbonate between 5 and 60 then ch.bicarbonate else null end as chem_bicarbonate,
        case when ch.aniongap   between 0 and 60 then ch.aniongap    else null end as aniongap,
        case when ch.glucose    between 20 and 1000 then ch.glucose  else null end as chem_glucose,
        case when ch.albumin    between 0.5 and 8 then ch.albumin    else null end as albumin,
        case when ch.calcium    between 4 and 20 then ch.calcium     else null end as calcium

    from base b
    left join mimiciv_derived.chemistry ch
        on b.subject_id = ch.subject_id
       and b.hadm_id = ch.hadm_id
       and ch.charttime >= b.intime
       and ch.charttime <  b.landmark12_time
),

chem_summary as (
    select
        stay_id,

        count(creatinine) as creatinine_n,
        min(creatinine) as creatinine_min,
        max(creatinine) as creatinine_max,
        avg(creatinine) as creatinine_mean,

        count(bun) as bun_n,
        min(bun) as bun_min,
        max(bun) as bun_max,
        avg(bun) as bun_mean,

        count(sodium) as sodium_n,
        min(sodium) as sodium_min,
        max(sodium) as sodium_max,
        avg(sodium) as sodium_mean,

        count(potassium) as potassium_n,
        min(potassium) as potassium_min,
        max(potassium) as potassium_max,
        avg(potassium) as potassium_mean,

        count(chloride) as chloride_n,
        min(chloride) as chloride_min,
        max(chloride) as chloride_max,
        avg(chloride) as chloride_mean,

        count(chem_bicarbonate) as chem_bicarbonate_n,
        min(chem_bicarbonate) as chem_bicarbonate_min,
        max(chem_bicarbonate) as chem_bicarbonate_max,
        avg(chem_bicarbonate) as chem_bicarbonate_mean,

        count(aniongap) as aniongap_n,
        min(aniongap) as aniongap_min,
        max(aniongap) as aniongap_max,
        avg(aniongap) as aniongap_mean,

        count(chem_glucose) as chem_glucose_n,
        min(chem_glucose) as chem_glucose_min,
        max(chem_glucose) as chem_glucose_max,
        avg(chem_glucose) as chem_glucose_mean,

        count(albumin) as albumin_n,
        min(albumin) as albumin_min,
        max(albumin) as albumin_max,
        avg(albumin) as albumin_mean,

        count(calcium) as calcium_n,
        min(calcium) as calcium_min,
        max(calcium) as calcium_max,
        avg(calcium) as calcium_mean

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

-- ------------------------------------------------------------
-- Complete blood count features
-- ------------------------------------------------------------
cbc_raw as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        cbc.charttime,

        case when cbc.wbc        between 0.1 and 200 then cbc.wbc        else null end as wbc,
        case when cbc.hemoglobin between 3 and 25 then cbc.hemoglobin    else null end as hemoglobin,
        case when cbc.hematocrit between 5 and 75 then cbc.hematocrit    else null end as hematocrit,
        case when cbc.platelet   between 1 and 2000 then cbc.platelet    else null end as platelet,
        case when cbc.rbc        between 0.5 and 10 then cbc.rbc         else null end as rbc,
        case when cbc.rdw        between 5 and 40 then cbc.rdw           else null end as rdw

    from base b
    left join mimiciv_derived.complete_blood_count cbc
        on b.subject_id = cbc.subject_id
       and b.hadm_id = cbc.hadm_id
       and cbc.charttime >= b.intime
       and cbc.charttime <  b.landmark12_time
),

cbc_summary as (
    select
        stay_id,

        count(wbc) as wbc_n,
        min(wbc) as wbc_min,
        max(wbc) as wbc_max,
        avg(wbc) as wbc_mean,

        count(hemoglobin) as hemoglobin_n,
        min(hemoglobin) as hemoglobin_min,
        max(hemoglobin) as hemoglobin_max,
        avg(hemoglobin) as hemoglobin_mean,

        count(hematocrit) as hematocrit_n,
        min(hematocrit) as hematocrit_min,
        max(hematocrit) as hematocrit_max,
        avg(hematocrit) as hematocrit_mean,

        count(platelet) as platelet_n,
        min(platelet) as platelet_min,
        max(platelet) as platelet_max,
        avg(platelet) as platelet_mean,

        count(rdw) as rdw_n,
        min(rdw) as rdw_min,
        max(rdw) as rdw_max,
        avg(rdw) as rdw_mean

    from cbc_raw
    group by stay_id
),

-- ------------------------------------------------------------
-- Coagulation features
-- ------------------------------------------------------------
coag_raw as (
    select
        b.subject_id,
        b.hadm_id,
        b.stay_id,
        co.charttime,

        case when co.inr        between 0.5 and 20 then co.inr        else null end as inr,
        case when co.pt         between 5 and 200 then co.pt          else null end as pt,
        case when co.ptt        between 10 and 300 then co.ptt        else null end as ptt,
        case when co.fibrinogen between 10 and 1000 then co.fibrinogen else null end as fibrinogen,
        case when co.d_dimer    between 0 and 100000 then co.d_dimer  else null end as d_dimer

    from base b
    left join mimiciv_derived.coagulation co
        on b.subject_id = co.subject_id
       and b.hadm_id = co.hadm_id
       and co.charttime >= b.intime
       and co.charttime <  b.landmark12_time
),

coag_summary as (
    select
        stay_id,

        count(inr) as inr_n,
        min(inr) as inr_min,
        max(inr) as inr_max,
        avg(inr) as inr_mean,

        count(pt) as pt_n,
        min(pt) as pt_min,
        max(pt) as pt_max,
        avg(pt) as pt_mean,

        count(ptt) as ptt_n,
        min(ptt) as ptt_min,
        max(ptt) as ptt_max,
        avg(ptt) as ptt_mean,

        count(fibrinogen) as fibrinogen_n,
        min(fibrinogen) as fibrinogen_min,
        max(fibrinogen) as fibrinogen_max,
        avg(fibrinogen) as fibrinogen_mean,

        count(d_dimer) as d_dimer_n,
        min(d_dimer) as d_dimer_min,
        max(d_dimer) as d_dimer_max,
        avg(d_dimer) as d_dimer_mean

    from coag_raw
    group by stay_id
)

select
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    b.primary_outcome_flag,

    -- blood gas / perfusion
    bg.lactate_n,
    lf.lactate_first,
    ll.lactate_last,
    bg.lactate_min,
    bg.lactate_max,
    bg.lactate_mean,
    ll.lactate_last - lf.lactate_first as lactate_delta,

    bg.ph_n,
    pf.ph_first,
    pl.ph_last,
    bg.ph_min,
    bg.ph_max,
    bg.ph_mean,
    pl.ph_last - pf.ph_first as ph_delta,

    bg.baseexcess_n,
    bg.baseexcess_min,
    bg.baseexcess_max,
    bg.baseexcess_mean,

    bg.bg_bicarbonate_n,
    bg.bg_bicarbonate_min,
    bg.bg_bicarbonate_max,
    bg.bg_bicarbonate_mean,

    bg.po2_n,
    bg.po2_min,
    bg.po2_max,
    bg.po2_mean,

    bg.pco2_n,
    bg.pco2_min,
    bg.pco2_max,
    bg.pco2_mean,

    bg.pf_ratio_n,
    bg.pf_ratio_min,
    bg.pf_ratio_max,
    bg.pf_ratio_mean,

    -- chemistry
    ch.creatinine_n,
    cf.creatinine_first,
    cl.creatinine_last,
    ch.creatinine_min,
    ch.creatinine_max,
    ch.creatinine_mean,
    cl.creatinine_last - cf.creatinine_first as creatinine_delta,

    ch.bun_n,
    ch.bun_min,
    ch.bun_max,
    ch.bun_mean,

    ch.sodium_n,
    ch.sodium_min,
    ch.sodium_max,
    ch.sodium_mean,

    ch.potassium_n,
    ch.potassium_min,
    ch.potassium_max,
    ch.potassium_mean,

    ch.chloride_n,
    ch.chloride_min,
    ch.chloride_max,
    ch.chloride_mean,

    ch.chem_bicarbonate_n,
    ch.chem_bicarbonate_min,
    ch.chem_bicarbonate_max,
    ch.chem_bicarbonate_mean,

    ch.aniongap_n,
    ch.aniongap_min,
    ch.aniongap_max,
    ch.aniongap_mean,

    ch.chem_glucose_n,
    ch.chem_glucose_min,
    ch.chem_glucose_max,
    ch.chem_glucose_mean,

    ch.albumin_n,
    ch.albumin_min,
    ch.albumin_max,
    ch.albumin_mean,

    -- CBC
    cbc.wbc_n,
    cbc.wbc_min,
    cbc.wbc_max,
    cbc.wbc_mean,

    cbc.hemoglobin_n,
    cbc.hemoglobin_min,
    cbc.hemoglobin_max,
    cbc.hemoglobin_mean,

    cbc.platelet_n,
    cbc.platelet_min,
    cbc.platelet_max,
    cbc.platelet_mean,

    cbc.rdw_n,
    cbc.rdw_min,
    cbc.rdw_max,
    cbc.rdw_mean,

    -- coagulation
    co.inr_n,
    co.inr_min,
    co.inr_max,
    co.inr_mean,

    co.pt_n,
    co.pt_min,
    co.pt_max,
    co.pt_mean,

    co.ptt_n,
    co.ptt_min,
    co.ptt_max,
    co.ptt_mean,

    co.fibrinogen_n,
    co.fibrinogen_min,
    co.fibrinogen_max,
    co.fibrinogen_mean,

    co.d_dimer_n,
    co.d_dimer_min,
    co.d_dimer_max,
    co.d_dimer_mean,

    -- availability flags
    case when bg.lactate_n > 0 then 1 else 0 end as lactate_available_flag,
    case when bg.ph_n > 0 then 1 else 0 end as ph_available_flag,
    case when ch.creatinine_n > 0 then 1 else 0 end as creatinine_available_flag,
    case when ch.bun_n > 0 then 1 else 0 end as bun_available_flag,
    case when cbc.wbc_n > 0 then 1 else 0 end as wbc_available_flag,
    case when cbc.platelet_n > 0 then 1 else 0 end as platelet_available_flag,
    case when co.inr_n > 0 then 1 else 0 end as inr_available_flag

from base b
left join bg_summary bg
    on b.stay_id = bg.stay_id
left join lactate_first lf
    on b.stay_id = lf.stay_id
left join lactate_last ll
    on b.stay_id = ll.stay_id
left join ph_first pf
    on b.stay_id = pf.stay_id
left join ph_last pl
    on b.stay_id = pl.stay_id
left join chem_summary ch
    on b.stay_id = ch.stay_id
left join creatinine_first cf
    on b.stay_id = cf.stay_id
left join creatinine_last cl
    on b.stay_id = cl.stay_id
left join cbc_summary cbc
    on b.stay_id = cbc.stay_id
left join coag_summary co
    on b.stay_id = co.stay_id;
		
		
		
		
		
-- 		070E QC1：总体人数
select
    count(*) as n_total,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate
from study_ahf_v3.model_070E_labs_0_12h_v1;



-- 070E QC2：主要实验室指标可用率
select
    count(*) as n_total,

    sum(lactate_available_flag) as n_lactate_available,
    round(sum(lactate_available_flag) * 100.0 / count(*), 2) as pct_lactate_available,

    sum(ph_available_flag) as n_ph_available,
    round(sum(ph_available_flag) * 100.0 / count(*), 2) as pct_ph_available,

    sum(creatinine_available_flag) as n_creatinine_available,
    round(sum(creatinine_available_flag) * 100.0 / count(*), 2) as pct_creatinine_available,

    sum(bun_available_flag) as n_bun_available,
    round(sum(bun_available_flag) * 100.0 / count(*), 2) as pct_bun_available,

    sum(wbc_available_flag) as n_wbc_available,
    round(sum(wbc_available_flag) * 100.0 / count(*), 2) as pct_wbc_available,

    sum(platelet_available_flag) as n_platelet_available,
    round(sum(platelet_available_flag) * 100.0 / count(*), 2) as pct_platelet_available,

    sum(inr_available_flag) as n_inr_available,
    round(sum(inr_available_flag) * 100.0 / count(*), 2) as pct_inr_available

from study_ahf_v3.model_070E_labs_0_12h_v1;




-- 070E QC3：主要实验室指标范围检查
select
    count(*) as n_total,

    min(lactate_min) as lactate_min_min,
    percentile_cont(0.5) within group (order by lactate_max) as lactate_max_median,
    max(lactate_max) as lactate_max_max,

    min(ph_min) as ph_min_min,
    percentile_cont(0.5) within group (order by ph_mean) as ph_mean_median,
    max(ph_max) as ph_max_max,

    min(creatinine_min) as creatinine_min_min,
    percentile_cont(0.5) within group (order by creatinine_max) as creatinine_max_median,
    max(creatinine_max) as creatinine_max_max,

    min(bun_min) as bun_min_min,
    percentile_cont(0.5) within group (order by bun_max) as bun_max_median,
    max(bun_max) as bun_max_max,

    min(wbc_min) as wbc_min_min,
    percentile_cont(0.5) within group (order by wbc_max) as wbc_max_median,
    max(wbc_max) as wbc_max_max,

    min(platelet_min) as platelet_min_min,
    percentile_cont(0.5) within group (order by platelet_min) as platelet_min_median,
    max(platelet_max) as platelet_max_max,

    min(inr_min) as inr_min_min,
    percentile_cont(0.5) within group (order by inr_max) as inr_max_median,
    max(inr_max) as inr_max_max

from study_ahf_v3.model_070E_labs_0_12h_v1;





-- 070E QC4：事件率按 0–12 h 最高乳酸分层
select
    case
        when lactate_max is null then '00_missing'
        when lactate_max < 2 then '01_lactate_lt2'
        when lactate_max >= 2 and lactate_max < 4 then '02_lactate_2_4'
        when lactate_max >= 4 then '03_lactate_ge4'
        else '99_other'
    end as lactate_max_group,

    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate

from study_ahf_v3.model_070E_labs_0_12h_v1
group by
    case
        when lactate_max is null then '00_missing'
        when lactate_max < 2 then '01_lactate_lt2'
        when lactate_max >= 2 and lactate_max < 4 then '02_lactate_2_4'
        when lactate_max >= 4 then '03_lactate_ge4'
        else '99_other'
    end
order by lactate_max_group;




-- 070E QC5：事件率按 0–12 h 最高肌酐分层
select
    case
        when creatinine_max is null then '00_missing'
        when creatinine_max < 1.2 then '01_creatinine_lt1_2'
        when creatinine_max >= 1.2 and creatinine_max < 2.0 then '02_creatinine_1_2_2_0'
        when creatinine_max >= 2.0 then '03_creatinine_ge2_0'
        else '99_other'
    end as creatinine_max_group,

    count(*) as n,
    sum(primary_outcome_flag) as n_events,
    round(sum(primary_outcome_flag) * 100.0 / count(*), 2) as event_rate

from study_ahf_v3.model_070E_labs_0_12h_v1
group by
    case
        when creatinine_max is null then '00_missing'
        when creatinine_max < 1.2 then '01_creatinine_lt1_2'
        when creatinine_max >= 1.2 and creatinine_max < 2.0 then '02_creatinine_1_2_2_0'
        when creatinine_max >= 2.0 then '03_creatinine_ge2_0'
        else '99_other'
    end
order by creatinine_max_group;



