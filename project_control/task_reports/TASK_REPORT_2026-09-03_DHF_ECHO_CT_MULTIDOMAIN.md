# 任务报告：DHF 心超、CXR/CT 与患者级多域审计

日期：2026-09-03  
状态：历史审计报告；其中“心超不强制、multidomain 为主队列”的建议已被用户后续决定取代。当前口径见 `TASK_REPORT_2026-09-03_DHF_ECHO_REQUIRED_INTERNAL_COHORT.md`。

## 1. 本轮完成

1. 完成结构化心超审计：5,549 个有效候选中 462 例有 TTE/TEE 检查记录，但可用结构化 LVEF 为 0。
2. 完成 5,549 stay 患者级多域审计，stay_id 唯一；结局守恒为 452 event + 2,934 compete + 2,163 censor。
3. 完成严格 ICU 前可见影像分层：definite CXR 425 例、definite chest CT 55 例、CXR OR CT 449 例、CXR AND CT 31 例。
4. 更新研究总览、项目 README、DHF 表型协议 v1.2、Study Definition v5.2 和周二周报补充版。

核心输出：

- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260903/dhf_multidomain_patient_level_audit_20260903.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260903/dhf_multidomain_patient_level_audit_20260903_outcome_epv.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260903/DHF_MULTIDOMAIN_AUDIT_2026-09-03.md`

## 2. 已冻结的研究对象口径

主研究对象是：成人 ICU 患者中，在 [T0-24 h, T12) 内已具有可追溯 DHF operational phenotype、并能够到达 T12 的患者。

不要求患者在 T0 入 ICU 时已经完成 DHF 诊断。患者可以在 ICU 早期获得或满足识别 DHF 所需证据，但所有入组证据必须早于 T12。严格 pre-T0 DHF 作为敏感性分析，不替代主窗口。

主事件仍为 T12 后治疗升级相关 ICU hemodynamic deterioration 加 ICU 内死亡；主模型为 Fine-Gray，1 h person-period 为补充。该结局不应表述为 incident cardiogenic shock。

## 3. 为什么心超重要且作为院内严格主队列必需条件

心超是最高优先级的客观心脏证据，可以提供 LVEF、左右室功能、瓣膜、充盈压相关线索等信息；结果可用时应优先纳入 DHF 表型判定。

但“做过心超”只说明检查发生，不说明结果异常。院内严格队列要求的是实际完成、T12 前结果可用且结果支持异常三项同时满足；未检查或结果缺失仍只能记为 unknown，不能判为阴性。该严格队列的检查选择性必须通过全 ICU 候选宇宙报告，而不能假设所有 ICU 患者都做过心超。

因此院内主规则为：`echo-supported DHF ICU cohort` 必须有心超结果支持异常，心超不可用者留在宽口径/桥接审计层；不能把 MIMIC 当前的 procedure-only 审计冒充心超确证。

## 4. 为什么不是 CXR AND CT

CXR 和胸部 CT 均可支持肺部充血，但临床选择性不同。胸片常用于初步评估，CT 通常在诊断不确定、疑似肺栓塞或需要进一步定位时才完成。要求两者同时检查，会优先纳入病情更复杂或检查资源使用更多的患者，并丢失只完成胸片但仍可能是 DHF 的患者。

因此：

- 主影像规则：CXR OR CT；
- CXR-only、CT-supported：分别报告；
- CXR AND CT：仅作严格敏感性分析；
- 任何影像规则都不能单独等同于临床确诊 DHF，需与 HF anchor、时间边界和管理/治疗证据分域组合。

## 5. 结果解释边界

本轮 425/55/449/31 是严格 ICU 前可见的规则支持审计结果，不是主窗口 [T0-24 h, T12) 的最终入组数，也不是全量人工金标准。当前 300 条第一位标注已完成，60 条为同标注者复制，不能用于独立 inter-rater kappa；规则层仍需按预设验证结果和替代诊断标签解释。

NT-proBNP、IV loop 和最终 HF ICD 不能单独确认 DHF。ACS、CKD、PE、肺炎/ARDS 等不应机械全部排除，应作为诱因、共病、替代解释和预设敏感性标签；其存在不自动否定 DHF。

## 6. 尚未解决的问题与估计投入

| 问题 | 下一动作 | 预计主动工时 | 外部依赖 |
|---|---|---:|---|
| 主队列证据层级未冻结 | 向导师提交 multidomain、radiology-supported、echo-result-supported 和 CXR AND CT 分层决策包 | 1-2 h | 导师确认 |
| 主窗口 T0-T12 证据需最终并入 | 对 T0-T12 radiology/echo 可用性按同一时间规则补齐并重报表型计数 | 2-4 h | BigQuery/字段可用性 |
| 独立一致性未完成 | 如论文需要，由第二位临床标注者盲法复核 60 条 | 1-3 h | 临床标注者 |
| 最终模型未重建 | 按最终事件数重新冻结低维特征和 manifest，重跑 Fine-Gray/person-period | 4-8 h | 主表型冻结 |

## 7. 下一步

1. 先由导师确认主队列是否采用 multidomain DHF operational phenotype。
2. 在不把心超检查记录当异常、不把未检查判阴性的前提下补齐主窗口审计。
3. 按最终队列事件数冻结低维预测器；不得将 broad v3.3 的 45 个预测器直接搬到低事件表型层。
4. 完成主模型、补充模型和预设敏感性分析。
