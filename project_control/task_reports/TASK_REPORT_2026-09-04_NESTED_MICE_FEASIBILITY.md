# 任务报告：嵌套 MICE 缺失处理可行性

日期：2026-09-04  
状态：已完成可行性运行；最终锁模等待 DHF 表型冻结

## 本轮完成

- 运行 `analysis_r/094_finegray_mice_sensitivity_v33.R`：5 折外层验证、每折 `m=5`、`maxit=5`、随机种子 `20260904`。
- 每个训练折仅以 T12 前 45 个预测变量进行 PMM MICE；验证折不读取其自身结局，只从完成训练折的供体进行 PMM 插补。
- 分别拟合 MICE-only 与 MICE+缺失指示器 Fine-Gray，完成患者级 48 h OOF CIF 和独立 OOF 评价。

## 可报告的工程/可行性结果

| 指标 | MICE-only | MICE + 缺失指示器 |
|---|---:|---:|
| 48 h OOF AUC | 0.7533 | 0.7566 |
| 48 h Brier | 0.06533 | 0.06490 |

- 输入为 5,555 stay、454 主事件；每个验证折有 90--92 个主事件。
- 五折均没有 `mice` logged event。
- 每折进入 3--4 个非冗余缺失指示器。

## 解释边界

该运行证明：在现有 v3.3 rule-supported development candidate 上，严格训练折内插补与竞争风险 OOF 评价可以稳定完成；检测可用性指示器对性能的影响较小。它不证明最终 DHF 模型性能，因为当前表型仍未冻结且 `m=5` 小于正式锁模拟采用的 `m=20`。

## 下一步

1. 冻结 MIMIC 多域 DHF 主表型和该表型的有效参数上限。
2. 用冻结后输入重跑 MICE `m=20`、MICE+缺失指示、中位数和 complete-case 诊断。
3. 运行锁模版 Fine-Gray 主模型、1 h person-period 补充模型以及预设表型/删失敏感性。

结果目录：`project_control/runs/20260904_finegray_mice_feasibility_v1/`。
