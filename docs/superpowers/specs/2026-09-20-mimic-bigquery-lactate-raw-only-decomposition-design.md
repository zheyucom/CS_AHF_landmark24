# MIMIC BigQuery lactate raw-only 第二层分解设计

日期：2026-09-20

## 目标

对 119 审计中的 549 个 lactate stay-level max `raw-only` stay 做
aggregate-only 第二层分解，判断 derived `bg.lactate` 缺失是否由官方同
specimen PO2 条件、官方乳酸范围、blood-gas specimen 聚合后的时间窗偏移或
其他差异解释。

本审计不创建患者级表，不导出 subject/hadm/stay/labevent/specimen 标识，不修改
119/120，不自动删除 raw 乳酸，不把 QC 数字解释为论文结果，也不晋级正式规则。

## 固定依据与口径

- MIMIC-IV release：3.1。
- cohort：不可变 5,549-stay 审计快照。
- raw：`mimiciv_3_1_hosp.labevents`、`d_labitems`。
- derived：`mimiciv_3_1_derived.bg`。
- 官方方法：`mimic-code@303d26c623dcc9c49cc0f204468d4acc2f063797`
  的 `bg.sql`。
- raw lactate 合同：itemid 50813、Blood、Blood Gas、mmol/L、非空唯一
  `specimen_id`、精确数值、采样 `[T0,T12)`、
  `GREATEST(charttime, COALESCE(storetime, charttime)) < T12`。
- `raw-only`：raw eligible max 存在，且同 stay 在 `[T0,T12)` 没有非空
  `bg.lactate`，必须复现 119 的 549。
- 数值匹配绝对容差：`1e-9`。

官方 `bg.sql` 按 `specimen_id` 聚合，对 blood-gas itemid 集合取
`MAX(charttime)` 和 `MAX(storetime)`；乳酸为 itemid 50813 且
`valuenum <= 10000`，PO2 为 itemid 50821，最终只保留 PO2 非空的 specimen。
公开 `bg` 不暴露 `specimen_id`。

## 方案比较与决定

1. **仅检查同 specimen PO2**：查询最简单，但无法区分乳酸上限和 specimen
   `MAX(charttime)` 把 derived 事件移出 T12 窗口。
2. **完整复制官方 `bg.sql`**：会重复 SpO2、FiO2、A–aDO2 等与乳酸是否保留无关的
   派生过程，扫描与维护成本过高。
3. **最小忠实重建（采用）**：保留官方完整 blood-gas itemid 集合以重建
   `MAX(charttime)`，只计算乳酸、PO2、候选时间窗和公开 `bg` 值匹配。

## 数据流

1. 复用 119/120 的 cohort、字典、合同、可用时间、specimen、删失与范围分类，
   重建 lactate `raw-only` stay 和 raw max。
2. 对这些 stay 内 `[T0,T12)` 的 lactate specimen，回查该 specimen 的官方
   blood-gas itemid 全集，不对 PO2 或其他 blood-gas 组件错误施加项目 landmark
   可用时间门，因为此处是在复现官方 derived 选择而非生成项目特征。
3. 按 specimen 重建官方 `MAX(charttime)`、范围内乳酸和 PO2。
4. 在查询内部判断：是否有同 specimen PO2、是否存在官方候选、候选聚合时间是否
   位于 `[T0,T12)` 或 T12 之后、候选是否能在公开 `bg` 中按 hadm/charttime/value
   匹配。
5. 最终仅输出
   `check_group,concept,cause_code,stay_count,mean_raw_max,max_raw_max`。

## 互斥分类优先级

每个 raw-only stay 只进入一个原因：

1. `no_lactate_specimen_has_po2`：该 stay 的 lactate specimen 均无非空 PO2。
2. `po2_present_all_lactate_values_outside_official_range`：至少一个 specimen 有 PO2，
   但没有 `valuenum <= 10000` 的官方乳酸候选。
3. `official_candidate_in_window_absent_from_public_bg`：重建候选的
   `MAX(charttime)` 位于 `[T0,T12)`，却没有匹配的公开 `bg.lactate`。
4. `official_candidates_all_after_t12`：存在官方候选，但其 specimen
   `MAX(charttime)` 全部位于 T12 或之后。
5. `raw_only_unresolved`：上述信息均不能解释，保留未解释，不猜测。

同时输出以下非互斥 membership：

- `raw_max_specimen_has_po2`
- `any_lactate_specimen_has_po2`
- `any_official_bg_candidate`
- `official_candidate_charttime_in_window`
- `official_candidate_charttime_after_t12`
- `official_candidate_matches_public_bg_any_time`

## 组件与质量门

- `sql_v3_3/bigquery/audits/121_audit_lactate_raw_only_phase_c_bq.sql`：
  aggregate-only BigQuery Standard SQL。
- `project_control/bigquery/run_mimic_lactate_raw_only_bq.py`：20 GB 上限、dry-run
  优先、严格 schema、原因目录和守恒验证。
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`：登记为 `AUDIT_ONLY`、
  `allow_final_run=false`。
- 既有 9 个实验室合同 hard gate 必须完整且全为 0。
- 新增结构门 `raw_only_public_bg_in_window_match` 必须为 0；否则 raw-only 定义与
  公开 derived 匹配自相矛盾。
- `reference_total` 必须为 549，互斥原因合计必须为 549，membership 不得超过 549。

## 失败处理

- SQL 解析、访问授权、20 GB 上限、schema、固定参考数、hard gate 或分类守恒任一
  失败即停止解释并保留失败状态。
- 公开 `bg` 与重建候选不一致时保留为异常聚合，不根据数值相似性强行回填。
- 提交版 `run.json` 只保留脱敏 metadata；CSV 只保留聚合计数和 raw max 摘要。

## 成功标准

- 新测试先因 121 SQL/runner 缺失而失败，再在实现后通过。
- BigQuery dry-run 低于 20 GB，正式查询只输出规定聚合字段。
- 121 `reference_total=549`，互斥原因合计为 549，10 个 hard gate 全为 0。
- MIMIC skill、BigQuery、数据库与静态质量门全套回归通过。
- 结果只进入内部证据、任务报告和非自动晋级的 skill 学习记录。
