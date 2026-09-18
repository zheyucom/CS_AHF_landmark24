-- Second-stage audit: raw MIMIC labevents against exact blood-gas itemids.
-- Requires the local partial index created during the audit:
--   labevents_idx_ahf_bg_item_hadm_time(itemid, hadm_id, charttime)
with base as (
  select b.stay_id,b.subject_id,b.hadm_id,a.admittime,b.intime,
         b.intime + interval '12 hour' t12,
         b.intime + interval '24 hour' t24,
         b.intime + interval '48 hour' t48
  from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
  join mimiciv_hosp.admissions a using(subject_id,hadm_id)
), rows as (
  select b.stay_id,l.charttime,l.itemid,l.valuenum
  from base b join mimiciv_hosp.labevents l
    on l.subject_id=b.subject_id and l.hadm_id=b.hadm_id
   and l.charttime>=b.admittime and l.charttime<b.t48
  where l.itemid in (50802,50813,50820)
), s as (
  select b.stay_id,
    count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t12) raw_0_12,
    count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t24) raw_0_24,
    count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t48) raw_0_48,
    count(r.charttime) filter(where r.charttime>=b.admittime and r.charttime<b.intime) raw_hosp_icu,
    count(r.charttime) filter(where r.charttime>=b.admittime and r.charttime<b.t12) raw_hosp_t12,
    count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t12) lactate_0_12,
    count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t24) lactate_0_24,
    count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t48) lactate_0_48,
    count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.intime) lactate_hosp_icu,
    count(r.charttime) filter(where r.itemid=50813 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.t12) lactate_hosp_t12,
    count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t12) ph_0_12,
    count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t24) ph_0_24,
    count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t48) ph_0_48,
    count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.intime) ph_hosp_icu,
    count(r.charttime) filter(where r.itemid=50820 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.t12) ph_hosp_t12,
    count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t12) be_0_12,
    count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t24) be_0_24,
    count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.intime and r.charttime<b.t48) be_0_48,
    count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.intime) be_hosp_icu,
    count(r.charttime) filter(where r.itemid=50802 and r.valuenum is not null and r.charttime>=b.admittime and r.charttime<b.t12) be_hosp_t12
  from base b left join rows r using(stay_id) group by b.stay_id
), long as (
  select 'icu_0_12' window_name,1 ord,(raw_0_12>0)::int target,(lactate_0_12>0)::int lactate,(ph_0_12>0)::int ph,(be_0_12>0)::int be from s
  union all select 'icu_0_24',2,(raw_0_24>0)::int,(lactate_0_24>0)::int,(ph_0_24>0)::int,(be_0_24>0)::int from s
  union all select 'icu_0_48',3,(raw_0_48>0)::int,(lactate_0_48>0)::int,(ph_0_48>0)::int,(be_0_48>0)::int from s
  union all select 'hospital_to_icu',4,(raw_hosp_icu>0)::int,(lactate_hosp_icu>0)::int,(ph_hosp_icu>0)::int,(be_hosp_icu>0)::int from s
  union all select 'hospital_to_t12',5,(raw_hosp_t12>0)::int,(lactate_hosp_t12>0)::int,(ph_hosp_t12>0)::int,(be_hosp_t12>0)::int from s
)
select window_name,count(*) n_stays,sum(target) raw_target_component,sum(lactate) raw_lactate,
       sum(ph) raw_ph,sum(be) raw_baseexcess,
       round(100.0*sum(lactate)/count(*),2) pct_lactate,
       round(100.0*sum(ph)/count(*),2) pct_ph,
       round(100.0*sum(be)/count(*),2) pct_baseexcess
from long group by window_name,ord order by ord;
