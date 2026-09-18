-- Quantifies source discordance at the primary ICU 0-12 h window.
with base as (
  select b.stay_id,b.subject_id,b.hadm_id,b.intime,b.intime + interval '12 hour' t12
  from study_ahf_v3_2.model_090A_modeling_base_v33_v1 b
), raw as (
  select b.stay_id,
         max((l.itemid=50813)::int) raw_lactate,
         max((l.itemid=50820)::int) raw_ph,
         max((l.itemid=50802)::int) raw_baseexcess
  from base b join mimiciv_hosp.labevents l
    on l.subject_id=b.subject_id and l.hadm_id=b.hadm_id
   and l.charttime>=b.intime and l.charttime<b.t12
  where l.itemid in (50802,50813,50820) and l.valuenum is not null
  group by b.stay_id
), derived as (
  select b.stay_id,
         max(g.lactate) lactate,max(g.ph) ph,max(g.baseexcess) baseexcess
  from base b join mimiciv_derived.bg g
    on g.subject_id=b.subject_id and g.hadm_id=b.hadm_id
   and g.charttime>=b.intime and g.charttime<b.t12
  group by b.stay_id
), flags as (
  select b.stay_id,
    coalesce(r.raw_lactate,0) raw_lactate,
    coalesce(r.raw_ph,0) raw_ph,
    coalesce(r.raw_baseexcess,0) raw_baseexcess,
    (d.lactate is not null)::int derived_lactate,
    (d.ph is not null)::int derived_ph,
    (d.baseexcess is not null)::int derived_baseexcess
  from base b
  left join raw r using(stay_id)
  left join derived d using(stay_id)
)
select
  count(*) n_stays,
  sum(raw_lactate) raw_lactate,
  sum(derived_lactate) derived_lactate,
  sum(case when raw_lactate=1 and derived_lactate=0 then 1 else 0 end) raw_lactate_only,
  sum(case when raw_lactate=0 and derived_lactate=1 then 1 else 0 end) derived_lactate_only,
  sum(raw_ph) raw_ph,
  sum(derived_ph) derived_ph,
  sum(case when raw_ph=1 and derived_ph=0 then 1 else 0 end) raw_ph_only,
  sum(raw_baseexcess) raw_baseexcess,
  sum(derived_baseexcess) derived_baseexcess,
  sum(case when raw_baseexcess=1 and derived_baseexcess=0 then 1 else 0 end) raw_baseexcess_only
from flags;
