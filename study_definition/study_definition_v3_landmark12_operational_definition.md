# Study Definition v3.0: 12 h Landmark Cohort and Operational Definitions

更新日期：2026-08-25

## 1. 本文件解决的问题

本研究不是 ICU 入科瞬间（`t=0`）的预测模型，而是一个 **12 h landmark prediction model**：

> 在 ICU 入科后最初 12 h 内，已满足预设 AHF 和 sepsis 操作性标准、且尚未出现显性休克代理指标的成人患者，利用 `0-12 h` 可获得信息，预测 `12-60 h` 内血流动力学恶化。

因此，论文中不能写成“所有患者在 ICU 入科时已经确诊 AHF 合并 sepsis”。数据库能可靠界定的是“满足操作性标准的最晚时间”，不是疾病真实起病时间。

## 2. 时间轴与分析单位

| 名称 | 正式定义 |
|---|---|
| 当前 v3 分析单位 | 每个 `subject_id` 在 MIMIC 中的首次 ICU stay (`stay_id`)；这是当前 SQL 的实际实现 |
| 建议最终分析单位 | 每次 index hospital admission 的首次 ICU stay；重复住院时预先指定只保留首次符合条件的住院，或以 patient-level split 处理相关性 |
| `T0` | ICU `intime` |
| `T12` | `T0 + 12 h`，landmark / 入组判定时点 |
| 特征窗口 | `[T0, T12)` |
| 预测窗口 | `[T12, T0 + 60 h)`，即 landmark 后 48 h |
| 允许的入组证据窗口 | `[T0 - 24 h, T12)`；仅用于 AHF 和 sepsis 的早期识别，不进入结局 |

所有主队列患者都必须存活且仍在 ICU 至 `T12`。`T12` 后才开始计算结局；任何 `T12` 后信息不得参与入组判定或特征生成。

当前按 `subject_id` 首次 ICU 的取法可以保留为 v3 基线复现，但它不等同于“每次住院的首次 ICU”。在本院外部验证和最终论文前，必须选定上述其中一个单位，并在两库用同一规则执行。

## 3. 当前 v3 已执行的口径

v3 SQL 已恢复在 [`sql_v3/executable`](/Users/zheyu/Desktop/CS_AHF_landmark24/sql_v3/executable)，并已成功顺序运行。请以此目录和 `study_ahf_v3` schema 为唯一可复现版本，不再使用根目录历史 `sql/` 重建队列。

| 环节 | SQL | 当前结果 |
|---|---|---:|
| 成人首次 ICU stay | `010_adult_first_icu.sql` | 65,366 |
| HF ICD candidate | `020_hf_icd_candidate.sql` | 14,877 |
| 当前 strict AHF12 | `061A/061B` | 7,562 |
| 到达 `T12` 且无 pre12 overt-CS proxy | `061C/061D` | 6,301 |
| early sepsis12 主队列 | `062A/062B` | 2,424 |
| 12-60 h primary HD outcome | `064` | 334/2,424 (13.78%) |

`run_v3.sh` 的 24 个 SQL 日志均已生成，未见 SQL `ERROR`；数据库中 `study_ahf_v3.outcome_064_primary_hd_deterioration_v1` 当前为 2,424 行、334 个主结局。

这说明 **v3 SQL 已恢复且可重复运行**，不表示当前队列定义已经冻结。第 4-5 节的时间可用性修订完成后，应另建 `v3.1` schema/输出目录重跑，不覆盖本版本。

## 4. AHF 定义：当前实际口径与冻结建议

### 4.1 当前 v3 实际口径

当前 `061B` 的 strict AHF12 为：

1. 本次住院存在 HF ICD（ICD-9 `428.*`、ICD-10 `I50.*` 或预设 hypertensive-HF code），且 HF 最小诊断序位 `<=5`；
2. 同时满足以下任一：
   - 最终 ICD 中有 acute / acute-on-chronic HF code；
   - `[T0-24 h, T12)` 内 IV loop diuretic prescription；
   - 同一窗口 NT-proBNP `>=300 pg/mL`。

该定义适合回顾性研究中的 **AHF 表型确认**，但最终 ICD 与诊断序位通常在出院后才完成，不能被解释为 `T0` 或 `T12` 的实时诊断信息。

在当前主队列中，981/2,424 (40.47%) 没有上述早期利尿剂或 NT-proBNP 证据，仅依赖最终 acute-HF ICD 支持。故当前 v3 队列不能严谨称为“所有患者在 landmark 前均有时间戳 AHF 临床证据”。

### 4.2 建议冻结的跨库主定义：AHF confirmed by T12

主研究仍使用 **AHF 在 `T12` 前可识别**，而非强行限定在 `T0` 已识别。为保证 MIMIC 与本院可复刻，按两个层面记录：

