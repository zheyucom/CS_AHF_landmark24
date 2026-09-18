# CS_AHF_landmark12

> **日常主入口**：见
> [`project_control/RESEARCH_DASHBOARD.md`](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/RESEARCH_DASHBOARD.md)。
> 它记录当前研究方案、已完成成果、阻塞问题、预计投入和最新周报。
>
> 当前项目总控与阶段门见
> [`project_control/README.md`](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/README.md)。
> 历史 `outputs/`、`outputs_v2/`、旧 `2,424/334` 队列和旧模型性能仅作探索/诊断对照；
> 论文最终结果必须来自 v3.3 eligible cohort、无泄露预测变量和可追溯冻结 run。

## Current Status Snapshot

更新时间：2026-08-29

当前主线已经修正为：

**DHF 操作性表型 ICU 患者 T12 landmark 后至 min(T60, 活着离开 index ICU) 的 ICU 内血流动力学恶化竞争风险预测；early sepsis 为预设亚组。DHF 表型正在进行文本/影像验证。**

已完成：

- v3.2 index-admission AHF-by-T12 候选队列重建；
- v3.3 strict 主标签和三态随访结构；
- landmark eligibility reconciliation；
- 1 h person-period v2 构建和 QC。
- 090 compact feature pipeline：45 个预设无泄露预测器、manifest、黑名单/缺失/三表连接 QC。

当前可靠数字：

| Metric | Value |
|---|---:|
| v3.2 candidate stays | 5,564 |
| T12 前/时死亡排除 | 9 |
| v3.3 eligible stays | 5,555 |
| 主事件 | 454 |
| alive ICU discharge competing events | 2,935 |
| administrative censoring at T60 | 2,166 |
| person-period rows | 176,525 |
| early sepsis stays/events | 1,498 / 151 |

当前未完成：完成 Fine-Gray 5 折外层验证并审阅 48 h CIF AUC/Brier/校准，随后进行 person-period、IPCW、complete60、phenylephrine、60 min 和 pre-T0 AHF 敏感性分析。

## Current Study Title

**失代偿性心衰操作性表型 ICU 患者 T12 landmark 后 ICU 内血流动力学恶化风险预测模型研究：基于 MIMIC-IV 的模型开发及本院外部验证**

Suggested English title:

**Early prediction of ICU hemodynamic deterioration after a 12-hour landmark in patients with a decompensated heart failure operational phenotype: model development using MIMIC-IV and external validation in a local hospital cohort**

## Study Question

本研究基于 ICU 入科后 0-12 h 可获得的结构化临床信息，预测失代偿性心衰（DHF）操作性表型 ICU 患者在 T12 后至 T60 或更早活着离开 index ICU 前发生 ICU 内血流动力学恶化的风险。

当前研究不是“已发生心源性休克患者”的预后模型，也不再把 early sepsis 作为唯一主队列限制。研究结构已从旧 v3 的
“AHF + early sepsis12 固定窗口二分类” 修订为：

**先完成 pre-T0 DHF 多域表型验证；early sepsis 为预设亚组；最终主开发队列在样本量/事件数审计和导师确认后冻结。**

在 v3.3 无泄露建模数据冻结前，不将旧的 `2,424/334` 结果作为最终论文主结果。

心源性休克或 mixed shock proxy 在当前版本中作为：

- pre-landmark 排除条件；
- 次要结局；
- 敏感性分析；
- 后续机制和亚组分析方向。

## Data Source

当前模型开发阶段使用：

- MIMIC-IV;
- MIMIC-IV derived tables;
- 本项目自建 `study_ahf` schema。

下一阶段计划使用本院 ICU/住院数据库进行外部验证。

## Study Design

| Item | Definition |
|---|---|
| Index time | ICU `intime` |
| Landmark time | ICU 入科后 12 h, 即 `landmark12_time = intime + 12 hours` |
| Predictor window | ICU 入科 0-12 h |
| Prediction window | ICU 入科 12-60 h，即 landmark 后未来 48 h |
| Unit of analysis | stay-level，每位患者当前主分析保留一个 ICU stay |
| Main model type | Fine-Gray competing-risk model |
| Complementary models | 1 h person-period landmark survival model；IPCW/complete60 固定窗口作为敏感性 |

## Study Population

### Inclusion Criteria

