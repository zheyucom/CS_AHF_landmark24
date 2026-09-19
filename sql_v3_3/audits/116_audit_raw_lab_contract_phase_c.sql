-- Phase-C fail-closed audit for the raw MIMIC-IV laboratory contract.
-- The output is aggregate-only.  Any failed hard gate raises an exception so
-- the phase runner cannot execute a downstream consumer on an invalid layer.

create schema if not exists study_ahf_v3_3;

drop table if exists study_ahf_v3_3.audit_116_lab_contract_phase_c_v1 cascade;

create table study_ahf_v3_3.audit_116_lab_contract_phase_c_v1 (
    metric_group text not null,
    metric_name text primary key,
    observed_value bigint not null,
    expected_value bigint,
    passed boolean not null,
    hard_gate boolean not null,
    detail text not null
);

with counts as (
    select
        (select count(*) from study_ahf_v3_3.lab_contract_v1) as contract_concept_n,
        (select count(*) from study_ahf_v3_3.lab_quarantine_item_v1) as quarantine_item_n,
        (select count(*) from study_ahf_v3_3.lab_event_classified_v1) as classified_n,
        (select count(*) from study_ahf_v3_3.lab_eligible_v1) as eligible_n,
        (select count(*)
           from study_ahf_v3_3.lab_event_classified_v1
          where quarantine_reason is not null) as quarantined_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1 e
          where exists (
                    select 1
                    from study_ahf_v3_3.lab_quarantine_item_v1 q
                    where q.itemid = e.itemid
                )
             or (e.concept = 'bun' and (e.itemid <> 51006 or e.fluid is distinct from 'Blood'))
        ) as eligible_wrong_fluid_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1
          where storetime < charttime) as eligible_reversed_time_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1
          where specimen_id is null) as eligible_missing_specimen_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1
          where specimen_itemid_count > 1) as eligible_duplicate_specimen_itemid_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1
          where concept <> 'inr'
            and nullif(trim(valueuom), '') is null) as eligible_non_inr_blank_unit_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1
          where concept = 'inr'
            and nullif(trim(valueuom), '') is not null) as eligible_inr_nonblank_unit_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1
          where quarantine_reason is not null) as eligible_quarantine_reason_n,
        (select count(*)
           from (
               select labevent_id
               from study_ahf_v3_3.lab_eligible_v1
               group by labevent_id
               having count(*) > 1
           ) duplicate_labevents) as eligible_duplicate_labevent_id_n,
        (select count(*)
           from study_ahf_v3_3.lab_eligible_v1 e
           left join study_ahf_v3_3.lab_contract_v1 c
             on e.itemid = c.itemid
          where c.itemid is null
             or e.concept is distinct from c.concept
             or e.label is distinct from c.expected_label
             or e.fluid is distinct from c.expected_fluid
             or e.category is distinct from c.expected_category
        ) as eligible_contract_metadata_mismatch_n
), hard_metrics as (
    select 'contract'::text as metric_group, 'contract_concept_n'::text as metric_name,
           contract_concept_n::bigint as observed_value, 14::bigint as expected_value,
           contract_concept_n = 14 as passed, true as hard_gate,
           'The versioned contract must contain exactly 14 allowed blood-laboratory concepts.'::text as detail
    from counts
    union all
    select 'contract', 'quarantine_item_n', quarantine_item_n, 8,
           quarantine_item_n = 8, true,
           'The BUN wrong-fluid quarantine registry must contain exactly 8 itemids.'
    from counts
    union all
    select 'balance', 'classified_row_balance_n',
           abs(classified_n - (eligible_n + quarantined_n)), 0,
           classified_n = eligible_n + quarantined_n, true,
           'Classified rows must equal eligible rows plus quarantined rows.'
    from counts
    union all
    select 'eligibility', 'eligible_wrong_fluid_n', eligible_wrong_fluid_n, 0,
           eligible_wrong_fluid_n = 0, true,
           'No known wrong-fluid item, and no non-51006/non-blood BUN, may enter eligible.'
    from counts
    union all
    select 'eligibility', 'eligible_reversed_time_n', eligible_reversed_time_n, 0,
           eligible_reversed_time_n = 0, true,
           'Eligible rows cannot have storetime before charttime.'
    from counts
    union all
    select 'eligibility', 'eligible_missing_specimen_n', eligible_missing_specimen_n, 0,
           eligible_missing_specimen_n = 0, true,
           'Eligible rows must have specimen_id.'
    from counts
    union all
    select 'eligibility', 'eligible_duplicate_specimen_itemid_n', eligible_duplicate_specimen_itemid_n, 0,
           eligible_duplicate_specimen_itemid_n = 0, true,
           'Eligible rows must be unique at specimen_id x itemid in the source contract slice.'
    from counts
    union all
    select 'unit', 'eligible_non_inr_blank_unit_n', eligible_non_inr_blank_unit_n, 0,
           eligible_non_inr_blank_unit_n = 0, true,
           'Blank units are forbidden for every eligible concept except dimensionless INR.'
    from counts
    union all
    select 'unit', 'eligible_inr_nonblank_unit_n', eligible_inr_nonblank_unit_n, 0,
           eligible_inr_nonblank_unit_n = 0, true,
           'The MIMIC-IV INR contract is dimensionless and permits only null/blank units.'
    from counts
    union all
    select 'eligibility', 'eligible_quarantine_reason_n', eligible_quarantine_reason_n, 0,
           eligible_quarantine_reason_n = 0, true,
           'The eligible table cannot retain a quarantine reason.'
    from counts
    union all
    select 'identity', 'eligible_duplicate_labevent_id_n', eligible_duplicate_labevent_id_n, 0,
           eligible_duplicate_labevent_id_n = 0, true,
           'Each source labevent_id must appear at most once in eligible.'
    from counts
    union all
    select 'metadata', 'eligible_contract_metadata_mismatch_n', eligible_contract_metadata_mismatch_n, 0,
           eligible_contract_metadata_mismatch_n = 0, true,
           'Eligible label, fluid and category must exactly match the versioned contract.'
    from counts
)
insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select * from hard_metrics;

insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select
    'result_class' as metric_group,
    'result_class:' || coalesce(result_class, '<null>') as metric_name,
    count(*) as observed_value,
    null::bigint as expected_value,
    true as passed,
    false as hard_gate,
    'Descriptive distribution in the full classified contract slice.' as detail
from study_ahf_v3_3.lab_event_classified_v1
group by result_class;

insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select
    'censor_type' as metric_group,
    'censor_type:' || coalesce(censor_type, '<none>') as metric_name,
    count(*) as observed_value,
    null::bigint as expected_value,
    true as passed,
    false as hard_gate,
    'Descriptive censoring distribution; censored values are not exact continuous values.' as detail
from study_ahf_v3_3.lab_event_classified_v1
group by censor_type;

insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select
    'quarantine_reason' as metric_group,
    'quarantine_reason:' || coalesce(quarantine_reason, '<eligible>') as metric_name,
    count(*) as observed_value,
    null::bigint as expected_value,
    true as passed,
    false as hard_gate,
    'Descriptive quarantine distribution; <eligible> means no contract violation.' as detail
from study_ahf_v3_3.lab_event_classified_v1
group by quarantine_reason;

insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select
    'analysis_exclusion' as metric_group,
    'analysis_exclusion:' || coalesce(analysis_exclusion_reason, '<included>') as metric_name,
    count(*) as observed_value,
    null::bigint as expected_value,
    true as passed,
    false as hard_gate,
    'Descriptive continuous-analysis disposition; raw values remain retained.' as detail
from study_ahf_v3_3.lab_event_classified_v1
group by analysis_exclusion_reason;

insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select
    'official_range_flag' as metric_group,
    'official_range_flag:' || official_range_outlier_flag::text as metric_name,
    count(*) as observed_value,
    null::bigint as expected_value,
    true as passed,
    false as hard_gate,
    'Descriptive official analysis-range flag; it is not a physical-impossibility label.' as detail
from study_ahf_v3_3.lab_event_classified_v1
group by official_range_outlier_flag;

insert into study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
select
    'eligible_concept' as metric_group,
    'eligible_concept:' || concept as metric_name,
    count(*) as observed_value,
    null::bigint as expected_value,
    true as passed,
    false as hard_gate,
    'Descriptive eligible-row count by contract concept.' as detail
from study_ahf_v3_3.lab_eligible_v1
group by concept;

select *
from study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
order by hard_gate desc, passed, metric_group, metric_name;

do $audit_gate$
declare
    failures text;
begin
    select string_agg(
               metric_name || '=' || observed_value::text ||
               ' expected=' || coalesce(expected_value::text, '<descriptive>'),
               '; ' order by metric_name
           )
      into failures
      from study_ahf_v3_3.audit_116_lab_contract_phase_c_v1
     where hard_gate
       and not passed;

    if failures is not null then
        raise exception 'Phase-C raw laboratory contract hard gate failed: %', failures;
    end if;
end
$audit_gate$;
