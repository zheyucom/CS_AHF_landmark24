-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/00_setup/001_create_schema_and_manifest.sql
-- Purpose:
--   1. Create project schema.
--   2. Create manifest tables for traceability.
--   3. Avoid uncontrolled accumulation of temporary tables.
-- ============================================================

drop schema if exists study_ahf_v3 cascade;
create schema study_ahf_v3;

drop table if exists study_ahf_v3.run_manifest cascade;

create table study_ahf_v3.run_manifest (
    run_id              bigserial primary key,
    table_name          text not null,
    sql_file            text,
    created_at          timestamp default current_timestamp,
    n_rows              bigint,
    n_subjects          bigint,
    n_hadm              bigint,
    n_stay              bigint,
    n_events            bigint,
    event_rate          numeric,
    time_window         text,
    version_tag         text,
    notes               text
);

drop table if exists study_ahf_v3.cohort_flow cascade;

create table study_ahf_v3.cohort_flow (
    step_id             integer,
    step_name           text,
    table_name          text,
    n_rows              bigint,
    n_subjects          bigint,
    n_hadm              bigint,
    n_stay              bigint,
    excluded_from_prior bigint,
    notes               text,
    created_at          timestamp default current_timestamp
);

drop table if exists study_ahf_v3.feature_dictionary cascade;

create table study_ahf_v3.feature_dictionary (
    feature_name        text primary key,
    feature_group       text,
    source_table        text,
    source_itemid       text,
    time_window         text,
    unit                text,
    aggregation_method  text,
    cleaning_rule       text,
    missing_rule        text,
    leakage_risk        text,
    notes               text
);
