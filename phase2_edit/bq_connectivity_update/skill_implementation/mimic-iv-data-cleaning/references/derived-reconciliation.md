# MIMIC-IV raw/derived reconciliation

Use this reference when comparing `mimiciv_hosp.labevents` with official
`mimiciv_derived.chemistry` or `mimiciv_derived.bg`. Treat the official derived
tables as reproducible transformations, not as complete raw truth.

## Pinned official logic

The verified source is `mimic-code@303d26c623dcc9c49cc0f204468d4acc2f063797`.

- `chemistry.sql` aggregates by `specimen_id`. BUN uses itemid 51006 and
  `0 < valuenum <= 300`; creatinine uses itemid 50912 and
  `0 < valuenum <= 150`.
- `bg.sql` aggregates by `specimen_id`. Lactate uses itemid 50813 with
  `valuenum <= 10000`, and the blood-gas row is retained only when PO2 itemid
  50821 is non-null in the same `specimen_id`.
- These official transforms do not implement a study-specific landmark
  availability contract. Reconcile against raw
  `GREATEST(charttime, COALESCE(storetime, charttime))` before using a derived
  value as an available predictor.

Pin both MIMIC release and mimic-code commit. Re-check the source if either
changes; do not copy these itemids or limits to another database.

## Project finding, status: proposed

The 2026-09-20 aggregate-only audit of the immutable 5,549-stay MIMIC-IV 3.1
snapshot found:

- BUN both-unequal: 222/222 derived-higher maxima matched contract-correct raw
  results that became available after T12.
- Creatinine both-unequal: 162/162 followed the same pattern.
- Lactate both-unequal: 126/136 were raw-higher maxima whose specimen lacked
  same-specimen PO2; 10/136 were derived-higher maxima explained by late raw
  availability.

These counts are a reproducible project finding, not a universal prevalence
estimate and not a patient-level fact. Keep the rule `proposed`:不得据此自动删除
raw rows, overwrite derived values, change a cohort, or promote a production
filter. 不得写成患者级事实。

## Reusable audit order

1. Match release, cohort, key, index and time window on both sides.
2. Compare coverage in both directions and separate equal from unequal values
   with a declared numeric tolerance.
3. For a derived-higher maximum, test whether the value exists in eligible,
   late, other-quarantine and any raw value sets, in that order.
4. For a raw-higher lactate maximum, test the raw-max `specimen_id` for itemid
   50821 before calling the value unexplained or contaminated.
5. Preserve unresolved rows as unresolved. Export only aggregate cause counts
   unless a separately authorized patient-level investigation is required.
