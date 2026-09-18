# Study Definition v4.0: Pre-T0 AHF and 12 h Landmark Prediction

更新日期：2026-08-26  
状态：历史 AHF 方案草案，已被 `study_definition_v5_pre_t0_dhf_landmark12.md` 的 ESC 2026 DHF 方案取代；仅保留审计可追溯性。

## 1. 研究问题

在成人首次 ICU stay 中，若患者在**本次住院期间、进入 ICU 之前已经具备可追溯的急性心力衰竭临床证据**，且 ICU 入科后最初 12 h 尚未出现预设的显性休克代理指标，能否利用 ICU `0-12 h` 的信息预测随后 `12-60 h` 内发生治疗升级相关血流动力学恶化？

当前研究不把“ICU 入科后才首次出现 AHF 证据”的患者作为主队列。否则研究问题会变成“在 ICU 0-12 h 内识别为 AHF 的患者，其后续恶化风险”，而不是“已存在 AHF 患者的后续恶化预测”。

## 2. 研究对象与分析单位

### 2.1 分析单位

- 一行代表一个 `stay_id`。
- 仅保留每位患者在 MIMIC-IV 中最早的 ICU stay。
- 若同一次住院存在多个 ICU stay，仅保留最早 ICU stay。
- `hadm_id` 是该 ICU stay 所属的本次住院；所有 pre-T0 AHF 证据必须来自同一个 `hadm_id`。

### 2.2 T0 与预测时间轴

| 项目 | 定义 |
|---|---|
| `T0` | ICU `intime` |
| `T12` | `T0 + 12 h` |
| AHF 主资格窗口 | `[hospital admittime, T0)` |
| AHF 严格敏感性窗口 | `[T0 - 24 h, T0)` |
| 预测变量窗口 | `[T0, T12)` |
| 结局窗口 | `[T12, T0 + 60 h)` |

所有预测变量必须在 `T12` 前可获得。所有结局变量只能在 `T12` 后生成，不能反向参与队列入组。

## 3. AHF 的可操作定义

### 3.1 重要术语边界

MIMIC-IV 的最终 `diagnoses_icd` 通常没有可用于实时建模的诊断确认时间。因此不能把“最终 ICD 出现”直接写成“患者在 T0 前已被临床诊断为 AHF”。

本研究正式使用更准确的表述：

> **Pre-T0 AHF phenotype established during the index hospitalization**：本次住院最终存在急性/急性加重 HF 的回顾性诊断锚点，并且在 ICU 入科前已有带时间戳的客观 AHF 临床证据。

这是一个可跨 MIMIC 与本院复刻的操作性表型，不等同于实时电子病历中“医生已经下达 AHF 诊断”的原始诊断时间。

### 3.2 必须同时满足

1. 本次住院存在 acute 或 acute-on-chronic HF ICD；
2. HF 诊断最小序位 `<=5`；
3. 在本次住院 `admittime` 至 ICU `intime` 之间至少有一项带时间戳证据：
   - 实际执行的 IV loop diuretic eMAR；
   - NT-proBNP `>=300`，且检验时间早于 ICU 入科。

### 3.3 `T_qualify`

`T_qualify` 定义为以下可用时间证据的最早时间：

```text
T_qualify =
min(first_actual_IV_loop_eMAR_time,
    first_NT_proBNP_ge300_time)
```

只允许：

```text
hospital admittime <= T_qualify < ICU intime
```

药物医嘱开始时间不作为主定义的 AHF 确认时间，因为医嘱不等于实际给药。处方开始时间只能做敏感性分析。

### 3.4 排除的 AHF 证据类型

- 只有最终 HF ICD、没有任何时间戳 AHF 证据：`ICD-only`，不进入主模型；
- 首次 IV loop/NT-proBNP 证据出现在 `T0` 后：不进入 pre-T0 AHF 主模型；
- 证据早于本次 `admittime`：不作为本次住院的 AHF 证据；
- 低序位或仅慢性 HF ICD：不满足 strict AHF phenotype。

## 4. 为什么这样可以避免主要泄露

### 4.1 AHF 定义不会使用未来结局

AHF 入组证据只使用 `T0` 前信息和回顾性诊断锚点；不会使用 `T12-T60` 的药物、生命体征或死亡信息。

### 4.2 最终 ICD 的定位

最终 ICD 和诊断序位可用于：

- 回顾性确认研究对象确实属于急性/急性加重 HF；
- 进行队列质量审计。

最终 ICD 和诊断序位不可用于：

- 预测变量；
- 声称实时可用的 T0/T12 诊断信息；
- 替代 pre-T0 时间戳证据。

### 4.3 预测目标不会变成“预测 AHF 是否发生”

