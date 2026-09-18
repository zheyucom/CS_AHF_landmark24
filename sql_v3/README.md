# SQL v3

Minimal reproducible 12-hour landmark pipeline for schema `study_ahf_v3`.
The current modeling endpoint is `model_080G_modeling_dataset_v2`; `081A` is
an echo-availability screen and is not merged into the primary model.

- `recovered_original/`: byte-for-byte copies recovered from Navicat; never execute or edit.
- `executable/`: isolated copies targeting `study_ahf_v3`.
- `run_v3.sh`: ordered execution with `ON_ERROR_STOP` and one log per SQL file.
- `SOURCE_SHA256.tsv`: checksums for recovered originals.

The executable `001` drops and recreates only `study_ahf_v3`, guaranteeing a
clean run without changing the historical `study_ahf` schema.

The old 24-hour branch, empty `002`, inspection-only SQL, and superseded raw
`070D` are intentionally excluded. The cleaned `070D2` SQL has one v3-only
change: its final comparison to the superseded raw table was removed.
