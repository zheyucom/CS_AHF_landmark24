-- Structured echocardiography availability audit for the v3.3 DHF phenotype.
-- This query is deliberately limited to procedure occurrence and the sparse
-- structured LVEF item. A procedure flag is not an abnormal echo result.
-- The table is an audit/sensitivity input, not a predictor table.

DROP TABLE IF EXISTS study_ahf_v3_2.audit_108_structured_echo_screen_v33_v1;

CREATE TABLE study_ahf_v3_2.audit_108_structured_echo_screen_v33_v1 AS
WITH base AS (
    SELECT
        subject_id,
        hadm_id,
        stay_id,
        intime,
        landmark12_time
    FROM study_ahf_v3_2.model_098_strict_label_v33_v1
),
echo_rows AS (
    SELECT
        b.stay_id,
        pe.itemid,
        pe.starttime,
        pe.endtime,
        EXTRACT(EPOCH FROM (pe.starttime - b.intime)) / 3600.0 AS hour_from_icu
    FROM base b
    JOIN mimiciv_icu.procedureevents pe
      ON pe.stay_id = b.stay_id
     AND pe.itemid IN (221255, 225432)
     AND pe.starttime < b.landmark12_time
     AND COALESCE(pe.endtime, pe.starttime) >= b.intime - INTERVAL '24 hour'
),
echo_summary AS (
    SELECT
        stay_id,
        COUNT(*) AS echo_procedure_pre12_n,
        COUNT(*) FILTER (WHERE itemid = 225432) AS tte_procedure_pre12_n,
        COUNT(*) FILTER (WHERE itemid = 221255) AS tee_procedure_pre12_n,
        MAX((itemid = 225432)::int) AS tte_procedure_pre12_flag,
        MAX((itemid = 221255)::int) AS tee_procedure_pre12_flag,
        1 AS echo_any_procedure_pre12_flag,
        MAX((hour_from_icu >= 0 AND hour_from_icu < 12)::int)
            AS echo_any_procedure_0_12h_flag,
        MAX((itemid = 225432 AND hour_from_icu >= 0 AND hour_from_icu < 12)::int)
            AS tte_procedure_0_12h_flag,
        MAX((itemid = 221255 AND hour_from_icu >= 0 AND hour_from_icu < 12)::int)
            AS tee_procedure_0_12h_flag,
        MIN(starttime) AS first_echo_procedure_pre12_time,
        MAX(starttime) AS last_echo_procedure_pre12_time,
        MIN(hour_from_icu) AS first_echo_procedure_hour_from_icu,
        MAX(hour_from_icu) AS last_echo_procedure_hour_from_icu
    FROM echo_rows
    GROUP BY stay_id
),
lvef_rows AS (
    SELECT
        b.stay_id,
        ce.charttime,
        EXTRACT(EPOCH FROM (ce.charttime - b.intime)) / 3600.0 AS hour_from_icu,
        ce.valuenum AS lvef_value
    FROM base b
    JOIN mimiciv_icu.chartevents ce
      ON ce.stay_id = b.stay_id
     AND ce.itemid = 227008
     AND ce.charttime >= b.intime - INTERVAL '7 day'
     AND ce.charttime < b.landmark12_time
     AND ce.valuenum BETWEEN 5 AND 90
),
lvef_summary AS (
    SELECT
        stay_id,
        COUNT(*) AS structured_lvef_pre12_n,
        MIN(lvef_value) AS structured_lvef_pre12_min,
        MAX(lvef_value) AS structured_lvef_pre12_max,
        AVG(lvef_value) AS structured_lvef_pre12_mean,
        MIN(charttime) AS first_structured_lvef_pre12_time,
        MAX(charttime) AS last_structured_lvef_pre12_time
    FROM lvef_rows
    GROUP BY stay_id
),
lvef_last AS (
    SELECT DISTINCT ON (stay_id)
        stay_id,
        lvef_value AS structured_lvef_pre12_last
    FROM lvef_rows
    ORDER BY stay_id, charttime DESC
)
SELECT
    b.subject_id,
    b.hadm_id,
    b.stay_id,
    COALESCE(e.echo_procedure_pre12_n, 0) AS echo_procedure_pre12_n,
    COALESCE(e.tte_procedure_pre12_n, 0) AS tte_procedure_pre12_n,
    COALESCE(e.tee_procedure_pre12_n, 0) AS tee_procedure_pre12_n,
    COALESCE(e.echo_any_procedure_pre12_flag, 0) AS echo_any_procedure_pre12_flag,
    COALESCE(e.tte_procedure_pre12_flag, 0) AS tte_procedure_pre12_flag,
    COALESCE(e.tee_procedure_pre12_flag, 0) AS tee_procedure_pre12_flag,
    COALESCE(e.echo_any_procedure_0_12h_flag, 0) AS echo_any_procedure_0_12h_flag,
    COALESCE(e.tte_procedure_0_12h_flag, 0) AS tte_procedure_0_12h_flag,
    COALESCE(e.tee_procedure_0_12h_flag, 0) AS tee_procedure_0_12h_flag,
    e.first_echo_procedure_pre12_time,
    e.last_echo_procedure_pre12_time,
    e.first_echo_procedure_hour_from_icu,
    e.last_echo_procedure_hour_from_icu,
    COALESCE(l.structured_lvef_pre12_n, 0) AS structured_lvef_pre12_n,
    (COALESCE(l.structured_lvef_pre12_n, 0) > 0)::int AS structured_lvef_pre12_available_flag,
    l.structured_lvef_pre12_min,
    l.structured_lvef_pre12_max,
    l.structured_lvef_pre12_mean,
    ll.structured_lvef_pre12_last,
    (ll.structured_lvef_pre12_last < 40)::int AS structured_lvef_last_lt40_flag,
    (ll.structured_lvef_pre12_last < 50)::int AS structured_lvef_last_lt50_flag,
    l.first_structured_lvef_pre12_time,
    l.last_structured_lvef_pre12_time,
    '108_v33; procedure_availability_only; structured_lvef_item_227008; no_echo_text' AS rule_version
FROM base b
LEFT JOIN echo_summary e ON e.stay_id = b.stay_id
LEFT JOIN lvef_summary l ON l.stay_id = b.stay_id
LEFT JOIN lvef_last ll ON ll.stay_id = b.stay_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_108_echo_stay
    ON study_ahf_v3_2.audit_108_structured_echo_screen_v33_v1 (stay_id);

ANALYZE study_ahf_v3_2.audit_108_structured_echo_screen_v33_v1;

SELECT
    COUNT(*) AS n_stays,
    SUM(echo_any_procedure_pre12_flag) AS n_echo_procedure_pre12,
    SUM(tte_procedure_pre12_flag) AS n_tte_pre12,
    SUM(tee_procedure_pre12_flag) AS n_tee_pre12,
    SUM(structured_lvef_pre12_available_flag) AS n_structured_lvef_available
FROM study_ahf_v3_2.audit_108_structured_echo_screen_v33_v1;
