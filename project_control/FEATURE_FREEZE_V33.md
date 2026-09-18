# v3.3 Feature Freeze

更新时间：2026-09-04

## 冻结结论

主分析已经定死：

- 主模型：`Fine-Gray` competing-risk
- 补充模型：`1 h person-period` landmark survival
- 主事件：ICU 内血流动力学恶化 + ICU 内死亡
- 竞争事件：alive index-ICU discharge
- 主队列：`v3.3 eligible cohort`，`n = 5,555`

## 已决策

1. `AHF` 资格变量不进主预测器。
2. `pre12_overt_cs_*` 只做资格审计/敏感性，不进主预测器。
3. `ICU 内死亡` 保留在 composite 主事件。
4. `pre-T0 AHF` 作为严格敏感性分析，不取代主分析。
5. 主文采用一个紧凑主模型，宽特征模型只做敏感性比较。

## 黑名单

以下列不进主预测器：

- 所有 ID / 时间锚点 / 结局列
  - `subject_id`
  - `hadm_id`
  - `stay_id`
  - `intime`
  - `landmark12_time`
  - `window60_time`
  - `final_state`
  - `final_time`
  - `event_type`
  - `death_after_exit_flag`
  - `esc_confirm_time`
  - `in_icu_death_time`
  - `period_status*`
  - `event_period_flag`
  - `compete_period_flag`
  - `censor_period_flag`
- 所有 AHF 资格定义列
  - `hf_icd_primary_seq`
  - `hf_icd_seq_eq1_flag`
  - `hf_icd_seq_2_5_flag`
  - `acute_hf_icd_flag`
  - `hf_icd_seq_le5`
  - `iv_loop_rx_early12_flag`
  - `ntprobnp_ge300_early12_flag`
  - `ahf_evidence_score_primary_12h`
- 所有 infection / sepsis 资格定义列
  - `suspected_infection_before_icu_flag`
  - `suspected_infection_icu_0_6h_flag`
  - `suspected_infection_icu_6_12h_flag`
  - `early_sepsis12_max_sofa_score`
  - `early_sepsis12_suspected_infection_hour`
  - `early_sepsis12_sofa_hour`
- 所有 pre12 overt CS 资格列
  - `pre12_overt_cs_main_flag`
  - `pre12_overt_cs_very_strict_flag`
  - `pre12_overt_cs_broad_flag`
- 所有 outcome-derived baseline support 聚合列
  - `nee_0_12h_max`
  - `vasoactive_agent_count_0_12h`
  - 任何直接复述 `pre12_nee_max` / `pre12_max_agent_count` 的重复列

## 白名单原则

主模型只保留三类特征：

1. 基线人口学和就诊入口信息
2. 0-12 h 临床状态摘要
3. 0-12 h 支持治疗的结构性描述

### 1. 基线人口学和就诊入口

- `age`
- `female` / `male`
- 首次 ICU unit 类型
  - `first_unit_micu_flag`
  - `first_unit_ccu_cicu_flag`
  - `first_unit_sicu_flag`
  - `first_unit_cvicu_flag`

### 2. 0-12 h 临床状态摘要

只保留每个生理域少量统计量，不要把同一域的所有衍生列全放进主模型。

建议优先：

- 心率：`mean`, `min`, `max`, `delta`
- 收缩压 / MAP：`mean`, `min`, `max`, `delta`
- 呼吸频率：`mean`, `min`, `max`, `delta`
- SpO2：`mean`, `min`, `max`, `delta`
- 乳酸：`max`, `mean`, `delta`
- 肾功能：`creatinine_max`, `creatinine_delta`, `bun_max`
- 酸碱 / 灌注：`ph_min`, `baseexcess_min`, `lactate_max`
- 主要电解质：`sodium_min/max`, `potassium_min/max`
- 血象：`wbc_max`, `hemoglobin_min`, `platelet_min`

### 3. 0-12 h 支持治疗结构描述

保留“有无与结构”，不要把事件定义本身重复放进特征表。

建议优先：

- vasoactive / inotrope 是否使用
- 第一次使用时间距 T0 的相对位置
- 药物种类计数
- 单药剂量摘要
- respiratory support 摘要
- urine output / fluid balance 摘要

## 特征规模策略

主文采用：

- 预先冻结的紧凑特征集，约 `30-45` 个候选特征
- 折内 elastic-net 仅作为收缩/筛选机制，不允许全自由扩列
- 额外更宽的全特征模型只做敏感性比较

不推荐：

- 把 070/080/081 的全部衍生列直接扔进主模型
- 让 `EPV=454` 承担三百列自由度

## 需要保留的诊断列

以下列可保留在审计表，不进主模型：

- `pre12_max_agent_count`
- `pre12_nee_max`
- `pre12_nee_last`
- `pre12_nee_historic`
- `early_sepsis12_main_flag`
- `death_after_exit_flag`

这些用于审计、分层、敏感性或标签解释。

## Compact-feature QC 修订

初版 45 特征表跑通后发现：

- `bg_bicarbonate_min` 缺失率 99.28%
- `pf_ratio_min` 缺失率 72.31%

因此这两个变量不进入主模型紧凑特征集，改用同一 0-12 h 窗口内覆盖更稳定的：

- `dbp_min`
- `modified_shock_index_max`

2026-09-04 的来源审计还发现，`mimiciv_derived.bg` 遗漏了 550 个有效的 ICU 0-12 h 原始乳酸记录。因此：

- `lactate_max` 和 `lactate_delta` 的唯一正式来源为 `mimiciv_hosp.labevents` 的 `itemid=50813`；
- 连接键为 `subject_id + hadm_id`，时间窗严格为 `[intime, landmark12_time)`，有效范围为 `0-30 mmol/L`；
- 090B/090C/090D 已用此定义重建，乳酸两项缺失为 `2,641/5,555 (47.54%)`；
- `ph_min` 和 `baseexcess_min` 暂仍来自 `mimiciv_derived.bg`，其约 46% 的缺失进入预设的折内缺失处理，不能因这一结果事后扩大预测窗。