| 标志 | 操作定义 | 用途 |
|---|---|---|
| `ahf_retro_confirmed_flag` | 本次住院 HF diagnosis code / 本院等价诊断最终确认 | 回顾性队列表型确认；**不得作预测器** |
| `ahf_time_confirmed_by_t12_flag` | `[T0-24 h, T12)` 至少一项带时间戳的 AHF 支持证据 | 主队列的时间可用性门槛 |
| `ahf_pre_icu_confirmed_flag` | 上述时间戳证据发生在 `T0` 前 | 预设敏感性分析，不是主入组门槛 |

建议 `ahf_time_confirmed_by_t12_flag=1` 的跨库最低证据为以下至少一项：

1. 实际执行或开始的 IV loop diuretic（furosemide、bumetanide、torsemide、ethacrynic acid），优先 eMAR/输液执行记录而非医嘱；
2. NT-proBNP `>=300 pg/mL`；若本院同时有 BNP，保留原始数值、项目名与单位，不能与 NT-proBNP 直接合并；
3. 仅在两库都能获得时间戳的前提下，`T12` 前记录的 acute-HF admission diagnosis / problem-list diagnosis。

最终 HF ICD 可保留为回顾性确认条件，但 **不能单独替代第 1-3 项时间戳证据**。MIMIC 当前仅稳定支持第 1-2 项；本院可额外抽取第 3 项作一致性审计和敏感性分析。

建议冻结后的主队列 AHF 条件为：`ahf_retro_confirmed_flag=1 AND ahf_time_confirmed_by_t12_flag=1`。前者用于回顾性表型锚定，后者保证模型在 `T12` 的目标人群已经可临床识别。两者及其组成项均不得作为预测器。当前队列若仅保留已有早期 IV 袢利尿剂或 NT-proBNP 支持者，样本为 1,443 例、事件 211 例（14.62%）；因此应在重跑后正式评估事件数与模型稳定性。

`NT-proBNP >=300` 是生物标志物支持证据，不是单独的临床确诊金标准。若后续样本量允许，应增加“早期 IV 袢利尿剂”与“NT-proBNP”不同组合的 AHF 表型敏感性分析。

## 5. Early sepsis 定义：by T12，而非默认 T0 已存在

### 5.1 当前 v3 的 MIMIC 等价实现

`062A_create_early_sepsis12_flags.sql` 使用 `mimiciv_derived.sepsis3`，并要求：

1. `suspected_infection_time` 位于 `[T0-24 h, T12)`；
2. `sofa_time` 位于同一窗口；
3. MIMIC `sepsis3` 表已保证 `SOFA >=2`，并将感染怀疑与 SOFA 时间在预设窗口内关联。

MIMIC 官方派生逻辑的 suspected infection 为：

- 培养在前：抗菌药在培养后 72 h 内开始，suspicion time = 培养采集时间；
- 抗菌药在前：培养在抗菌药后 24 h 内采集，suspicion time = 抗菌药开始时间；
- SOFA `>=2` 的时间须位于 suspicion time 前 48 h 至后 24 h 的关联窗口内。

MIMIC SOFA 使用 ICU 小时级数据，并将未知的分组件视为正常；其 Sepsis-3 实现隐含假定基线 SOFA 为 0。因此，论文应称其为 **MIMIC-compatible Sepsis-3 operational phenotype**，不能声称已获得每名患者感染前真实基线 SOFA 增量。

### 5.2 必须修复的时间可用性问题

当前 SQL 仅检查 `suspected_infection_time` 和 `sofa_time` 是否早于 `T12`，未同时检查形成感染怀疑所需的 `antibiotic_time` 与 `culture_time`。实测当前 2,424 例中有 625 例（25.78%）至少一项感染配对记录发生在 `T12` 后，其中 593 例为抗菌药时间在 `T12` 后。这部分病例使用了 landmark 后的治疗信息来回溯标记早期 sepsis，不符合可部署预测模型的时间可用性要求。

因此，冻结后的 `early_sepsis12_main_flag` 必须同时满足：

```text
sepsis3 = true
AND suspected_infection_time in [T0 - 24 h, T12)
AND sofa_time in [T0 - 24 h, T12) with SOFA >= 2
AND antibiotic_time < T12
AND culture_time < T12
```

这保留了“感染证据可以在 ICU 前 24 h 已开始”的临床现实，同时保证截至 `T12` 已能观察到形成疑似感染判断的培养和抗菌药配对。MIMIC 中使用派生表的 `antibiotic_time`；本院优先使用抗菌药实际执行时间，若仅能获得医嘱起始时间，必须单独标志并做敏感性分析。

### 5.3 时间解释

当前 2,424 例中：

