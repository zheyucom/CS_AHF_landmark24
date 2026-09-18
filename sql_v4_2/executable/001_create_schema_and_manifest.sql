-- ============================================================
-- Project: CS_AHF_landmark24
-- Version: v4.2 AHF-only, strict pre-T0 AHF
-- Purpose: isolated schema for the AHF-only feasibility analysis.
-- ============================================================

drop schema if exists study_ahf_v4_2 cascade;
create schema study_ahf_v4_2;

create table study_ahf_v4_2.run_manifest (
    run_id bigserial primary key,
    table_name text not null,
    sql_file text,
    created_at timestamp default current_timestamp,
    n_rows bigint,
    n_subjects bigint,
    n_hadm bigint,
    n_stay bigint,
    n_events bigint,
    event_rate numeric,
    time_window text,
    version_tag text,
    notes text
);

create table study_ahf_v4_2.cohort_flow (
    step_id integer,
    step_name text,
    table_name text,
    n_rows bigint,
    n_subjects bigint,
    n_hadm bigint,
    n_stay bigint,
    excluded_from_prior bigint,
    notes text,
    created_at timestamp default current_timestamp
);
