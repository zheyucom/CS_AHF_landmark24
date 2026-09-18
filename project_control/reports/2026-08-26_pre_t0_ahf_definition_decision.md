# Pre-T0 AHF Definition Decision

日期：2026-08-26  
依据：`T_qualify` 审计与 `093_pre_t0_ahf_definition_audit.sql`

## 核心决定

本研究应保留“患者在 ICU 入科前已经存在 AHF”这一关键设计条件。

正式表述不写成“最终 ICD 在 T0 前已经诊断 AHF”，而写成：

> 本次住院最终存在急性/急性加重 HF 诊断锚点，并且在 ICU 入科前已有可追溯的客观 AHF 时间证据。

原因是 MIMIC-IV 的最终诊断表通常没有实时诊断确认时间。最终 ICD 可作回顾性表型确认，但不能伪装成 T0 前实时诊断时间。

## 推荐时间边界

### 主分析

```text
[hospital admittime, ICU intime)
```

该范围表示：本次住院开始后、进入 ICU 之前已经出现 AHF 相关客观证据。

### 严格敏感性分析

```text
[ICU intime - 24 h, ICU intime)
```

该范围检验“仅使用 ICU 入科前最近 24 h 证据”是否改变样本量、事件率和模型性能。

## AHF 主操作定义

同时满足：

1. acute 或 acute-on-chronic HF ICD；
2. HF 诊断最小序位 `<=5`；
3. 当前住院 ICU 入科前存在以下至少一项：
   - 实际 IV loop diuretic eMAR；
   - NT-proBNP `>=300`。

处方医嘱时间不作为主定义，只做敏感性分析。

## 093 审计结果

当前 `study_ahf_v3.cohort_061D_landmark12_riskset_main_v1`：

| 定义 | stays | 事件 | 事件率 | complete60 | early-sepsis stays |
|---|---:|---:|---:|---:|---:|
| 现有 landmark risk set | 6,301 | 605 | 9.60% | 3,008 | 2,424 |
| pre-T0：admittime 至 ICU | 562 | 57 | 10.14% | 268 | 165 |
| pre-T0：ICU 前 24 h | 280 | 29 | 10.36% | 134 | 95 |
| acute HF ICD + 无合法 pre-T0 时间证据 | 5,116 | 499 | 9.75% | 2,530 | 2,017 |

## 对旧 2,424 例主队列的解释

`T_qualify` 审计显示旧 early-sepsis 主队列中：

- 516 例的执行/检验 AHF 证据在 T0 前；
- 358 例首次证据在 T0-6 h；
- 93 例首次证据在 6-12 h；
- 1,457 例为 ICD-only。

因此旧 `2,424/334` 队列不是“入 ICU 前已确立 AHF”的队列，而是“最终 AHF 表型在 T12 前可被支持”的历史队列。

## 是否存在数据泄露

### 不是典型的 outcome leakage

旧队列没有使用 `T12-T60` 结局数据来计算 AHF 证据，因此不是把未来结局直接喂给模型。

### 但存在目标人群时间不对称

旧队列中部分患者在 ICU 入科后才首次出现 AHF 时间证据，而模型却使用同一 `0-12 h` 窗口进行预测。这样会造成：

- 一部分患者在特征窗口开始时已知 AHF；
- 另一部分患者在特征窗口中途才获得 AHF 支持；
- 还有一部分患者仅依赖最终 ICD。

这会使队列定义与研究问题不一致，并可能让模型学习“被识别/被检测的过程”，而不只是 AHF 患者的恶化风险。

## 研究方向是否需要改变

不需要改变核心方向。应保留：

```text
pre-T0 AHF
-> ICU 0-12 h dynamic observation
-> ICU 12-60 h hemodynamic deterioration
```

需要改变的是：

1. 将 `AHF_pre_T0_admission_to_icu` 设为候选主分析队列；
2. 将 `AHF_pre_T0_last24h` 设为严格敏感性队列；
3. 将旧 `AHF_by_T12` 设为历史/可比性分析；
4. 将 `ICD-only` 明确排除出主模型；
5. 重新评估 early sepsis 是否作为主队列条件，还是作为 pre-T0 AHF-only 队列中的预设亚组。

## 当前样本量判断

### AHF-only

562 stays、57 events 可以支持：

- 低维预先指定特征模型；
- elastic-net 或 ridge；
- 严格重复验证和校准审计；
- 少量预设敏感性分析。

不适合在同一分析中进行大量自由特征选择、复杂交互和多个树模型竞争。

### AHF + early sepsis

当前严格 pre-T0 AHF 与 early-sepsis 的交集：

- admission-to-T0：165 stays；
- ICU 前 24 h：95 stays。

这两个队列事件数不足以训练稳定的高维主模型，暂时应作为高特异性亚群/可行性分析。

## 当前不应做的事

- 不立即覆盖 v3 的 2,424/334 结果；
- 不把 2,424 例继续称为“入 ICU 前 AHF + early sepsis”；
- 不把最终 HF ICD 或诊断序位放入预测器；
- 不因为严格定义样本减少就放弃 pre-T0 AHF 设计；
- 不在未完成 early-sepsis 时间审计前把 AHF+sepsis 作为稳定主模型。

## 下一步

1. 依据 `093` 审计建立新的 `pre-T0 AHF` 队列表；
2. 重新生成 AHF-only modeling base；
3. 先跑低维/预设特征的可行性模型；
4. 同步输出 AHF-only 与 AHF+early-sepsis 的样本量和事件数；
5. 再决定最终论文主队列。
