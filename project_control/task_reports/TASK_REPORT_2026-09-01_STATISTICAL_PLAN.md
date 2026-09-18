# 任务报告：DHF 预测模型统计分析方案补齐

日期：2026-09-01  
状态：已完成统计方案草案，等待 DHF 表型冻结后执行

## 本次完成

1. 明确 Fine-Gray 作为主模型的理由：它直接对应“48 h 目标事件 CIF，alive ICU discharge 为竞争事件”的研究 estimand。
2. 将 1 h person-period 定位为时间结构补充，将 cause-specific Cox 定位为机制/组件敏感性，而不是另一个可自由试错的主模型。
3. 明确普通 Logistic、Fisher 精确检验和单因素 P 值筛选的适用边界：Logistic 只能作为有明确固定 horizon 和竞争事件处理的敏感性；Fisher 和单因素分析不用于筛选预测变量。
4. 规定以 elastic net 作为唯一预设惩罚回归比较，alpha 预先冻结，训练折内 10 折选 lambda，外层 5 折估计性能；所有插补/标准化/选择必须折内完成。
5. 将随机森林/XGBoost限制为有条件的竞争风险基准模型，将 SHAP 限定为 OOF 树模型解释，不作为训练集变量筛选或因果解释；ridge/LASSO 不作为常规必做模型。
6. 澄清历史 650/66 队列只是严格口径可行性审计，不能作为“先测试再用 5,555 例正式建模”的固定两阶段设计。

## 文献核验

通过 Crossref 核对了计划中的关键 DOI，并修正了一个引用：`10.1002/sim.7993` 是连续结局样本量论文，已改为 van Smeden 二分类模型论文的正确 DOI `10.1177/0962280218784726`。另补充 TRIPOD+AI 2024（doi:10.1136/bmj-2023-078378）。

## 标注交互调整

新增中英对照指南和中文快速开始文档。说明原始报告保留英文、标准标签保留英文值；Codex 可以提供 AI-assisted 草标和逐条解释，但不能把自动草标直接包装成临床金标准。另修正判读边界：仅“未提及肺充血”应标 `indeterminate`，只有明确否定才标 `no_congestion`。

进一步发现本轮 300 条抽样含非胸部放射科检查，已在草标中增加 `report_scope`，并规定仅胸部/胸腔报告的 `FINDINGS/IMPRESSION` 可用于肺充血判读；非胸部检查不作为肺充血证据。

## 当前用户可选路径

- 推荐：由 Codex 先完成 300 条 AI-assisted 草标，再由用户/导师复核不确定和冲突病例，并保留 60 条独立临床复核。
- 可接受但证据较弱：跳过人工复核，保留 broad operational HF 队列；影像只作为 rule-based/weak-label 敏感性分析，不将其写成确认的 DHF 表型。
- 不建议：直接把关键词阳性表当作 DHF 金标准并据此声称已准确筛选患者。

## 草标工作副本

已生成 `project_control/bigquery/controlled_annotation_20260830_v2/dhf_radiology_annotation_round1_codex_draft.csv`：300 行、23 列，包含英文原文、术语辅助中文、关键证据句中英对照、Codex 草标和留给人工确认的 `final_*` 列。草标分布为：`definite_congestion` 102、`possible_congestion` 4、`no_congestion` 27、`indeterminate` 167；该分布是工作提示，不是最终研究结果。已通过 Python CSV 读写和脚本语法检查。

新增 `project_control/bigquery/merge_dhf_annotation_review.py`，用于在人工填写完成后检查标签、ID、空值和 `human_reviewed` 状态，再导出原始标注表格式。空白最终字段测试已按预期失败，证明未复核草标不会被误回写。

## 当前可靠基础

- broad v3.3 eligible cohort：5,555 stays、454 主事件。
- 当前 compact 候选：45 个，名义事件/变量约 10.1；最终 DHF 表型冻结后必须重新计算。
- 已有 Fine-Gray 5 折 OOF、1 h person-period OOF 和缺失指示敏感性结果，但在 DHF 多域表型冻结前不能写成最终论文结果。

## 仍未完成

1. 完成 `controlled_annotation_20260830_v2` 中 300 条第一轮标注和 60 条独立复核。
2. 计算 PPV、Cohen kappa、替代诊断/否定表达误触发，并确定 DHF 证据层级。
3. 按最终主队列重算事件数、有效参数数、缺失率和样本量/收缩要求。
4. 更新 R 分析脚本，使最终版本明确区分外层性能评估、内层 lambda 选择和全数据最终拟合。
5. 依次运行主 Fine-Gray、person-period、预设敏感性及有条件的机器学习基准。

## 关键文件

- 统计分析计划：[STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md](../STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md)
- 实时研究总览：[RESEARCH_DASHBOARD.md](../RESEARCH_DASHBOARD.md)
- 特征冻结合同：[FEATURE_FREEZE_V33.md](../FEATURE_FREEZE_V33.md)
- 当前人工标注交接：[NEXT_ACTION_DHF_ANNOTATION.md](../NEXT_ACTION_DHF_ANNOTATION.md)

## 下一步

当前用户优先动作仍是完成盲法临床标注；标注结果返回后，自动继续 QC、分层、事件数审计和最终模型冻结。统计计划已经补齐，因此当前阻塞不是分析方法选择，而是表型验证和最终主队列尚未冻结。
