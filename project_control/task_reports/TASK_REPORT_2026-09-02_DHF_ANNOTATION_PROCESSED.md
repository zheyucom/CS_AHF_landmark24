# 任务报告：300 条 DHF 影像标注处理与全量患者级审计

日期：2026-09-02  
任务：对照已完成的 300 条标注继续处理；第二位标注者按用户指示与第一位相同。

## 本次完成

1. 读取并验证工作簿 `工作簿1_标注完成版.xlsx`：300 条记录、ID 唯一、标签合法，第一张工作表为有效标注表。
2. 生成第一位标注规范化 CSV。
3. 按用户指示将 60 条第二轮记录复制为同标注者重复，并明确标记为 `same-reviewer repeat`。
4. 计算报告级分层验证指标，并生成 259 个 stay 的验证样本患者级汇总。
5. 基于完整 106/107 导出，对 5,549 个有效 stay 生成规则支持的 DHF 表型层、结局状态和 45 预测器 EPV 审计。

## 300 条标注的关键结果

- definite-positive 规则层：100 条中 78 条为 `definite_congestion`，报告级确认率 78.0%；Wilson 95% CI 68.9%-85.0%。
- 若合并 `possible_congestion`：84/100 = 84.0%，但这不能作为确定性 DHF 证据。
- 分层加权的报告级估计：sensitivity 72.0%、specificity 90.6%、PPV 78.0%、NPV 87.5%。这些不是患者级诊断性能。
- 300 条报告涉及 259 个 stay；按 `storetime < intime` 要求，至少一份人工明确充血报告的验证样本为 79 个；同时有影像明确充血和 loop/NT-proBNP 支持者为 24 个。均为抽样验证样本，不能外推为全队列计数。

## 全量 5,549 stay 冻结前审计

| 规则支持层 | stays | event | alive ICU discharge compete | censor | EPV/45 predictors |
|---|---:|---:|---:|---:|---:|
| DHF candidate（HF anchor + IV loop 或 NT-proBNP） | 650 | 66 | 317 | 267 | 1.47 |
| radiology charttime（HF anchor + definite screen） | 754 | 84 | 374 | 296 | 1.87 |
| radiology available（再要求 storetime < intime） | 580 | 72 | 277 | 231 | 1.60 |
| radiology available + IV loop | 20 | 5 | 5 | 10 | 0.11 |
| radiology available + IV loop 或 NT-proBNP | 221 | 33 | 105 | 83 | 0.73 |

所有层的 event、compete、censor 之和均等于 stays。上述 radiology 层必须称为 `rule-supported operational phenotype`，不能称为全量人工确诊 DHF。

## 方法学限制

- 第二轮 60 条结果是同一标注者复制，100% 一致和 kappa=1 是构造性结果，不能写成独立 Cohen kappa 或独立 inter-rater reliability。
- 300 条是报告级分层抽样；同一 stay 可有多份报告。因此 PPV、sensitivity、specificity 和 NPV 不能替代患者级金标准验证。
- 规则阳性层 PPV 约 78%，说明全量 regex 层会有误触发；它适合用于表型验证/敏感性层，而不是未经导师确认的临床金标准。
- `loop_or_ntprobnp` 是宽松支持口径；只有 IV loop 才可描述为实际治疗证据，NT-proBNP 不能写成治疗证据，也不能单独确诊 DHF。
- 当前 45 预测器下所有候选层 EPV 都很低；不能直接在这些层上运行 45 变量最终模型，必须先冻结主队列并重新按事件数锁定低维特征。

## 交付文件

- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/dhf_radiology_annotation_round1_completed.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/dhf_radiology_annotation_round2_same_reviewer.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/dhf_annotation_validation_metrics.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/dhf_annotation_patient_level_validation_sample.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/dhf_patient_level_rule_supported_audit_20260902.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/dhf_patient_level_rule_supported_outcome_epv_audit_20260902.csv`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/DHF_ANNOTATION_VALIDATION_REPORT_2026-09-02.md`
- `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/DHF_PATIENT_LEVEL_RULE_SUPPORTED_AUDIT_2026-09-02.md`

## 当前下一步

1. 将 `radiology available 580/72` 作为主要候选表型层，将 `radiology + IV loop 20/5` 保留为极严格敏感性层，而不是主建模队列。
2. 由导师确认主队列命名和证据层级；建议使用 `rule-supported operational phenotype`，除非补做更充分人工患者级验证。
3. 主队列冻结后按 EPV 重新锁定低维预测器，再重跑 Fine-Gray 主模型和 1 h person-period 补充模型。
4. 若论文需要独立一致性指标，另请一位临床标注者盲法复核 60 条；当前同标注者重复不需要重算，但不能替代该步骤。
