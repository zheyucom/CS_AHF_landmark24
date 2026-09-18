# 任务报告：DHF 入组证据、心超与 CXR/CT 决策

日期：2026-09-03  
状态：本轮方案澄清已完成；用户已确认院内严格主队列为 `echo-supported DHF ICU cohort`。MIMIC/院内可用心超结果源和严格队列计数仍待补齐。

## 1. 本轮结论

主研究对象再次明确为：

> 成人 ICU 患者，在首次 index ICU stay 中到达 `T12`，并在 `[T0-24 h,T12)` 内具有可时间追溯的 DHF operational phenotype；不要求患者在 `T0` 入 ICU 时已经完成 DHF 诊断。

`T0` 是 ICU 入科时间，`T12` 是入科后 12 h。患者可以在 ICU 早期完成心超、出现影像证据或启动/强化 DHF 相关治疗，只要这些证据在 `T12` 前可追溯。T12 前死亡、无法到达 landmark、时间边界不可靠和 T12 前已存在 overt shock proxy 的患者按既有合同处理。

## 2. 心超的正确位置

心超是最重要的客观心脏证据。用户已确认院内外部验证主队列将心超作为硬门槛，但硬门槛必须具体为“实际完成 + 结果可用 + 结果支持异常”，而不能简化为 procedure flag。全 ICU 候选宇宙仍需保留，以报告检查选择性，不能声称所有 ICU 患者必然完成心超。

1. MIMIC 的心超检查不是对所有患者随机完成，而是由临床指征决定；强制有心超会选择出被医生认为需要心超的人群，产生检查指征选择偏倚。
2. 当前结构化审计仅发现 `462/5,549` 例有 TTE/TEE 操作记录，结构化 LVEF 可用为 `0`。因此现在不能把“做过心超”写成“心超异常”，也不能把未检查者判为阴性。
3. 心超可以证明心脏结构/功能异常，但不能单独证明当前症状就是 DHF；仍需结合时间、临床表现、肺部充血或治疗强化。

因此当前采用以下层级：

- 心超结果真实可用时：作为最高优先级客观心脏证据；
- 心超未做或结果缺失时：记为 `unknown`，不进入严格院内主队列，不能判阴性；
- `echo-result-supported DHF`：作为院内严格外部验证主队列；
- “echo procedure available”：只作为可用性/缺失模式字段。

院内研究问题已明确为“在心超结果支持异常的 DHF ICU 患者中预测后续风险”；因此必须报告全 ICU 候选宇宙到严格队列的选择性，不能将严格队列泛化为所有 DHF ICU 患者。

## 3. CXR 与胸部 CT 的正确位置

胸片与胸部 CT 都可提供肺水肿、间质性/肺泡性水肿和肺血管充血证据；CT 还更适合发现 PE、肺炎/ARDS 等替代或并存诊断。但 CT 通常在诊断不确定、疑似 PE 或需要进一步定位时选择性完成，不能要求所有疑似 DHF 患者都同时完成 CXR 和 CT。

冻结为：

- 主影像规则：时间合规的 `CXR OR chest CT` 明确充血证据；
- 分层报告：`CXR-only`、`CT-supported`、`CXR-and-CT`；
- `CXR AND CT`：严格敏感性分析，不能作为主纳入门槛；
- 单独胸腔积液、心影增大、肺部模糊或“可能”不能自动等同于 DHF；
- CT 未检查不能当作 CT 阴性。

## 4. ACS、CKD/AKI、PE 和肺炎/ARDS 怎么处理

这些疾病不能机械地全部排除，因为 ACS、感染、肾功能恶化和心律失常都可能是 DHF 的诱因或并存病。正确做法是要求 HF anchor 加独立的失代偿证据，而不是只靠 BNP。