纳入者在 T0 前已具备 AHF 的操作性证据；`0-12 h` 变量用于预测后续 `12-60 h` 的 hemodynamic deterioration，而不是预测患者是否会被诊断为 AHF。

## 5. Early sepsis 的暂定位置

AHF 的时间要求与 early sepsis 不必完全相同：

- AHF：主定义要求 `T0` 前已经成立；
- early sepsis：当前先定义为在 `T12` 前达到可追溯的 early sepsis 操作标准；
- 预设敏感性分析：要求 infection suspicion、antibiotic/culture 和 SOFA 证据均在 `T0` 前。

这样既保持 AHF 主体清晰，又避免把“感染在 ICU 前尚未被完整确认”与“AHF 在 ICU 后才出现”混为一谈。

若最终课题标题坚持“入 ICU 时已合并早期脓毒症”，则必须使用更严格的 pre-T0 sepsis 队列，并将其作为独立可行性分析，不能继续沿用 `T12` 确认结果直接命名。

## 6. 主要纳入与排除标准

### 纳入

1. 年龄 `>=18` 岁；
2. 每位患者最早 ICU stay；
3. 本次住院存在 strict AHF retrospective anchor；
4. `T_qualify` 位于 `[admittime, T0)`；
5. ICU stay 到达 `T12`；
6. `0-12 h` 无 pre12 overt shock proxy；
7. 能建立 `T12-T60` 结局观察记录。

### 排除

1. 非成人；
2. 非每位患者最早 ICU stay；
3. 只有 ICD-only AHF 证据；
4. AHF 首次时间证据位于 T0 后；
5. AHF 证据早于本次住院开始；
6. 未到达 `T12`；
7. `0-12 h` 已出现预设 overt shock proxy；
8. 关键时间字段缺失。

## 7. 需要报告的预设队列层次

在重跑前，不直接把单个队列称为“正确答案”，而是固定报告以下四层：

| 队列 | 用途 |
|---|---|
| `AHF_by_T12` | 历史主线/可比性分析；允许 T0 后到 T12 才出现 AHF 时间证据 |
| `AHF_pre_T0_admission_to_icu` | 推荐主分析；最符合当前研究问题 |
| `AHF_pre_T0_last24h` | 严格时间敏感性分析 |
| `AHF_ICD_only` | 标签质量审计，不进入主模型 |

主模型只有在 `AHF_pre_T0_admission_to_icu` 的样本量和事件数通过可行性评估后才正式训练。

## 8. 当前 `T_qualify` 审计对方案的影响

当前 early-sepsis 主队列 `n=2,424` 中，执行/检验时间证据分层为：

| 分层 | n | 事件 | 事件率 |
|---|---:|---:|---:|
| pre-T0 | 516 | 52 | 10.08% |
| T0-6 h | 358 | 55 | 15.36% |
| 6-12 h | 93 | 19 | 20.43% |
| ICD-only | 1,457 | 208 | 14.28% |

因此，旧 2,424 例队列不能继续表述为“所有患者在入 ICU 前已诊断 AHF”。

进一步的 `093` 审计在 6,301 例 landmark risk set 中显示：

| 定义 | stays | 事件 | 事件率 | early-sepsis stays |
|---|---:|---:|---:|---:|
| pre-T0：本次住院入院至 ICU | 562 | 57 | 10.14% | 165 |
| pre-T0：ICU 前 24 h | 280 | 29 | 10.36% | 95 |

因此，推荐将 `pre-T0 admission-to-ICU` 作为候选主分析队列，将 ICU 前 24 h 作为严格敏感性分析；AHF+early-sepsis 交集暂不作为高维机器学习主模型。

## 9. 当前阶段的决定

本轮只冻结定义和审计，不立即重跑模型：

1. 先运行 `sql_v3/audits/093_pre_t0_ahf_definition_audit.sql`；
2. 检查 `[admittime, T0)` 主定义和 `[T0-24h,T0)` 敏感性定义的样本量、事件数、complete60 比例；
3. 若主定义事件数足够，再建立新的 cohort/modeling dataset 版本；
4. 旧 v3 `2,424/334` 结果保留为历史比较，不作为最终无泄露主结果。

## 10. 论文中建议使用的表述

> We included adults in their first ICU stay who had a retrospective acute or acute-on-chronic heart failure diagnosis during the index hospitalization and objective, timestamped heart-failure-related evidence recorded between hospital admission and ICU admission. We used ICU admission as T0, summarized predictors during the first 12 hours, and predicted treatment-escalation-based hemodynamic deterioration during the subsequent 48 hours. Final discharge diagnoses were used for retrospective phenotype anchoring only and were excluded from model predictors.