当前修订中的主分析队列拟纳入：

1. 成人 ICU 患者；
2. 每位患者最早 ICU stay；
3. 本次住院存在回顾性 HF ICD anchor；
4. 在最终 DHF 主表型中，`[T0-24 h,T12)` 内需有临床/客观失代偿证据及紧急管理/治疗证据；NT-proBNP 只作支持性证据。该证据不要求全部发生在 ICU 入科前；
5. 可达到 ICU 入科 12 h landmark；
6. ICU 入科 0-12 h 内无 overt shock proxy；
7. 可构建 12-60 h outcome window。

正式方案见
[`study_definition_v5_pre_t0_dhf_landmark12.md`](/Users/zheyu/Desktop/CS_AHF_landmark24/study_definition/study_definition_v5_pre_t0_dhf_landmark12.md)。

### AHF Definition

AHF 相关队列基于：

- HF ICD candidate；
- HF ICD sequence restriction；
- 早期 AHF 支持证据，例如早期 IV loop diuretic prescription、NT-proBNP >=300 等。

旧 v3 主线使用的是 “AHF confirmed by T12”，允许 AHF 时间证据在 ICU 入科后
0-12 h 才出现。该版本保留用于历史对照，不再作为“入 ICU 前已存在 AHF”的正式表述。

### Early Sepsis12 Definition

`early_sepsis12_main_flag = 1` 的患者进入预设亚组。该定义基于 landmark 前可获得的 suspected infection 与 SOFA 相关证据。

在 v3.3 eligible cohort 中：

- early sepsis stays/events = `1,498 / 151`;
- non-sepsis stays/events = `4,057 / 303`;
- early sepsis 不再限制主队列。

### Exclusion Criteria

排除：

1. 非成人；
2. 非首次 ICU stay；
3. 不满足 AHF strict 12 h 证据；
4. 未达到 12 h landmark；
5. ICU 入科 0-12 h 已发生 overt cardiogenic shock proxy；
6. T12 前或 T12 时已死亡，不能进入 T12 landmark 风险集；
7. 关键时间字段缺失；
8. 可能导致 post-landmark 信息泄露的数据项作为预测变量。

## Cohort Flow

旧 v3 数据库 `study_ahf.cohort_flow` 中的历史流程如下，仅作为历史对照：

| Step | Cohort | n |
|---|---:|---:|
| 10 | Adult first ICU | 65,366 |
| 20 | HF ICD candidate | 14,877 |
| 62 | Strict AHF cohort for 12 h landmark | 7,562 |
| 64 | Reached 12 h landmark and excluded pre12 overt CS | 6,301 |
| 67 | AHF + early sepsis12 main analysis cohort | 2,424 |
| 68 | Primary HD deterioration outcome table | 2,424 |
| 070G/080G | Final modeling datasets | 2,424 |

以上数字属于 v3 历史版本，不能作为当前论文最终主结果。新的 pre-T0 AHF 审计 SQL 为
`sql_v3/audits/093_pre_t0_ahf_definition_audit.sql`，完成后将建立独立版本的正式队列和建模数据。

当前候选主线数字见本 README 顶部快照和 `project_control/RESEARCH_DASHBOARD.md`。

## Primary Outcome

主结局为：

**12-60 h hemodynamic deterioration**

对应当前 SQL/Python 中的：

`primary_outcome_flag`

其上游定义为：

`hd_deterioration_broad_nee005_flag`

在 ICU 入科 12 h landmark 后未来 48 h 内发生以下任一事件即记为阳性：

1. 新启用 vasoactive / inotrope support；
2. vasoactive / inotrope 药物种类增加；
3. norepinephrine-equivalent dose 较 0-12 h 最大值增加 >=0.05 ug/kg/min；
4. 12-60 h 内死亡。

以下为旧 v3 固定窗口二分类主结局，保留为历史对照：

| Metric | Value |
|---|---:|
| Total stays | 2,424 |
| Primary outcome events | 334 |
| Event rate | 13.78% |
| Support escalation events | 240 |
| NEE >=0.05 escalation events | 102 |
| Death 12-60 h | 57 |

## Secondary Outcomes and Sensitivity Outcomes

