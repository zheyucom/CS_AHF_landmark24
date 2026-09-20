-- Aggregate-only audit for the 063A v2 -> v3 lactate window correction.
-- Run after creating v3 in the same transaction. The final output contains no
-- patient, admission, stay, or laboratory-event identifiers.

WITH late_pre12 AS (
    SELECT
        b.stay_id,
        le.labevent_id,
        count(*) OVER (PARTITION BY le.labevent_id) AS episode_match_count
    FROM study_ahf_v3_3.outcome_061E_post12_overt_cs_future48h_main_v2 b
    JOIN study_ahf_v3_3.lab_eligible_v1 le
      ON le.subject_id = b.subject_id
     AND le.hadm_id = b.hadm_id
     AND le.concept = 'lactate'
     AND le.charttime >= b.intime
     AND le.charttime < b.landmark12_time
     AND le.availability_time >= b.landmark12_time
     AND le.availability_time < b.observed_until_time
),
late_aggregate AS (
    SELECT
        count(*) FILTER (WHERE episode_match_count = 1) AS excluded_late_event_n,
        count(DISTINCT stay_id) FILTER (WHERE episode_match_count = 1) AS affected_stay_n
    FROM late_pre12
),
version_comparison AS (
    SELECT
        count(*) AS matched_stay_n,
        count(*) FILTER (
            WHERE old.pre12_lactate_contract_max IS DISTINCT FROM
                  new.pre12_lactate_contract_max
        ) AS pre12_max_changed_n,
        count(*) FILTER (
            WHERE old.pre12_lactate_contract_min IS DISTINCT FROM
                  new.pre12_lactate_contract_min
        ) AS pre12_min_changed_n,
        count(*) FILTER (
            WHERE old.pre12_lactate_contract_last IS DISTINCT FROM
                  new.pre12_lactate_contract_last
        ) AS pre12_last_changed_n,
        count(*) FILTER (
            WHERE old.post12_lactate_contract_max IS DISTINCT FROM
                  new.post12_lactate_contract_max
        ) AS post12_max_changed_n,
        count(*) FILTER (
            WHERE old.lactate_new_ge2_flag IS DISTINCT FROM
                  new.lactate_new_ge2_flag
        ) AS new_ge2_changed_n,
        count(*) FILTER (
            WHERE old.lactate_2to4_worsen_ge4_flag IS DISTINCT FROM
                  new.lactate_2to4_worsen_ge4_flag
        ) AS worsen_ge4_changed_n,
        count(*) FILTER (
            WHERE old.lactate_delta_ge2_from_last_flag IS DISTINCT FROM
                  new.lactate_delta_ge2_from_last_flag
        ) AS delta_ge2_changed_n,
        count(*) FILTER (
            WHERE old.hd_deterioration_lac_confirmed_flag IS DISTINCT FROM
                  new.hd_deterioration_lac_confirmed_flag
        ) AS composite_changed_n
    FROM study_ahf_v3_3.outcome_063A_candidate_hd_outcomes_overall_v2 old
    JOIN study_ahf_v3_3.outcome_063A_candidate_hd_outcomes_overall_v3 new
      USING (stay_id)
)
-- FINAL_AGGREGATE_OUTPUT
SELECT
    l.excluded_late_event_n,
    l.affected_stay_n,
    v.matched_stay_n,
    v.pre12_max_changed_n,
    v.pre12_min_changed_n,
    v.pre12_last_changed_n,
    v.post12_max_changed_n,
    v.new_ge2_changed_n,
    v.worsen_ge4_changed_n,
    v.delta_ge2_changed_n,
    v.composite_changed_n
FROM late_aggregate l
CROSS JOIN version_comparison v;
