---
name: mimic-iv-data-cleaning
description: Audit and guide MIMIC-IV extraction, cleaning, SQL, and feature construction with fail-closed laboratory contracts for itemid, fluid, category, unit, result-availability time, duplicate specimens, censored values, missingness, and raw-versus-derived coverage. Use when Codex works on MIMIC-IV data cleaning or extraction, reviews MIMIC SQL or derived concepts, investigates raw/derived count differences, or records a newly discovered MIMIC cleaning rule.
---

# MIMIC-IV Data Cleaning

Prevent silent semantic contamination and time leakage. Preserve raw provenance, quarantine uncertainty, and distinguish a static audit from a patient-level data run.

## Start Here

1. Read `references/workflow.md` before extracting, cleaning, or freezing features.
2. Read `references/mimic-iv-lab-rules.json` for laboratory contracts. Run:

   ```bash
   python3 scripts/validate_rule_pack.py references/mimic-iv-lab-rules.json
   ```

3. Read `references/source-provenance.md` before changing a rule or claiming compatibility with a MIMIC release.
4. Read `references/derived-reconciliation.md` when comparing raw `labevents` with official `chemistry`/`bg` or investigating max-value differences.
5. Read `references/rule-schema.md` when proposing, promoting, or deprecating a rule.
6. Read `references/evidence-policy.md` before learning from a paper, public pipeline, or general database-cleaning method.
7. For SQL input, run the read-only scanner before manual review:

   ```bash
   python3 scripts/audit_mimic_sql.py path/to/query.sql
   ```

Treat scanner output as preflight evidence, not proof that SQL or clinical logic is correct.

## Required Workflow

1. Confirm the exact MIMIC-IV release, schema, source tables, cohort unit, index, landmark, predictor window, outcome window, and official `mimic-code` commit.
2. Verify access to the metadata and source tables before a patient-level run. Connectivity (`SELECT 1`) and SQL dry-run are not data authorization. If a source table returns `Access Denied`, stop and report `not_run_access_denied`; do not bypass controls, substitute an unapproved mirror, or claim that data were audited.
3. If version, dictionary, join path, or time contract is unknown, stop filtering and report `not_run`; do not guess.
4. Validate each concept against exact `itemid × fluid × category × unit`. Use names or regex only to discover candidates.
5. Preserve source row identifiers, `value`, `valuenum`, `valueuom`, comparison operator/boundary, `charttime`, `storetime`, `specimen_id`, flag, comments, source table, and applied rule ID before normalization.
6. Gate laboratory availability with `GREATEST(charttime, COALESCE(storetime, charttime))`. Use an exclusive window end unless the research contract explicitly says otherwise.
7. Quarantine unknown itemids, units, fluid/category mismatches, late results, time inversions, ambiguous episode joins, and conflicting duplicates. Never silently delete, winsorize, convert, or zero-fill them.
8. Declare the scientific purpose of first/last/min/max aggregation. Audit `specimen_id × itemid` before collapsing duplicates.
9. For every core variable with a derived concept, report `raw_only`, `derived_only`, and `both` using the same cohort, join keys, and time window.
10. Produce the four outputs in `references/workflow.md`. If no authorized database connection was used, say `not_run` or `not_run_access_denied` and retain executable SQL.

## Hard Rules

- Accept BUN as the blood concept only through active rule `lab-bun-blood-v1`; quarantine urine, other-body-fluid, and ascites itemids.
- Do not infer analyte identity from label similarity or a plausible numeric range.
- Do not treat official derived tables as complete raw truth; reconcile both directions.
- Do not turn `<x`, `>x`, or interval text into an exact value. Preserve censor type and boundary.
- Do not use a result merely because its `charttime` is before the landmark when `storetime` makes it unavailable.
- Do not fill an unmeasured laboratory or urine output with zero.
- Do not promote a new rule to `active` without a source, a failing fixture, a passing regression, and human approval.

## Learning Loop

When a new failure is found:

1. Add it as `proposed` with the trigger, risk, applicable version, and quarantine-first action.
2. Attach an official dictionary/concept source or a reproducible project finding.
3. Add the smallest synthetic fixture that fails before the rule exists.
4. Implement the smallest change and run all fixtures.
5. Keep the rule non-enforcing until a human records approval; never self-promote it.
6. Preserve deprecated rules with their replacement and reason.

Run all bundled regression fixtures after any change:

```bash
python3 scripts/test_fixtures.py
```

## Boundaries

- Never bundle patient-level rows, credentials, database tokens, local absolute paths, or project-private identifiers in this Skill.
- Do not modify an existing cohort or SQL in audit mode. Report findings and propose a patch separately.
- Keep medication, urine-output, and vital-sign rules advisory until their independent rule packs have equivalent evidence and fixtures.
- Build separate dataset adapters for eICU or OMOP; reuse the lifecycle, not MIMIC itemids.