- 1,485 (61.26%) 的 suspected infection signal 发生在 ICU 前；
- 939 (38.74%) 在 ICU `0-12 h` 内首次出现 suspected infection signal；
- 仅 20 例的 suspected infection 和 SOFA 时间均在 ICU 前；多数为“感染怀疑在 ICU 前、器官功能障碍证据在 ICU 后最初 12 h 内确认”。

所以主队列的准确表述是“**在 `T12` 前满足 early sepsis 操作性标准**”，不是“ICU `T0` 时已全部存在 sepsis”。

### 5.4 本院复刻规则

本院必须导出抗菌药实际执行/起始时间、培养**采集**时间（不用结果回报时间）及 SOFA 六分组件原始带时间记录。按与 MIMIC 相同的配对窗口生成：

```text
sepsis_qualification_time = max(antibiotic_time, culture_time, first_sofa_ge2_time)
early_sepsis12_flag = 1 when all required source times are available by T12,
  suspected_infection_time and first_sofa_ge2_time are in [T0 - 24 h, T12),
  and the paired antibiotic/culture times are earlier than T12
```

同时保留 `antibiotic_time`、`culture_time`、`suspected_infection_time`、各 SOFA 分组件、`first_sofa_ge2_time` 和 `sepsis_qualification_time`，以便审计而不是只交付一个 sepsis 标签。

## 6. 既有休克排除与结局

| 项目 | 现行操作定义 | 正确表述 |
|---|---|---|
| pre12 exclusion | `[T0,T12)` 内 vasoactive/inotrope exposure 且 lactate max `>=2 mmol/L` | `overt shock proxy`，不是临床确诊 CS |
| 主结局 | `[T12,T60)` 新启用/增加 vasoactive-inotrope，或 NEE 相对 pre12 max 增加 `>=0.05 ug/kg/min`，或死亡 | treatment-escalation-based hemodynamic deterioration |

该研究不应把主结局称为纯 cardiogenic shock：其中可包含心源性、脓毒性或 mixed physiology 的治疗升级。严格 mixed-shock/CS-like proxy 仅作次要结局和敏感性分析。

## 7. 预测变量可用性规则

任何变量都要先回答“临床团队在 `T12` 是否已经能看到它”：

| 可用于预测器 | 不可用于预测器 |
|---|---|
| `T12` 前的生命体征、检验、血气、尿量、实际给药/输注、呼吸支持、GCS、心超检查/报告已完成时间 | `T12` 后记录、结局组件、出院时间、死亡时间、最终诊断编码、最终 ICD 序位 |

当前 v3 Python 未自动排除 `hf_icd_primary_seq`、`hf_icd_seq_eq1_flag`、`hf_icd_seq_2_5_flag`、`acute_hf_icd_flag`。其中 `hf_icd_primary_seq` 在当前稳定选择中频率为 1.00、排位第 1。它们来自最终诊断编码，属于临床可用性泄露；`mimiciv_derived.charlson` 如使用本次住院最终 ICD 也须改为仅基于 ICU 前既往史/入院时可用诊断，或暂不作为外部验证模型预测器。

因此，当前 v3 模型性能只能作为 **回顾性内部开发结果**，不能作为已可部署或已可外部验证的最终性能。重新训练前必须排除这类最终编码字段，并单独报告性能变化。

## 8. 冻结前的最小必做工作

1. 将 `061A/061B` 增加 `ahf_retro_confirmed_flag`、`ahf_time_confirmed_by_t12_flag`、`ahf_pre_icu_confirmed_flag`，并重新输出队列 flow；
2. 将 “ICD-only AHF” 与 “time-confirmed AHF” 分层样本数、事件率和模型性能报告为预设敏感性分析；
3. 将最终 HF ICD、诊断序位和本次住院 ICD-derived Charlson 从预测器中排除，建立新的独立输出目录后重跑模型；
4. 修订 `062A`：把 `antibiotic_time < T12` 和 `culture_time < T12` 纳入 early sepsis 主定义，并输出 infection、SOFA 与 qualification 三个时间戳；本院按同一规则提取原始抗菌药、培养和 SOFA 分组件；
5. 决定最终 ICU 分析单位（当前 `subject_id` 首次 ICU，或 index admission 首次 ICU），并同步修改 MIMIC 和本院的选择规则；
6. 对 ICU `T60` 前出 ICU 的患者明确删失处理，并报告 complete-60 h sensitivity analysis。

在这些步骤完成前，导师沟通和论文中应使用以下准确表述：

> 本研究为 12 h landmark 队列：成人 ICU 患者在 `T12` 时已具备可时间追溯的 AHF 证据和 MIMIC-compatible Sepsis-3 证据、且尚无 overt shock proxy；模型使用 `0-12 h` 内可获得的结构化信息预测随后 48 h 的治疗升级相关血流动力学恶化。患者不要求在 ICU 入科瞬间已满足两种诊断标准。
