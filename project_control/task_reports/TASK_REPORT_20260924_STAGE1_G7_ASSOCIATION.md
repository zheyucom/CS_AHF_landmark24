# 任务报告：研究一 G7 低维院内死亡关联分析

日期：2026-09-24
状态：G7_COMPLETED_WITH_PRE_SPECIFIED_LOW_DIMENSION_MODEL

## 1. 研究问题和边界

- 人群：本院 A+B+C 操作性 DHF 队列 773 人。
- 时间零点：index ICU 入科 T0。
- 结局：同次住院病案首页确认的院内全因死亡，62 例。
- 候选因素：年龄、性别、入院途径（急诊 vs 非急诊）。
- 合并症只做描述性和来源缺失审计，不进入本版调整模型。
- 本分析是预后因素关联和假设生成，不是第二个死亡预测模型，也不作因果解释。

## 2. 模型和质量门

- 使用自包含的 Jeffreys/Firth 惩罚 Logistic 实现，年龄按线性项并以中位数居中。
- 有效自由度为 3，低于预设上限 4。
- 未进行单因素 P 值筛选、逐步回归、AUC 优化或变量竞赛。
- 内置分离数据数值 smoke test 通过。
- 主分析、严格客观表型敏感性分析和排除 2024 不完整期敏感性分析均收敛；12 个系数行的 OR 和置信区间均为有限数值。

## 3. 结果（仅作关联描述）

| 分析 | n | 死亡 | 年龄 OR（每岁） | 男性 OR | 急诊入院 OR |
|---|---:|---:|---:|---:|---:|
| 主 A+B+C | 773 | 62 | 1.005（0.986–1.024） | 0.995（0.588–1.686） | 0.792（0.473–1.326） |
| 严格客观层 | 594 | 52 | 1.002（0.983–1.022） | 0.902（0.508–1.602） | 0.779（0.441–1.375） |
| 排除 2024 | 768 | 61 | 1.003（0.984–1.022） | 0.961（0.566–1.631） | 0.767（0.457–1.288） |

置信区间较宽，不能据此宣称没有关联；结果主要用于描述本院病例组合和后续研究假设。

## 4. 一致性和限制

三组分析方向和不确定性范围相近，但事件数有限、合并症来源缺失较多，因此不扩展变量、不解释为独立危险因素。研究一结果不得反向修改 MIMIC 变量、阈值、时间窗或研究三外部验证切点。

## 5. 输出

- project_control/designs/INTERNAL_DHF_STAGE1_T0_FACTOR_CONTRACT_V1_20260924.md
- project_control/runs/20260924_internal_stage1_g7_comorbidity_mapping/
- project_control/runs/20260924_internal_stage1_g7_association/model_input_v1.csv
- project_control/runs/20260924_internal_stage1_g7_association/model_input_qc.json
- project_control/runs/20260924_internal_stage1_g7_association/association_model_results_v1.csv
- project_control/run_internal_stage1_g7_firth.R

原始 DHF_SRR 未修改，eMAR 到位后只用于 T12–T60 执行级治疗升级重建。
