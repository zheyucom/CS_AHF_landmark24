# Study Definition v2.1: landmark 12 h 主研究协议

更新日期：2026-07-29

## 1. 研究主题

### 中文题目

**入 ICU 时已存在急性心力衰竭临床综合征并在最初 12 h 内满足早期脓毒症证据、且尚未发生显性心源性休克的成人患者，未来 48 h 血流动力学恶化风险预测：基于 MIMIC-IV 的模型开发及本院外部验证**

### 推荐英文题目

**Early prediction of hemodynamic deterioration in critically ill adults with acute heart failure present at or shortly after ICU admission and early sepsis: model development using MIMIC-IV and external validation in a local hospital cohort**

### 一句话研究问题

在成人首次 ICU stay 中，针对 ICU 入科时或入科后最初 12 h 已有严格 AHF 证据、在 12 h landmark 前满足 early sepsis12、且 0-12 h 尚无 overt cardiogenic shock proxy 的患者，能否使用 ICU 0-12 h 可获得的结构化信息，预测 ICU 12-60 h 内新发 treatment-escalation-based hemodynamic deterioration？

## 2. 研究对象不是一句宽泛的“AHF + sepsis”

本研究的目标人群由四个同时成立的条件构成：

1. **成人首次 ICU stay**：研究单位为 stay，每位患者只保留首次 ICU stay。
2. **严格 AHF 表型**：不是仅凭既往 HF 病史或任意 HF ICD；要求 HF ICD 在本次住院诊断中较靠前，并有急性或早期治疗/生物标志物证据。
3. **landmark 前 early sepsis12**：不是“住院期间任何时候得过 sepsis”，而是感染怀疑和器官功能障碍证据在 ICU 入科后 12 h 决策点前已经可获得。
4. **尚未发生显性 CS**：0-12 h 已有 overt cardiogenic shock proxy 者被排除，模型预测的是 landmark 后新发恶化，而不是既有休克患者的预后。

因此，本研究是一个**预先限定的严格 AHF 人群中的 early-sepsis 富集预测队列**。从疾病层级上，它属于 AHF 人群的一个临床高风险子人群；从统计设计上，early sepsis12 是主队列纳入条件，不是建模后才做的普通亚组。

## 3. AHF 是否在入 ICU 前已经存在

当前可支持的准确说法是：

> AHF 在 ICU 入科时或入科后最初 12 h 内已存在（present at or shortly after ICU admission），而不是保证所有患者在 ICU `intime` 前已经完成 AHF 诊断。

当前 AHF 支持证据窗口包含 ICU 前后信息；部分证据来自住院 ICD，部分早期证据允许在 ICU 0-12 h 出现。因此不能把主队列统称为“入 ICU 前已经是 AHF”。

预设补充分析：建立 **pre-ICU-confirmed AHF sensitivity cohort**，只允许 ICU `intime` 前已有急性/急性加重 HF 诊断、IV 袢利尿剂或合格 NT-proBNP 证据。该队列用于检验“真正入 ICU 前已成立 AHF”限制对样本量、事件率和模型性能的影响，不替代当前主队列，除非本院数据也能稳定复刻。

## 4. Index、landmark 与时间窗

| 项目 | 正式定义 |
|---|---|
| Index time | ICU `intime` |
| Landmark | ICU `intime + 12 h` |
| Predictor window | ICU 0-12 h；任何 12 h 后信息不得进入模型 |
| Prediction window | ICU 12-60 h，即 landmark 后未来 48 h |
| 分析单位 | 首次 ICU stay；每位患者一行 |
| 数据源 | MIMIC-IV 开发；本院独立队列外部验证 |

## 5. 纳入标准

患者必须同时满足：

1. 年龄 >=18 岁；
2. 患者在数据库中的首次 ICU stay；
3. 本次住院存在 HF ICD candidate；
4. HF 相关 ICD 最小序位 `seq_num <=5`；
5. 在预设早期窗口内至少有一项 AHF 支持证据：
   - acute 或 acute-on-chronic HF ICD；或
   - 早期 IV loop diuretic prescription；或
   - 血液 NT-proBNP `itemid=50963` 且 >=300；
6. ICU stay 达到 12 h landmark；
7. `early_sepsis12_main_flag=1`，且构成证据在 landmark 前可追溯；
8. 0-12 h 无 overt cardiogenic shock proxy；
9. 可建立 ICU 12-60 h 结局观察窗和必要时间字段。

当前 cohort flow：65,366 成人首次 ICU -> 14,877 HF ICD candidate -> 7,562 strict AHF12 -> 7,366 到达 landmark -> 排除 1,065 例 pre12 overt CS -> 6,301 AHF risk set -> 2,424 例 early sepsis12 主队列。

## 6. 排除标准

