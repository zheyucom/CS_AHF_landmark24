-- Phase-C aggregate-only comparison of the raw laboratory contract against the
-- historical v3.2 derived-table predictors on the identical modeling base.
-- Differences are descriptive evidence, not a rule-tuning target.

create schema if not exists study_ahf_v3_3;

drop table if exists study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1 cascade;

create table study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1 (
    audit_domain text not null,
    concept text not null,
    metric text not null,
    denominator_n bigint,
    raw_n bigint,
    derived_n bigint,
    raw_only_n bigint,
    derived_only_n bigint,
    both_n bigint,
    unequal_n bigint,
    mean_abs_diff double precision,
    max_abs_diff double precision,
    detail text not null,
    primary key (audit_domain, concept, metric)
);

insert into study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1
with feature_pairs as (
    select
        f.concept,
        f.metric,
        f.raw_value,
        f.derived_value
    from study_ahf_v3_3.model_090B_compact_predictors_v34_v1 r
    full join study_ahf_v3_2.model_090B_compact_predictors_v33_v1 d
      on r.stay_id = d.stay_id
    cross join lateral (
        values
            ('lactate', 'lactate_max', r.lactate_max::double precision, d.lactate_max::double precision),
            ('lactate', 'lactate_delta', r.lactate_delta::double precision, d.lactate_delta::double precision),
            ('ph', 'ph_min', r.ph_min::double precision, d.ph_min::double precision),
            ('base_excess', 'baseexcess_min', r.baseexcess_min::double precision, d.baseexcess_min::double precision),
            ('creatinine', 'creatinine_max', r.creatinine_max::double precision, d.creatinine_max::double precision),
            ('creatinine', 'creatinine_delta', r.creatinine_delta::double precision, d.creatinine_delta::double precision),
            ('bun', 'bun_max', r.bun_max::double precision, d.bun_max::double precision),
            ('sodium', 'sodium_min', r.sodium_min::double precision, d.sodium_min::double precision),
            ('sodium', 'sodium_max', r.sodium_max::double precision, d.sodium_max::double precision),
            ('potassium', 'potassium_min', r.potassium_min::double precision, d.potassium_min::double precision),
            ('potassium', 'potassium_max', r.potassium_max::double precision, d.potassium_max::double precision),
            ('bicarbonate', 'chem_bicarbonate_min', r.chem_bicarbonate_min::double precision, d.chem_bicarbonate_min::double precision),
            ('wbc', 'wbc_max', r.wbc_max::double precision, d.wbc_max::double precision),
            ('hemoglobin', 'hemoglobin_min', r.hemoglobin_min::double precision, d.hemoglobin_min::double precision),
            ('platelet', 'platelet_min', r.platelet_min::double precision, d.platelet_min::double precision),
            ('inr', 'inr_max', r.inr_max::double precision, d.inr_max::double precision)
    ) as f(concept, metric, raw_value, derived_value)
)
select
    'feature_comparison'::text as audit_domain,
    concept,
    metric,
    count(*)::bigint as denominator_n,
    count(raw_value)::bigint as raw_n,
    count(derived_value)::bigint as derived_n,
    count(*) filter (where raw_value is not null and derived_value is null)::bigint as raw_only_n,
    count(*) filter (where raw_value is null and derived_value is not null)::bigint as derived_only_n,
    count(*) filter (where raw_value is not null and derived_value is not null)::bigint as both_n,
    count(*) filter (
        where raw_value is not null
          and derived_value is not null
          and abs(raw_value - derived_value) > 1e-9
    )::bigint as unequal_n,
    avg(abs(raw_value - derived_value)) filter (
        where raw_value is not null and derived_value is not null
    )::double precision as mean_abs_diff,
    max(abs(raw_value - derived_value)) filter (
        where raw_value is not null and derived_value is not null
    )::double precision as max_abs_diff,
    'Same v3.2 modeling base and [T0,T12); raw additionally requires availability_time inside the window.'::text as detail
from feature_pairs
group by concept, metric;

insert into study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1
with base as (
    select subject_id, hadm_id, stay_id, intime, landmark12_time
    from study_ahf_v3_2.model_090A_modeling_base_v33_v1
), sampled_candidates as (
    select
        b.stay_id,
        le.labevent_id,
        le.concept,
        le.availability_time,
        b.landmark12_time,
        count(*) over (partition by le.labevent_id) as episode_match_count
    from base b
    join study_ahf_v3_3.lab_event_classified_v1 le
      on le.subject_id = b.subject_id
     and le.hadm_id = b.hadm_id
     and le.charttime >= b.intime
     and le.charttime < b.landmark12_time
     and le.concept is not null
     and le.quarantine_reason is null
), by_concept as (
    select
        concept,
        count(*) filter (where episode_match_count = 1)::bigint as sampled_unique_episode_n,
        count(*) filter (
            where episode_match_count = 1
              and availability_time >= landmark12_time
        )::bigint as late_result_n,
        count(*) filter (where episode_match_count > 1)::bigint as ambiguous_episode_match_n
    from sampled_candidates
    group by concept
)
select
    'availability_timing'::text as audit_domain,
    concept,
    'late_result_events'::text as metric,
    sampled_unique_episode_n as denominator_n,
    late_result_n as raw_n,
    null::bigint as derived_n,
    null::bigint as raw_only_n,
    null::bigint as derived_only_n,
    null::bigint as both_n,
    ambiguous_episode_match_n as unequal_n,
    null::double precision as mean_abs_diff,
    null::double precision as max_abs_diff,
    'Raw events sampled in [T0,T12) but availability_time at/after T12; unequal_n records ambiguous episode matches.'::text as detail
from by_concept;

insert into study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1
with counts as (
    select
        (select count(*) from study_ahf_v3_2.model_090A_modeling_base_v33_v1)::bigint as base_n,
        (select count(*) from study_ahf_v3_3.model_090B_compact_predictors_v34_v1)::bigint as raw_model_n,
        (select count(*) from study_ahf_v3_2.model_090B_compact_predictors_v33_v1)::bigint as derived_model_n,
        (select coalesce(sum(ambiguous_episode_match), 0)
           from study_ahf_v3_3.model_090B_lab_episode_match_audit_v34_v1)::bigint as ambiguous_n
)
select
    'structural_qc'::text as audit_domain,
    'all'::text as concept,
    'model_row_count'::text as metric,
    base_n as denominator_n,
    raw_model_n as raw_n,
    derived_model_n as derived_n,
    null::bigint as raw_only_n,
    null::bigint as derived_only_n,
    null::bigint as both_n,
    ambiguous_n as unequal_n,
    null::double precision as mean_abs_diff,
    null::double precision as max_abs_diff,
    'raw_n and derived_n must equal the shared base; unequal_n is the raw lab ambiguous-episode count.'::text as detail
from counts;

select *
from study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1
order by audit_domain, concept, metric;

do $structural_gate$
declare
    structural_failure record;
begin
    select *
      into structural_failure
      from study_ahf_v3_3.audit_117_raw_vs_derived_phase_c_v1
     where audit_domain = 'structural_qc'
       and metric = 'model_row_count';

    if structural_failure.raw_n is distinct from structural_failure.denominator_n
       or structural_failure.derived_n is distinct from structural_failure.denominator_n
       or coalesce(structural_failure.unequal_n, 0) <> 0 then
        raise exception
            'Phase-C raw-vs-derived structural gate failed: base=%, raw=%, derived=%, ambiguous=%',
            structural_failure.denominator_n,
            structural_failure.raw_n,
            structural_failure.derived_n,
            structural_failure.unequal_n;
    end if;
end
$structural_gate$;
