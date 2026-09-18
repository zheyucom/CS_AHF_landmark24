-- ============================================================
-- Project: CS_AHF_landmark12 v3.3
-- Purpose: Describe primary-window measurement availability by the
--          prespecified three-state follow-up outcome. This is a
--          missingness-mechanism audit, not predictor selection.
-- Input:   model_090C_finegray_input_v33_v1 after the 2026-09-04
--          raw-lactate source correction.
-- ============================================================

\pset format csv
\o project_control/runs/20260904_lab_measurement_outcome_audit/reports/115_measurement_availability_by_final_state.csv

with source as (
    select
        final_state,
        event_type,
        lactate_max,
        lactate_delta,
        ph_min,
        baseexcess_min,
        inr_max
    from study_ahf_v3_2.model_090C_finegray_input_v33_v1
), long as (
    select final_state, event_type, 'lactate_max'::text as variable_name,
           (lactate_max is not null)::integer as measured
    from source
    union all
    select final_state, event_type, 'lactate_delta',
           (lactate_delta is not null)::integer
    from source
    union all
    select final_state, event_type, 'ph_min',
           (ph_min is not null)::integer
    from source
    union all
    select final_state, event_type, 'baseexcess_min',
           (baseexcess_min is not null)::integer
    from source
    union all
    select final_state, event_type, 'inr_max',
           (inr_max is not null)::integer
    from source
), grouped as (
    select
        final_state as outcome_group,
        variable_name,
        count(*) as n_stays,
        sum(measured) as n_measured,
        round(100.0 * sum(measured) / nullif(count(*), 0), 2) as pct_measured
    from long
    group by final_state, variable_name

    union all

    select
        'event:' || event_type as outcome_group,
        variable_name,
        count(*) as n_stays,
        sum(measured) as n_measured,
        round(100.0 * sum(measured) / nullif(count(*), 0), 2) as pct_measured
    from long
    where final_state = 'event'
    group by event_type, variable_name
)
select outcome_group, variable_name, n_stays, n_measured, pct_measured
from grouped
order by
    case outcome_group
        when 'event:escalation' then 1
        when 'event:in_icu_death' then 2
        when 'event' then 3
        when 'compete' then 4
        when 'censor' then 5
        else 6
    end,
    variable_name;

\o
\pset format aligned
