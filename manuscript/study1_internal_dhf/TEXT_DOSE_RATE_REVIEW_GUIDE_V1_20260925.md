# Text dose/rate support review guide V1

Date: 2026-09-25
Status: ready_for_blinded_pilot / not_a_medication_administration_gold_standard

## Purpose

This review evaluates whether the rule-based NLP correctly links a local dose or rate phrase to the named target drug. It does not establish that a medication was administered, does not reconstruct pump settings, and does not change the frozen 81-event treatment-proxy ledger.

Review pack:

/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/20260925_internal_stage1_text_dose_extract/text_dose_rate_review_sample_v1.csv

The pack contains 154 rows from 81 strata. Each row keeps the patient/visit key, document metadata, raw evidence snippet, source reference, polarity, context type, and dose_rate_ambiguity.

## Review fields

Fill only the following columns:

- review_status: confirmed, false_positive, uncertain, or not_reviewable.
- reviewer: reviewer initials or coded identifier.
- confirmed_drug: yes / no / uncertain.
- confirmed_dose: yes / no / uncertain / not_present.
- confirmed_rate: yes / no / uncertain / not_present.
- review_notes: brief reason, especially the competing drug, negation, template, or missing context.

Do not overwrite the extracted fields or delete the source reference.

## Review order

1. Read the complete local evidence snippet and document name before deciding.
2. Decide whether the mention refers to the patient, a score/template/reference example, or a negated/uncertain statement.
3. Confirm drug identity first.
4. Confirm dose or rate only when the value is locally attributable to that drug. If two target drugs share one paragraph and attribution is unclear, mark uncertain and retain the ambiguity flag.
5. Do not infer administration from an order, plan, medication list, or retrospective summary. If the text only supports planned/ordered treatment, note this explicitly.
6. A rate such as ml/h is not a dose unless the concentration and drug attribution are explicit; do not convert it to dose or NEE.
7. A numeric value in SOFA/APACHE or another scoring template is reference text, not clinical exposure.

## Double review and reporting

At least 20% of rows should be independently reviewed by a second clinician; all disagreement rows should be adjudicated. Report:

- drug-mention precision;
- dose-text attribution precision;
- rate-text attribution precision;
- proportions of uncertain and template/reference rows;
- common false-positive categories.

These metrics are support-layer QC only. They must not be used to relabel a treatment-proxy event without a separate, pre-specified amendment. The frozen treatment proxy remains order-based and is not eMAR-confirmed.
