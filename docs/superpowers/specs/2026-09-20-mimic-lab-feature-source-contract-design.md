# MIMIC 实验室特征来源与时间合同设计

日期：2026-09-20

## 1. 目的

将 118–121 的实验室合同、raw-vs-derived 对账和原因分解结论，转成可由测试读取的特征来源决策矩阵；同时修复候选结局 SQL 中乳酸 pre-T12 可用时间门不完整的问题。

本设计仍处于正式队列冻结前：不修改历史 SQL 原件，不导出患者级数据，不把审计快照数字写成论文结果，不把任何候选 SQL 晋级为 `ACTIVE`。

## 2. 已确认问题

`sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql` 以 `charttime` 区分 pre/post-T12，但候选乳酸只统一要求 `availability_time < observed_until_time`。因此，采样在 T12 前但 T12 后才可用的结果可能进入 pre-T12 基线。

该风险不是推测：119–120 已确认 BUN、肌酐和部分乳酸 raw/derived 差异由 T12 后才可用的 raw 结果解释。继续依赖 v2 会破坏 landmark 预测的时间因果顺序。

## 3. 方案比较与选择

### 方案 A：只新增文字说明

优点是改动最少；缺点是后续 SQL 修改时无法自动发现来源或时间合同回退，因此不采用。

### 方案 B：机器可读矩阵、回归门和版本化 SQL 修复

矩阵登记每个正式候选实验室特征的概念、角色、主来源、采样窗、可用窗、聚合、顺序、缺失解释和 derived 用途；测试同时核对矩阵和 SQL。历史 v2 保留，新增 v3 修复时间门。该方案可审计、可复用且不需要提前晋级生产规则，采用此方案。

### 方案 C：立即把全部规则写入生产质量门并解锁正式运行

最终 DHF 表型、风险集、结局和完整依赖尚未冻结，此时晋级会把候选定义误当成正式定义，因此不采用。

## 4. 交付物

1. `project_control/MIMIC_LAB_FEATURE_SOURCE_DECISION_MATRIX_V1.csv`
   - 一行对应一个直接输出或内部派生所需的实验室特征。
   - 覆盖当前 v3.3 候选主线中的预测变量、表型支持变量和结局乳酸变量。
   - 明确 raw 为主源、derived 仅用于对账；不复制患者级结果或审计计数。
2. `project_control/quality_gates/mimic_lab/tests/test_feature_source_decision_matrix.py`
   - 校验矩阵 schema、枚举、唯一键、证据路径、主来源和缺失语义。
   - 校验使用 `max/min/first/last/delta` 的 SQL 与矩阵一致。
   - 校验非审计 v3.3 SQL 不读取 `mimiciv_derived.bg` 或 `mimiciv_derived.chemistry`。
   - 锁定 063A v3 的 pre/post 双时间门，防止 pre-T12 late result 泄漏。
3. `sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v3.sql`
   - 从 v2 复制为新版本，不覆盖 v2。
   - pre-T12：`charttime` 与 `availability_time` 都必须位于 `[T0,T12)`。
   - post-T12：`charttime` 与 `availability_time` 都必须位于 `[T12, observed_until)`。
   - 采样在 T12 前、T12 后才可用的结果不进入 pre 或 post 生理窗口。
   - first/last 以 `charttime, labevent_id` 做确定性顺序；可用时间用于资格门，不用于改变生理采样顺序。
4. 权威清单、任务报告、总览与索引更新。

## 5. 决策矩阵合同

矩阵至少包含以下字段：

- `feature_key`：`sql_path::feature_name` 唯一键。
- `feature_name`、`concept`、`research_role`。
- `source_sql`、`source_relation`、`source_policy`。
- `sample_window`、`availability_window`、`aggregation`、`sequence_order`。
- `value_policy`、`missingness_policy`、`derived_policy`。
- `evidence_refs`、`freeze_status`。

允许的核心策略固定如下：

- `source_policy=raw_contract_primary`。
- `source_relation=study_ahf_v3_3.lab_eligible_v1`。
- `derived_policy=reconciliation_only`。
- 连续聚合仅使用 `analysis_value`；删失结果只能支持已经被边界完全确定的一侧阈值判断。
- first/last/delta 必须有确定性顺序，delta 明确为 `last - first`。
- 未测量、迟到、隔离或不可解析均保持缺失，不补零、不从 derived 静默回填。

## 6. 版本和权限状态

- 063A v2 保持原样并继续 `LEGACY_BLOCKED`。
- 063A v3 登记为新的候选结局 SQL，但仍为 `LEGACY_BLOCKED`、`allow_final_run=false`。
- 118–121 继续为 `AUDIT_ONLY`。
- 矩阵描述候选特征合同，不代表最终队列或论文变量已冻结。

## 7. 验证顺序

1. 先新增失败测试，证明当前缺少矩阵、v3 和 pre-T12 可用时间门。
2. 新增矩阵与 v3，使测试转绿。
3. 运行 MIMIC skill 规则包、fixtures、edge cases。
4. 运行 BigQuery、PostgreSQL Phase-C、语义审计、start-run 和质量门回归。
5. 对新 v3 运行 SQL 解析与 MIMIC 静态扫描。
6. 只在有可复现数据库连接时运行聚合 QC；未运行则明确标记 `not_run`，不得声称 v3 数据库结果已验证。

## 8. 验收标准

- 历史 v2 未被修改。
- 矩阵覆盖当前候选主线全部实验室聚合输出及 first/last 内部组件。
- 063A v3 明确阻止 pre-T12 late result 进入基线。
- 正式候选实验室特征不读取官方 derived chemistry/bg 作为主源。
- 所有测试和质量门通过，Git 工作树仅包含本轮预期文件。
- 提交后本地与 `origin/main` SHA 一致。
