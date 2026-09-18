# BigQuery Web Console Execution - 2026-09-04

## Purpose

Use the authenticated Google Cloud BigQuery web console as the execution path for
MIMIC-IV-Note SQL, because the Codex process still times out when it calls Google
APIs directly.

## Confirmed

- Billing project: `project-9386bb9f-de39-47eb-886`.
- Account: `zheyu.sy@gmail.com`.
- A web-console `SELECT 1 AS connectivity_ok` job completed successfully in US.
- This confirms that web-console query jobs are a valid replacement for the
  blocked Codex CLI/API network path; it does not change project credentials or
  permissions.

## Web-Console Queries

- `109_query_landmark12_dhf_radiology.sql` completed in the web console and
  created `ahf_work.dhf_radiology_raw_landmark12_v1`.
- `110_query_landmark12_dhf_radiology_patient_summary.sql` completed and created
  `ahf_work.dhf_radiology_patient_summary_landmark12_v1`.

## Main-window QC

The read-only QC query against the `110` output returned:

| Metric | Value |
|---|---:|
| Valid candidate stays | 5,549 |
| Stays with any report in `[T0-24 h,T12)` | 3,886 |
| Stays with report available by T12 | 3,542 |
| All reports | 7,828 |
| Reports available by T12 | 6,415 |
| Reports with missing `storetime` | 0 |
| Regex-positive stays / definite regex-positive stays | 2,707 / 2,321 |
| Stays with an available regex-positive report | 2,350 |

The positive counts remain screening-rule outputs, not confirmed DHF labels.

## Design Guardrail

The `[T0-24 h, T12)` radiology text is phenotype evidence only. It must remain
physically separate from the `[T0, T12)` predictor matrix and is not a model
feature.
