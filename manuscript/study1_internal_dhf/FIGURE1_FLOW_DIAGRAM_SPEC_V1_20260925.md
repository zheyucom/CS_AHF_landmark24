# Figure 1 flow diagram specification V1

Use the accompanying CSV:
project_control/runs/20260925_internal_stage1_flowchart_data_v1.csv

## Boxes

1. Source frame: 8,385 adult ICU episodes with bedside echocardiography.
2. Algorithmic screens: A current HF anchor 2,035; B decompensation/congestion 3,168; C evidence branches: NT-proBNP rule-in 1,283, echo abnormality 1,083, IV loop-order proxy 1,215.
3. Primary cohort: A+B+C 773 episodes; label as algorithmic operational phenotype, clinical calibration pending.
4. Strict objective sensitivity layer: 594 episodes.
5. T12 landmark risk set: 558 episodes; explicitly state this layer is used for short pathway description and Studies 2/3, not as the uniform start point for Study 1 hospital mortality.
6. Outcomes: primary cohort hospital death 62; T12 short proxy outcome composition: target event 81, competing discharge from index ICU 150, administrative censor 273, unknown 54.

## Required annotations

- T0 is index ICU admission time.
- A+B+C may be retrospectively confirmed within [T0,T12).
- The treatment branch is an order-based exposure proxy, not eMAR-confirmed administration.
- Unknown is not negative.
- V2 text-expanded cohort (784) is not shown in the primary flow and remains an exploratory candidate pending clinical review.
