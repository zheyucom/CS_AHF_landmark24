# MIMIC-IV source provenance

Before activating or comparing a rule, record the exact dataset release and the
official dictionary/schema source used to identify the item. A connection token,
SQL parser success, or SELECT 1 is not evidence that a controlled MIMIC table
was readable.

For every extraction, keep:

- MIMIC release and schema (for example 3.1, mimiciv_hosp);
- official mimic-code commit used for derived concepts;
- source and dictionary table names;
- rule-pack version and rule ID;
- SQL content hash and run status;
- cohort key, index/landmark, predictor and outcome windows;
- whether patient-level execution was passed, failed, not_run, or
  not_run_access_denied.

When a dictionary observation is local to this project, label it as a project
finding. It can support a proposed or explicitly approved quarantine rule, but
does not silently establish a universal clinical definition. Keep deprecated
rules and their replacement so historical outputs remain auditable.
