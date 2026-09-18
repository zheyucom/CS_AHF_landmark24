# DHF 300 条影像标注验证报告

日期：2026-09-03

## 结论

Excel 第一张表作为第一位标注者的完成结果导入并通过 ID/标签 QC。第二位标注者按用户指示复制第一位结果，因此重复一致率和 kappa 为构造性结果，不能作为独立双盲 inter-rater reliability；正式论文应将该验证降级说明，不能声称完成独立双标注。

## 报告级结果

| 筛查层 | 全部报告数 | 抽样数 | definite | possible | no | indeterminate |
|---|---:|---:|---:|---:|---:|---:|
| definite_positive_rule_screen | 1259 | 100 | 78 | 6 | 13 | 3 |
| negated_or_uncertain_screen | 864 | 100 | 29 | 6 | 19 | 46 |
| no_hit_screen | 2180 | 100 | 6 | 2 | 3 | 89 |

阳性规则层中明确充血比例为 **78/100 = 78.0%**（Wilson 95% CI：68.9%–85.0%）；若将 possible 合并为非确定性支持，则为 84/100 = 84.0%。这些是报告级、分层抽样估计，不是 DHF 确诊率。

按完整报告层规模加权、以 `definite_congestion` 为参考，报告级敏感度约 **72.0%**、特异度约 **90.6%**、PPV **78.0%**、NPV **87.5%**。由于标注样本是报告级分层抽样，且同一患者可有多份报告，这些数字不能替代患者级表型验证。

## 患者级验证样本

300 条报告涉及 259 个 stay。至少一份明确充血报告（按 charttime）为 107 个；按 `storetime < intime` 的可见性要求为 79 个；同时满足影像明确充血和 pre-T0 loop/NT-proBNP 支持的 multidomain 验证样本为 24 个。该结果仅适用于 300 条验证报告涉及的患者，不能外推为 5,549 个候选 stay 的完整队列。

工作簿中 `final_comments` 缺失 189/300 条；不对缺失备注补写临床判断，保留为空并在 QC 中记录。

这些 stay 中已有结局标签审计：event 36、alive ICU discharge compete 121、censor 102；仅作验证样本描述，不用于冻结主模型。

## 文件

- `dhf_radiology_annotation_round1_completed.csv`：Excel 第一张表规范化结果。
- `dhf_radiology_annotation_round2_same_reviewer.csv`：按用户要求复制的 60 条重复复核。
- `dhf_annotation_validation_metrics.csv`：报告级性能和一致性指标。
- `dhf_annotation_patient_level_validation_sample.csv`：验证样本患者级分层与结局审计。

## 下一步

1. 不把同一标注者复制结果写成独立 inter-rater kappa。
2. 如需正式方法学验证，补充一位真正独立的临床标注者对 60 条报告的盲法复核；否则把影像域定位为人工复核的单标注验证/weak-label sensitivity。
3. 在导师确认证据层级后，必须从完整 5,549 个候选重新构建患者级 radiology-supported/multidomain DHF 表型，不能仅用这 300 条抽样报告构建最终主队列。
