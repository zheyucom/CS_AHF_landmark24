-- MIMIC lab coverage audit. Audit only; no model changes.
-- Windows: ICU 0-12/0-24/0-48 h, hospital-to-ICU, hospital-to-T12.
-- Raw component itemids: 50802 Base Excess, 50813 Lactate, 50820 pH.

drop table if exists study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1;

create table study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1 as
with base as (
    select b.stay_id,b.subject_id,b.hadm_id,a.admittime,b.intime,
           b.intime + interval '12 hour' t12,
           b.intime + interval '24 hour' t24,
           b.intime + interval '48 hour' t48,
           b.final_state,b.early_sepsis12_main_flag
    from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
    join mimiciv_hosp.admissions a on a.hadm_id=b.hadm_id and a.subject_id=b.subject_id
),
derived as (
    select b.stay_id,b.intime,b.admittime,b.t12,b.t24,b.t48,
           g.charttime,g.lactate,g.ph,g.baseexcess
    from base b join mimiciv_derived.bg g
      on g.subject_id=b.subject_id and g.hadm_id=b.hadm_id
     and g.charttime>=b.admittime and g.charttime<b.t48
),
raw as (
    select b.stay_id,b.intime,b.admittime,b.t12,b.t24,b.t48,
           l.charttime,l.itemid,l.valuenum
    from base b join mimiciv_hosp.labevents l
      on l.subject_id=b.subject_id and l.hadm_id=b.hadm_id
     and l.charttime>=b.admittime and l.charttime<b.t48
    where l.itemid in (50802,50813,50820)
),
ds as (
    select b.stay_id,
      count(d.charttime) filter(where d.charttime>=b.intime and d.charttime<b.t12) bg_0_12,
      count(d.charttime) filter(where d.charttime>=b.intime and d.charttime<b.t24) bg_0_24,
      count(d.charttime) filter(where d.charttime>=b.intime and d.charttime<b.t48) bg_0_48,
      count(d.charttime) filter(where d.charttime>=b.admittime and d.charttime<b.intime) bg_hosp_icu,
      count(d.charttime) filter(where d.charttime>=b.admittime and d.charttime<b.t12) bg_hosp_t12,
      count(d.lactate) filter(where d.charttime>=b.intime and d.charttime<b.t12) lactate_0_12,
      count(d.lactate) filter(where d.charttime>=b.intime and d.charttime<b.t24) lactate_0_24,
      count(d.lactate) filter(where d.charttime>=b.intime and d.charttime<b.t48) lactate_0_48,
      count(d.lactate) filter(where d.charttime>=b.admittime and d.charttime<b.intime) lactate_hosp_icu,
      count(d.lactate) filter(where d.charttime>=b.admittime and d.charttime<b.t12) lactate_hosp_t12,
      count(d.ph) filter(where d.charttime>=b.intime and d.charttime<b.t12) ph_0_12,
      count(d.ph) filter(where d.charttime>=b.intime and d.charttime<b.t24) ph_0_24,
      count(d.ph) filter(where d.charttime>=b.intime and d.charttime<b.t48) ph_0_48,
      count(d.ph) filter(where d.charttime>=b.admittime and d.charttime<b.intime) ph_hosp_icu,
      count(d.ph) filter(where d.charttime>=b.admittime and d.charttime<b.t12) ph_hosp_t12,
      count(d.baseexcess) filter(where d.charttime>=b.intime and d.charttime<b.t12) be_0_12,
      count(d.baseexcess) filter(where d.charttime>=b.intime and d.charttime<b.t24) be_0_24,
      count(d.baseexcess) filter(where d.charttime>=b.intime and d.charttime<b.t48) be_0_48,
      count(d.baseexcess) filter(where d.charttime>=b.admittime and d.charttime<b.intime) be_hosp_icu,
      count(d.baseexcess) filter(where d.charttime>=b.admittime and d.charttime<b.t12) be_hosp_t12,
      min(d.charttime) filter(where d.lactate is not null) first_derived_lactate,
      min(d.charttime) first_derived_bg
    from base b left join derived d using(stay_id) group by b.stay_id
),
rs as (
    select b.stay_id,
      count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t12) raw_0_12,
      count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t24) raw_0_24,
      count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t48) raw_0_48,
      count(r.charttime) filter(where r.charttime>=b.admittime and r.charttime<b.intime) raw_hosp_icu,
      count(r.charttime) filter(where r.charttime>=b.admittime and r.charttime<b.t12) raw_hosp_t12,
      count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t12) raw_lactate_0_12,
      count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t24) raw_lactate_0_24,
      count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t48) raw_lactate_0_48,
      count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.intime) raw_lactate_hosp_icu,
      count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.t12) raw_lactate_hosp_t12,
      count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t12) raw_ph_0_12,
      count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t24) raw_ph_0_24,
      count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t48) raw_ph_0_48,
      count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.intime) raw_ph_hosp_icu,
      count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.t12) raw_ph_hosp_t12,
      count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t12) raw_be_0_12,
      count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t24) raw_be_0_24,
      count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t48) raw_be_0_48,
      count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.intime) raw_be_hosp_icu,
      count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.t12) raw_be_hosp_t12,
      min(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null) first_raw_lactate,
      min(r.charttime) first_raw_target
    from base b left join raw r using(stay_id) group by b.stay_id
)
select b.*,
       ds.bg_0_12,ds.bg_0_24,ds.bg_0_48,ds.bg_hosp_icu,ds.bg_hosp_t12,
       ds.lactate_0_12,ds.lactate_0_24,ds.lactate_0_48,ds.lactate_hosp_icu,ds.lactate_hosp_t12,
       ds.ph_0_12,ds.ph_0_24,ds.ph_0_48,ds.ph_hosp_icu,ds.ph_hosp_t12,
       ds.be_0_12,ds.be_0_24,ds.be_0_48,ds.be_hosp_icu,ds.be_hosp_t12,
       ds.first_derived_lactate,ds.first_derived_bg,
       rs.raw_0_12,rs.raw_0_24,rs.raw_0_48,rs.raw_hosp_icu,rs.raw_hosp_t12,
       rs.raw_lactate_0_12,rs.raw_lactate_0_24,rs.raw_lactate_0_48,rs.raw_lactate_hosp_icu,rs.raw_lactate_hosp_t12,
       rs.raw_ph_0_12,rs.raw_ph_0_24,rs.raw_ph_0_48,rs.raw_ph_hosp_icu,rs.raw_ph_hosp_t12,
       rs.raw_be_0_12,rs.raw_be_0_24,rs.raw_be_0_48,rs.raw_be_hosp_icu,rs.raw_be_hosp_t12,
       rs.first_raw_lactate,rs.first_raw_target,
       case when rs.raw_0_48>0 and ds.bg_0_48=0 then 1 else 0 end raw_target_no_derived_bg_48h,
       '114_v3' audit_version