| 情形 | 主分析处理 | 预设敏感性/审计 |
|---|---|---|
| CKD/AKI/ESRD | 保留；在 Table 1/模型中描述或作为协变量；BNP-only 不足以入组 | 排除 BNP-only；可另报严重肾功能异常层 |
| ACS/AMI | 有 HF 客观/临床证据时保留，视作诱因/共病 | 排除“孤立 ACS、无 HF 失代偿证据”层 |
| PE | 有独立 HF 证据时可保留并标记；PE 可能造成右心负荷和 BNP 升高 | PE-code/text-supported exclusion，作为高特异性 DHF 敏感性 |
| 肺炎/ARDS/COPD | 不因共存自动排除；肺部影像必须区分替代解释 | 排除“非 HF 主导、无心脏证据”层 |

因此，BNP/NT-proBNP、IV loop 或最终 HF ICD 均不能单独确诊 DHF。尤其 BNP 受 CKD、年龄、房颤、PE、肺高压和脓毒症影响；本研究将 NT-proBNP 定位为支持域，而不是独立 rule-in。

## 5. DHF 与本研究结局的时间分离

ESC 2026 的 DHF 概念本身包含“需要紧急医疗关注并启动或强化治疗”。这不等于本研究把入组和结局混成同一指标：

- 入组证据：仅用 `[T0-24 h,T12)` 内已经发生且可追溯的 HF 失代偿证据和早期管理/治疗证据；
- 预测器：只用 `[T0,T12)` 可获得信息；
- 结局：仅用 `T12` 之后相对 pre-T12 基线的新循环支持升级、持续 NEE 升高或 ICU 内死亡。

所以治疗行为在时间上分离，但仍需在论文中承认其受临床决策影响。主结局继续命名为 `treatment-escalation-based ICU hemodynamic deterioration`，不能改称 incident cardiogenic shock。

## 6. 新增执行文件

- `project_control/bigquery/109_query_landmark12_dhf_radiology.sql`：抽取 `[T0-24 h,T12)` 内放射科报告，保留 `charttime`、`storetime` 和文本规则字段。
- `project_control/bigquery/110_query_landmark12_dhf_radiology_patient_summary.sql`：生成一人一行的主窗口报告覆盖和筛查汇总。

两条查询仍需在用户自己的 BigQuery Terminal/控制台执行；当前 Codex 会话不能代替用户的 Google API 网络和 BigQuery job 权限。106/107 的严格 pre-T0 结果不能替代 109/110 的主窗口结果。

## 7. 依据与边界

- 2026 ESC HF guideline：DHF 取代 acute HF，强调临床综合征、病程和治疗启动/强化；正式引用前应以指南全文核对原文位置。
- 2021 ESC HF guideline：支持症状/体征、客观心脏结构/功能和生物标志物的综合诊断框架。
- 2023 HFA worsening HF consensus：支持将失代偿/恶化与治疗强化及后续结局分开描述。
- CheXpert/NegEx：支持放射科报告的不确定性和否定语境必须经过规则与人工标注验证。
- TRIPOD+AI/PROBAST+AI：支持预先冻结表型、变量、时间边界和缺失处理，避免结局驱动的后验筛选。

这些文献支持“多域整合、时间截断、未知不等于阴性”的原则，但没有任何文献可以直接替本研究规定 MIMIC 的 ICD、BNP、eMAR 组合。因此最终论文必须称为 `operational phenotype`，并报告人工验证、缺失模式和敏感性结果。

## 8. 当前仍需完成

1. 用户运行 109/110，导出主窗口 radiology 原始表和 patient summary。
2. 若可申请到独立 MIMIC echo 数据源，完成心超报告/结构化结果时间审计；当前 MIMIC-IV-Note 不包含完整心超结果。
3. 由用户已确认的严格 `echo-supported DHF ICU cohort` 口径执行，不再等待 `multidomain` 作为主队列的选择。
4. 按确认后的事件数重新冻结低维特征 manifest，再运行最终 Fine-Gray 和 person-period 模型。
