-- Fast first-stage audit using the 697k-row derived blood-gas table.
-- Compares ICU 0-12/0-24/0-48 h and hospital-to-ICU/T12 coverage.
with base as (
  select b.stay_id,b.subject_id,b.hadm_id,a.admittime,b.intime,
         b.intime + interval '12 hour' t12,
         b.intime + interval '24 hour' t24,
         b.intime + interval '48 hour' t48
  from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
  join mimiciv_hosp.admissions a using(subject_id,hadm_id)
), rows as (
  select b.stay_id,g.charttime,g.lactate,g.ph,g.baseexcess
  from base b join mimiciv_derived.bg g using(subject_id,hadm_id)
  where g.charttime >= b.admittime and g.charttime < b.t48
), s as (
  select b.stay_id,
    count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t12) bg_0_12,
    count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t24) bg_0_24,
    count(r.charttime) filter(where r.charttime>=b.intime and r.charttime<b.t48) bg_0_48,
    count(r.charttime) filter(where r.charttime>=b.admittime and r.charttime<b.intime) bg_hosp_icu,
    count(r.charttime) filter(where r.charttime>=b.admittime and r.charttime<b.t12) bg_hosp_t12,
    count(r.lactate) filter(where r.charttime>=b.intime and r.charttime<b.t12) lactate_0_12,
    count(r.lactate) filter(where r.charttime>=b.intime and r.charttime<b.t24) lactate_0_24,
    count(r.lactate) filter(where r.charttime>=b.intime and r.charttime<b.t48) lactate_0_48,
    count(r.lactate) filter(where r.charttime>=b.admittime and r.charttime<b.intime) lactate_hosp_icu,
    count(r.lactate) filter(where r.charttime>=b.admittime and r.charttime<b.t12) lactate_hosp_t12,
    count(r.ph) filter(where r.charttime>=b.intime and r.charttime<b.t12) ph_0_12,
    count(r.ph) filter(where r.charttime>=b.intime and r.charttime<b.t24) ph_0_24,
    count(r.ph) filter(where r.charttime>=b.intime and r.charttime<b.t48) ph_0_48,
    count(r.ph) filter(where r.charttime>=b.admittime and r.charttime<b.intime) ph_hosp_icu,
    count(r.ph) filter(where r.charttime>=b.admittime and r.charttime<b.t12) ph_hosp_t12,
    count(r.baseexcess) filter(where r.charttime>=b.intime and r.charttime<b.t12) be_0_12,
    count(r.baseexcess) filter(where r.charttime>=b.intime and r.charttime<b.t24) be_0_24,
    count(r.baseexcess) filter(where r.charttime>=b.intime and r.charttime<b.t48) be_0_48,
    count(r.baseexcess) filter(where r.charttime>=b.admittime and r.charttime<b.intime) be_hosp_icu,
    count(r.baseexcess) filter(where r.charttime>=b.admittime and r.charttime<b.t12) be_hosp_t12
  from base b left join rows r using(stay_id) group by b.stay_id
), long as (
  select 'icu_0_12' window_name,1 ord, (bg_0_12>0)::int bg,(lactate_0_12>0)::int lactate,(ph_0_12>0)::int ph,(be_0_12>0)::int be from s
  union all select 'icu_0_24',2,(bg_0_24>0)::int,(lactate_0_24>0)::int,(ph_0_24>0)::int,(be_0_24>0)::int from s
  union all select 'icu_0_48',3,(bg_0_48>0)::int,(lactate_0_48>0)::int,(ph_0_48>0)::int,(be_0_48>0)::int from s
  union all select 'hospital_to_icu',4,(bg_hosp_icu>0)::int,(lactate_hosp_icu>0)::int,(ph_hosp_icu>0)::int,(be_hosp_icu>0)::int from s
  union all select 'hospital_to_t12',5,(bg_hosp_t12>0)::int,(lactate_hosp_t12>0)::int,(ph_hosp_t12>0)::int,(be_hosp_t12>0)::int from s
)
select window_name,count(*) n_stays,sum(bg) derived_bg,sum(lactate) derived_lactate,
       sum(ph) derived_ph,sum(be) derived_baseexcess,
       round(100.0*sum(lactate)/count(*),2) pct_lactate,
       round(100.0*sum(ph)/count(*),2) pct_ph,
       round(100.0*sum(be)/count(*),2) pct_baseexcess
from long group by window_name,ord order by ord;
