# MIMIC 实验室流水线阶段 B 实施计划

日期：2026-09-19

## 目标

在不改写历史 SQL 的前提下，建立版本化 raw `labevents` 合同层，并复制修订项目当前依赖实验室结果的 NT-proBNP、乳酸结局和 45 变量建模路径。

## 实施顺序

1. 先增加无患者数据回归测试，覆盖精确 itemid/metadata、单位、可用时间、重复 specimen、删失边界、官方分析范围及 episode 多重匹配。
2. 建立 `sql_v3_3/executable/060_create_raw_lab_contract_layer_v1.sql`，产出合同、已知错误体液、全量分类和合格事件四张表。
3. 复制修订 `061A/061C/061E/063A/090B`；历史 `sql_v3_2` 文件不原地修改。
4. 用 PostgreSQL parser 做语法检查；运行阶段 A/B 全部无患者数据回归测试和全仓静态质量门。
5. 可访问 BigQuery 时仅做聚合 QC；不得导出或提交患者级数据。
6. Postgres 实际执行不可用时，将数据库验证明确记为 `not_run`，全部新 SQL 保持 `LEGACY_BLOCKED`，正式入口继续 fail-closed。

## 晋级条件

- 规则来源固定到 MIMIC-IV 3.1 与 `mimic-code` commit `303d26c623dcc9c49cc0f204468d4acc2f063797`。
- 静态回归、SQL parser、清单覆盖和质量门全部通过。
- PostgreSQL 中 raw 层实际建表成功，隔离计数和 episode 匹配 QC 可解释且关键违规为零。
- 完整上游依赖链有相同级别 QC；不能只因局部 SQL 合格而晋级 ACTIVE。

## 明确不做

- 不把 derived laboratory 表作为正式实验室来源。
- 不将 `>x/<x/区间` 伪装为精确连续值。
- 不把官方分析范围描述为物理不可能范围。
- 不因阶段 B 完成而重跑或冻结最终队列、事件数或模型结果。
