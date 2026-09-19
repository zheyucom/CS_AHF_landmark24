# MIMIC-IV rule schema

The JSON rule pack is declarative and versioned.

Top-level fields:

- schema_version: semantic version of this rule-pack schema.
- dataset: must identify MIMIC-IV and one or more supported releases.
- governance: requires explicit approval before active.
- rules: one or more concept contracts.

Each rule declares an exact allow contract (itemid, dictionary fluid,
category, and allowed units) and a quarantine list of known candidates that
must never enter the feature without an explicit new rule. The two itemid sets
must be disjoint.

The time contract uses the first time the result is available:

GREATEST(charttime, COALESCE(storetime, charttime))

A rule must specify fail-closed handling for unknown units, fluid mismatch,
duplicate specimen_id x itemid, and censored values. Active rules also carry
evidence sources, fixture IDs, and an approval record. This schema records
decisions; it does not prove that the database query succeeded or that a
clinical threshold is scientifically valid.
