# DHF 患者级规则支持表型与结局/EPV 审计

日期：2026-09-02

## 解释边界

本文件把 106/107 的全量 radiology regex 结果汇总到 stay level，供冻结前审计。所有 radiology 层均命名为 `rule-supported operational phenotype`，不是 5,549 个 stay 的人工确诊 DHF。300 条人工标注是报告级分层验证样本，不能直接回填全量患者标签。

`multidomain_loop_rule_supported` 使用 IV loop 作为实际治疗证据；另列 `loop_or_ntprobnp` 仅作宽松敏感性口径，不能把 NT-proBNP 写成治疗证据。

## 全量队列结果

| 表型层 | stays | event | alive ICU discharge compete | censor | EPV (45 predictors) |
|---|---:|---:|---:|---:|---:|
| `dhf_candidate_rule_supported` | 650 | 66 | 317 | 267 | 1.47 |
| `radiology_supported_charttime_rule_supported` | 754 | 84 | 374 | 296 | 1.87 |
| `radiology_supported_available_rule_supported` | 580 | 72 | 277 | 231 | 1.60 |
| `multidomain_loop_rule_supported` | 20 | 5 | 5 | 10 | 0.11 |
| `multidomain_loop_or_ntprobnp_rule_supported` | 221 | 33 | 105 | 83 | 0.73 |

所有层的 event + compete + censor 应等于该层 stays；EPV 只是当前 45 个候选预测器下的冻结前审计，不代表最终模型已经批准使用 45 个变量。

## 交付文件

- `dhf_patient_level_rule_supported_audit_20260902.csv`：5,549 个 stay 的逐患者证据和结局字段。
- `dhf_patient_level_rule_supported_outcome_epv_audit_20260902.csv`：各规则支持层的样本量、结局和 EPV。
- `DHF_PATIENT_LEVEL_RULE_SUPPORTED_AUDIT_2026-09-02.md`：本审计说明。

## 尚未解决

1. 规则阳性层单标注 PPV 为 78.0%，因此全量规则支持层仍存在误触发，不能当作临床金标准。
2. 60 条重复是同标注者复制，未产生独立 inter-rater kappa。
3. 主队列应在导师确认后从上述层中冻结；冻结后才重建最终无泄露预测器并重跑 Fine-Gray。