from base b join ds using(stay_id) join rs using(stay_id);

create unique index idx_114_lab_time_window_stay
  on study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1(stay_id);
analyze study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1;

-- One-row-per-window summary.
select 'icu_0_12' window_name,count(*) n_stays,
 sum((bg_0_12>0)::int) derived_bg, sum((lactate_0_12>0)::int) derived_lactate,
 sum((ph_0_12>0)::int) derived_ph, sum((be_0_12>0)::int) derived_baseexcess,
 sum((raw_0_12>0)::int) raw_target, sum((raw_0_12>0 and bg_0_12=0)::int) raw_without_derived
 from study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1
union all select 'icu_0_24',count(*),sum((bg_0_24>0)::int),sum((lactate_0_24>0)::int),sum((ph_0_24>0)::int),sum((be_0_24>0)::int),sum((raw_0_24>0)::int),sum((raw_0_24>0 and bg_0_24=0)::int) from study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1
union all select 'icu_0_48',count(*),sum((bg_0_48>0)::int),sum((lactate_0_48>0)::int),sum((ph_0_48>0)::int),sum((be_0_48>0)::int),sum((raw_0_48>0)::int),sum((raw_0_48>0 and bg_0_48=0)::int) from study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1
union all select 'hospital_to_icu',count(*),sum((bg_hosp_icu>0)::int),sum((lactate_hosp_icu>0)::int),sum((ph_hosp_icu>0)::int),sum((be_hosp_icu>0)::int),sum((raw_hosp_icu>0)::int),sum((raw_hosp_icu>0 and bg_hosp_icu=0)::int) from study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1
union all select 'hospital_to_t12',count(*),sum((bg_hosp_t12>0)::int),sum((lactate_hosp_t12>0)::int),sum((ph_hosp_t12>0)::int),sum((be_hosp_t12>0)::int),sum((raw_hosp_t12>0)::int),sum((raw_hosp_t12>0 and bg_hosp_t12=0)::int) from study_ahf_v3_2.audit_114_lab_time_window_feasibility_v1;