| Outcome | Meaning | Current Events |
|---|---|---:|
| `secondary_hd_deterioration_nee010_flag` | stricter NEE threshold, delta >=0.10 | 315 |
| `secondary_hd_deterioration_no_nee_flag` | hemodynamic deterioration excluding NEE-only events | 282 |
| `secondary_mixed_shock_proxy_flag` | strict mixed shock / CS-like proxy | 133 |
| `secondary_hd_lactate_confirmed_flag` | lactate-confirmed HD | 105 |
| `death_12_60_flag` | death during prediction window | 57 |

## Predictor Principle

所有候选预测变量必须来自 ICU 入科 0-12 h。

建模时自动排除：

- IDs: `subject_id`, `hadm_id`, `stay_id`;
- time anchors: `intime`, `landmark12_time`, `window60_time`;
- primary outcome and all `label_` columns;
- post12 variables;
- death time;
- event time;
- follow-up/censoring variables;
- any variable measured or defined after the 12 h landmark.

后续如果纳入 echo、LVEF、note-derived features，必须明确检查时间、报告时间或临床可用时间在 landmark 前。

## Historical Modeling Datasets

以下数据集属于旧 v3/v2 固定窗口二分类路线，不能作为 v3.3 最终建模输入。当前最终输入需要基于 5,555 eligible stays 重新构建。

| Dataset | Historical Description |
|---|---|
| `model_070G_modeling_dataset_v1.csv` | v1 modeling dataset, baseline feature set |
| `audit_079_event_timing_components_v1.csv` | patient-level event timing and outcome component audit |
| `model_080G_modeling_dataset_v2.csv` | v2 modeling dataset, v1 plus 080A vital burden features |

Raw data exports are saved in:

`CS_AHF_hemodynamic_deterioration_ml_project/data/raw/`

## Historical Feature Engineering Progress

以下模块说明旧特征工程已经覆盖的内容，可作为 v3.3 重建时的参考清单；最终仍需重新审计并排除资格变量、结局变量和 post-landmark 泄露变量。

Completed feature modules:

- static clinical features;
- comorbidities;
- early AHF evidence;
- early sepsis12 variables;
- 0-12 h vital signs;
- 0-12 h laboratory features;
- 0-12 h respiratory, GCS, urine output, vasoactive/inotrope support;
- 0-12 h NEE features;
- 080A dynamic vital burden features.

### 080A Vital Burden Features

080A added:

- MAP <65 and <60 record proportions;
- SBP <90 and <100 record proportions;
- HR >110 and >120 record proportions;
- RR >24 and >30 record proportions;
- SpO2 <90 record proportion;
- shock index;
- modified shock index;
- pulse pressure;
- SBP/MAP/HR/RR/SpO2 slopes.

080A QC:

| Metric | Value |
|---|---:|
| Vital burden availability | 100% |
| Missing MAP <65 burden | 0% |
| Missing shock_index_max | 13.08% |
| Missing SBP slope | 0.04% |

MAP <65 burden event rate:

| MAP <65 burden | Event Rate |
|---|---:|
| none | 10.54% |
| >0 to 25% | 14.57% |
| 25 to 50% | 12.28% |
| >50% | 21.18% |

## Historical Model Performance

以下性能来自旧 `2,424/334` 固定窗口二分类路线，仅作历史探索和诊断材料。当前 v3.3 主模型尚未完成，不能引用这些数字作为论文最终模型性能。

Best historical model:

**v2 top80 elastic-net + Platt calibration**

50-repeat internal validation:

| Model | AUROC | AUPRC | Brier |
|---|---:|---:|---:|
| v1 top80 elastic-net | 0.7536 | 0.3374 | 0.10695 |
| v2 top80 elastic-net | 0.7588 | 0.3453 | 0.10616 |
| v2 top80 LightGBM | 0.7479 | 0.3449 | 0.10684 |
| v2 top50 HistGB | 0.7451 | 0.3369 | 0.10763 |

Top-risk enrichment:

| Model | Top 10% Event Rate | Top 20% Event Rate | Top 20% Capture |
|---|---:|---:|---:|
| v1 top80 elastic-net | 39.80% | 32.47% | 47.01% |
| v2 top80 elastic-net | 42.04% | 33.28% | 48.18% |

Interpretation:

- 080A dynamic vital burden features provide a small but stable improvement;
- elastic-net remains more stable and interpretable than LightGBM;
- LightGBM is retained as a benchmark, not the current primary model.

