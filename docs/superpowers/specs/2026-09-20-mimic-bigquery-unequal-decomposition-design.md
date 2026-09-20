# MIMIC BigQuery both-unequal 第二层分解设计

日期：2026-09-20

## 目标

在 119 raw-vs-derived 原因分层审计之上，仅对 BUN、肌酐和乳酸的 stay-level max `both-unequal` 记录做第二层聚合分解。回答两个问题：derived max 是否能在 raw 值集合中找到；差异是否能由结果可用时间、raw 合同、官方派生选择条件或聚合范围解释。

本审计不创建患者级表，不导出 subject/hadm/stay/labevent/specimen 标识，不修改 119，不自动回填、过滤或晋级规则，也不把 QC 计数解释为论文最终结果。

## 固定依据与范围

- MIMIC-IV release：3.1。
- raw：`mimiciv_3_1_hosp.labevents` 与 `d_labitems`。
- derived：`mimiciv_3_1_derived.chemistry` 与 `bg`。
- cohort：不可变 5,549-stay 审计快照。
- landmark：`[T0,T12)`；raw 可用时间为 `GREATEST(charttime, COALESCE(storetime, charttime)) < T12`。
- 官方方法：`mimic-code@303d26c623dcc9c49cc0f204468d4acc2f063797` 的 `chemistry.sql` 与 `bg.sql`。
- 数值匹配容差：绝对误差 `1e-9`。
- 只处理 max；delta 留待最终特征合同冻结后独立验证。

官方 `chemistry.sql` 按 `specimen_id` 聚合，BUN 使用 itemid 51006、`0 < valuenum <= 300`，肌酐使用 itemid 50912、`0 < valuenum <= 150`。官方 `bg.sql` 按 `specimen_id` 聚合乳酸 itemid 50813，并要求同一 blood-gas specimen 有非空 PO2；公开 derived `bg` 不暴露 `specimen_id/storetime`。

## 方案比较与决定

1. **仅做值集合匹配**：实现简单，但无法说明乳酸 specimen 是否因官方 PO2 条件被排除。
2. **完整复制官方 derived SQL**：解释最细，但重复整个派生流水线，维护成本高，且容易与官方更新产生第二份漂移实现。
3. **混合分解（采用）**：做方向和值集合匹配，并只复现与 BUN/肌酐/乳酸直接相关的官方 itemid、范围、specimen 聚合和乳酸 PO2 条件。

## 数据流

1. 读取固定 cohort 和三个 raw itemid，保留查询内部的 provenance、合同、可用时间、result class、范围和 specimen 信息。
2. 构造 raw 值集合：
   - `eligible_raw_set`：合同、时间、specimen、精确数值和范围均通过；
   - `late_contract_raw_set`：合同通过但 T12 后才可用；
   - `other_quarantine_raw_set`：合同/时间以外原因未通过；
   - `official_itemid_raw_set`：仅按固定官方 itemid 与范围选择。
3. 读取 derived event 值，按 stay 生成 derived max；按同一 stay 生成 raw eligible max。
4. 仅保留两边均有值且差异超过 `1e-9` 的 stay，在查询内部判断：
   - derived max 是否命中各 raw 集合；
   - raw max 是否存在于 derived event 集合；
   - 差异方向；
   - chemistry specimen 是否存在于 derived；
   - 乳酸 raw-max specimen 是否满足官方 PO2 条件。
5. 最终只输出 `check_group/concept/direction/cause_code/stay_count/mean_abs_diff/max_abs_diff`。

## 互斥分类优先级

按以下优先级，每个 `both-unequal` stay 只进入一个原因：

1. `precision_only`：差异不超过 `1e-9`；作为结构哨兵，正常应为 0。
2. `derived_higher_matches_late_raw`：derived max 高于 raw max，且 derived max 能在合同正确但 T12 后才可用的 raw 值中找到。
3. `derived_higher_matches_other_quarantine_raw`：derived max 只在其他 quarantine raw 值中找到。
4. `derived_higher_not_found_in_raw`：derived max 在同 stay 的 raw 源值中无法找到。
5. `raw_higher_lactate_specimen_missing_po2`：乳酸 raw max 更高，其 specimen 不满足官方 `bg.sql` 的 PO2 条件。
6. `raw_higher_specimen_absent_from_derived`：raw max 更高，其 chemistry specimen 或重建的 blood-gas specimen 未出现在 derived 事件集合。
7. `raw_higher_derived_value_in_eligible_raw_set`：derived max 能在 eligible raw 中找到，但更高的 raw max 未成为 derived max，表示派生选择/聚合范围差异。
8. `raw_higher_unresolved`、`derived_higher_unresolved`：现有字段不足以确定原因，保留为未解释，不强行归因。

另外输出非互斥 membership 汇总，分别统计 `derived_max_in_eligible_raw_set`、`derived_max_in_late_raw_set`、`derived_max_in_any_raw_set` 与 `raw_max_in_derived_event_set`，用于核验互斥分类没有掩盖信息。

## 组件

- `sql_v3_3/bigquery/audits/120_audit_raw_vs_derived_unequal_phase_c_bq.sql`：aggregate-only BigQuery Standard SQL。
- `project_control/bigquery/run_mimic_raw_derived_unequal_bq.py`：20 GB 上限、dry-run 优先、严格输出 schema 和 hard-gate 完整性。
- 现有 BigQuery 回归文件新增 120 合同、runner 和脱敏证据测试。
- 提交版 `run.json` 与 `aggregate_qc.csv` 只保留脱敏 metadata 和聚合输出。

## 失败处理

- SQL 解析、授权、字节上限、schema 或 hard gate 任一失败即停止正式解释。
- 9 个既有实验室合同 hard gate 必须完整、唯一且全为 0。
- 新增结构 gate：第二层互斥分类总数必须等于 `both-unequal` 总数；membership 只作交叉核验，不参与互斥加总。
- 无法归因的记录保留为 `unresolved`，不得根据数值范围或模型表现猜测。

## 成功标准

- 测试先失败后通过。
- BigQuery dry-run 低于 20 GB，正式运行仅输出聚合字段。
- 119 的 `both-unequal` 数量与 120 的互斥原因总数逐概念一致。
- 全套 MIMIC skill、Phase-C、静态质量门与正式入口回归通过。
- SQL 登记为 `AUDIT_ONLY`、`allow_final_run=false`；不自动晋级 `ACTIVE`。