1. 年龄 <18 岁；
2. 非首次 ICU stay；
3. 只有慢性 HF 病史/低序位 HF ICD，不能满足 strict AHF 规则；
4. 未达到 ICU 12 h landmark；
5. ICU 0-12 h 已出现 overt cardiogenic shock proxy；
6. 不满足 landmark 前 early sepsis12 主定义，或感染/SOFA 时间无法确认在 landmark 前；
7. 关键 index/landmark/outcome 时间字段缺失；
8. 无法建立合法的 12-60 h 风险观察；
9. 用于建模的变量只能由 landmark 后信息得到时，该变量排除而不是机械排除患者。

## 7. early sepsis12 的临床含义

这里的 sepsis 患者不是“额外混入的一部分无关患者”。主队列 2,424 例全部满足 early sepsis12；其余 3,877 例 strict AHF risk-set 患者因不满足 early sepsis12 而不进入主模型，可作为预设对照/敏感性队列。

`early_sepsis12_main_flag` 的概念要求是：landmark 前存在可追溯的 suspected infection signal，并有相应 SOFA/器官功能障碍证据。最终论文必须在方法部分展开写清：

- suspected infection 的抗菌药与培养配对规则；
- suspicion time 的计算；
- baseline SOFA 与 SOFA 增量规则；
- 哪些 SOFA 分组件落在 ICU 前、0-6 h、6-12 h；
- 所有证据是否确实早于 landmark。

当前仓库只保留了派生结果和说明，缺少生成 `early_sepsis12_main_flag` 的完整版本化 SQL。**在冻结协议前必须补回该 SQL 和数据字典；否则 early sepsis12 尚不具备充分可复现性。**

## 8. 主结局

主结局为 ICU 12-60 h 内首次发生的 **treatment-escalation-based hemodynamic deterioration**，即以下任一：

1. 新启用 vasoactive/inotrope support；
2. 同时使用的 vasoactive/inotrope 药物种类增加；
3. norepinephrine-equivalent dose 相对 0-12 h 基线最大值增加 >=0.05 ug/kg/min；
4. 12-60 h 内死亡。

当前主结局为 334/2,424（13.78%）。事件首次出现：12-36 h 248 例，12-48 h 301 例，12-60 h 334 例。旧材料中的 133/2,424（5.49%）指较严格的 mixed-shock/CS-like proxy，不是当前 broad HD 主结局。

## 9. 次要与敏感性结局

| 结局 | 定位 | 当前事件数 |
|---|---|---:|
| NEE delta >=0.10 | 更严格治疗升级 | 315 |
| 排除 NEE-only | 检验 NEE 单成分影响 | 282 |
| mixed shock / CS-like proxy | 更严格、病理生理特异的次要结局 | 133 |
| lactate-confirmed HD | 低灌注确认 | 105 |
| 12-60 h death | 硬结局 | 57 |

## 10. 研究定位与亚组

- 主模型目标域：上述 2,424 例严格 AHF + landmark 前 early sepsis12 风险人群。
- AHF without early sepsis12（n=3,877）不是主队列中的“阴性组”，而是主目标域之外的预设比较/可迁移性分析人群。
- 推荐报告 early sepsis12 与 non-early-sepsis12 的事件率差异：5.49% vs 2.58%（严格 mixed-shock/CS-like proxy）；broad HD 也应使用同一版本结局重新输出分层事件率。
- 不应把本研究称为 septic cardiomyopathy 模型，因为没有要求新发超声心肌功能异常。
- 不应把主结局称为纯 cardiogenic shock，因为 broad HD 包含治疗行为和死亡，病因可能是心源性、脓毒性或 mixed physiology。

## 11. 当前最优论文表述

本研究聚焦于一个临床上可识别但病理生理高度复杂的目标人群：入 ICU 时或最初 12 h 已有严格 AHF 表型，同时在决策点前满足早期脓毒症证据、但尚未进入显性心源性休克的成人患者。模型目的不是诊断 sepsis、AHF 或 septic cardiomyopathy，而是预测 landmark 后未来 48 h 是否将出现需要血管活性/强心支持升级或死亡的血流动力学恶化，从而触发强化监测、灌注复评和床旁心脏/容量状态评估。

## 12. 冻结前必须完成的协议改进

1. 恢复并版本化 strict AHF12、early sepsis12、pre12 overt CS 和主结局的全套生成 SQL。
2. 明确 AHF 证据窗口的绝对起止时间，并单独输出 ICU 前已经成立 AHF 的比例。
3. 重算 broad HD 在 AHF overall、early sepsis12、non-early-sepsis12 三组中的事件率和交互/异质性。
4. 审计 simultaneous agent count、30/60 min persistence、phenylephrine/procedure use 和 NEE baseline。
5. 对主结局随机抽取 TP/FP/FN/TN 病例做盲法标签复核。
6. 冻结 15-30 个本院可映射 raw predictors，再开始本院小样本可行性提取。