## Historical Audit Results

以下审计结果来自旧固定窗口二分类路线，可解释为什么后来需要重写 strict label 和竞争风险 estimand；最终论文主结果应优先引用 v3.2/v3.3 审计。

### 078 Error Analysis

Fixed test split:

| Group | n |
|---|---:|
| True positive | 22 |
| False positive | 75 |
| False negative | 45 |
| True negative | 343 |

Key findings:

- 56.0% of false positives had pre12 shock proxy but no primary outcome;
- 64.4% of false negatives were support-escalation-only events;
- 71.1% of false negatives had no pre12 shock signal.

Implication:

The main bottleneck is not just model class. Important limitations include label noise, treatment-behavior variation, post-landmark clinical changes, and missing high-value physiologic features.

### 079A Event Timing Audit

| Metric | Value |
|---|---:|
| Primary label events | 334 |
| Timing events | 334 |
| Label/timing mismatch | 0 |
| 12-36 h events | 248 |
| 12-48 h events | 301 |
| 12-60 h events | 334 |

First event component:

| Component | n |
|---|---:|
| support escalation | 218 |
| NEE >=0.05 escalation | 74 |
| death | 42 |

## External Validation Plan

下一阶段将在本院数据库中进行外部验证。

本院数据需尽量复刻 v3.3 当前定义：

1. 成人 ICU stay；
2. AHF evidence；
3. index hospitalization 内首次 ICU stay；
4. 12 h landmark；
5. 排除 T12 前/时已死亡或 0-12 h overt shock proxy；
6. 0-12 h predictors；
7. T12 至 T60 或 alive index-ICU discharge 前 ICU 内 hemodynamic deterioration；
8. alive ICU discharge competing event；
9. early sepsis12 作为预设亚组；
10. pre-T0 AHF 作为严格敏感性分析。

External validation workflow:

1. 构建本院 AHF landmark12 队列，并标记 early sepsis 亚组；
2. 对齐变量名、单位、时间窗和缺失编码；
3. 在查看本院结局前锁定 MIMIC 模型；
4. 直接应用 MIMIC 训练模型；
5. 评估 competing-risk AUC、Brier、calibration、CIF 和风险分层；
6. 如校准偏移明显，进行 recalibration；
7. 再考虑模型更新或院内特征增强。

## Next Feature Directions

优先级从高到低：

1. 080B lactate / acid-base trends；
2. 080C fluid balance, urine output, diuretic dose and response；
3. 080D BNP/NT-proBNP, troponin, CK-MB；
4. 080E echo, LVEF, RV dysfunction；
5. SOFA component-level features；
6. infection source and treatment context；
7. prespecified subgroup models.

Current decision:

Do not promote old LightGBM/logistic results as the main model. Current priority is v3.3 no-leakage feature reconstruction, Fine-Gray competing-risk validation, and prespecified sensitivity analyses.

## Repository Structure

| Path | Purpose |
|---|---|
| `sql/` | SQL cohort, outcome, audit, and feature construction |
| `sql_results/` | SQL QC exports |
| `study_definition/` | study definition history and protocol notes |
| `CS_AHF_hemodynamic_deterioration_ml_project/data/raw/` | exported modeling and audit CSVs |
| `CS_AHF_hemodynamic_deterioration_ml_project/scripts/` | reproducible Python analysis scripts |
| `CS_AHF_hemodynamic_deterioration_ml_project/src/` | reusable Python package code |
| `CS_AHF_hemodynamic_deterioration_ml_project/outputs/` | v1 outputs and historical analyses |
| `CS_AHF_hemodynamic_deterioration_ml_project/outputs_v2/` | v2 outputs after adding 080A features |
| `CS_AHF_hemodynamic_deterioration_ml_project/docs/` | feature manifest and model documentation |

## Historical Note

This project originally considered a 24 h landmark design focused on new overt cardiogenic shock among AHF patients. During cohort and outcome audits, the main analysis was first updated to a 12 h landmark AHF + early sepsis12 fixed-window cohort, and then revised again to the current AHF-by-T12 competing-risk framework.

The older CS-focused and early-sepsis-only definitions are retained for historical context and secondary/sensitivity analyses, but the current primary study is the 12 h landmark competing-risk hemodynamic deterioration prediction model described above.
