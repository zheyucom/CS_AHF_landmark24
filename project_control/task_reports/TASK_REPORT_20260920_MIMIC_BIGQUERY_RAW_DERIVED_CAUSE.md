# MIMIC raw-vs-derived 原因分层：BigQuery 聚合审计

日期：2026-09-20

## 1. 用户问题与本轮范围

在 BigQuery Phase-C 合同审计通过后，本轮继续对 BUN、肌酐和乳酸的 raw-vs-derived 差异进行原因分层。目标是区分可由原始记录直接支持的迟到结果、删失/非数值、范围外、单位/字典合同不符、缺 specimen 与重复 specimen，并报告 raw-only、derived-only、both-equal、both-unequal 的聚合计数。

本轮仍是内部 QC：不创建患者级永久表，不导出患者/住院/stay/labevent/specimen 标识，不修改历史 SQL，不调整分析范围以追求更好覆盖率，不将结果晋级为 `ACTIVE` 或写作论文最终结果。

## 2. 使用的文件、版本和数据状态

- 数据源：PhysioNet BigQuery MIMIC-IV 3.1 的 raw `labevents`/`d_labitems`，derived `chemistry`/`bg`。
- 队列：不可变 `ahf_work.dhf_lab_audit_cohort_snapshot_20260918`，5,549 个有效 stay。
- BUN/肌酐对账键：stay + `specimen_id`；乳酸对账键：stay + `charttime`。乳酸 derived `bg` 不暴露 `specimen_id` 或 `storetime`，因此该键的限制保留在解释中。
- 结果窗口：采样时间 `[T0,T12)`；raw 可用时间为 `GREATEST(charttime, COALESCE(storetime, charttime))`。
- SQL 模板 SHA-256：`19bbe735ad5839285f8387b0426276d3abb3b01cceb98c905d92f6375ae85519`。
- runner SHA-256：`082b7d788633c31a7e72e52fae4edd6aa84122ef5c7a8524d1c5a34952294a42`。
- 规则包 SHA-256：`9f0fd0eca70dbd8e08ea3d17367b382154f9f961e817127443dfc9037aa1f720`。

## 3. 已验证事实与证据

### 3.1 BigQuery 作业

- dry-run：约 9,798,093,020 bytes，低于 20 GB 上限。
- 正式作业：`bqjob_r4479c54773e5d64c_000001a0bd4603dc_1`（仅记录脱离个人项目名的作业后缀）。
- 状态：`DONE`，无 `errorResult`；处理 9,798,093,020 bytes，计费 9,798,942,720 bytes，5,323,426 slot-ms，未命中缓存。
- 输出 70 行聚合结果，runner 状态为 `passed_aggregate_qc`。

### 3.2 合同与原始原因

9 个 hard gate 全部为 0：active/quarantine 字典、cohort 唯一性/边界/关键键、eligible 合同、时间、specimen，以及 BUN 血液合同均通过。

| 概念 | eligible raw 事件 | contract-ok 迟到事件（stay） | contract-ok 删失/非数值（事件） | 合同错误事件（stay） |
| --- | ---: | ---: | ---: | ---: |
| BUN | 6,917 | 644（643） | 1（1） | 384（377） |
| 肌酐 | 6,936 | 649（648） | 1（1） | 0（0） |
| 乳酸 | 4,932 | 38（38） | 0（0） | 0（0） |

本窗口内三种概念均未发现范围外、`storetime < charttime`、缺 specimen 或重复 `specimen_id × itemid`。BUN 的 384 个合同错误事件对应已登记的非血液 quarantine 集合；没有进入 eligible raw。

原因事件计数是可重叠的审计维度，不应把各行相加当作唯一事件总数；`*_contract_ok` 行用于排除已知错误体液/合同污染后的解释。

### 3.3 特征层 raw-vs-derived 覆盖与差异

| 概念 | 两边都有 | derived-only | raw-only | both-equal | both-unequal | unequal 平均绝对差 | unequal 最大绝对差 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BUN max | 4,985 | 142 | 0 | 4,763 | 222 | 3.0856 | 44.0 |
| 肌酐 max | 4,987 | 142 | 0 | 4,825 | 162 | 0.1840 | 0.9 |
| 乳酸 max | 2,357 | 4 | 549 | 2,221 | 136 | 0.6801 | 3.9 |

- BUN 的 142 个 derived-only stay 均同时存在 contract-ok raw 迟到记录，计数与此前 Phase-C 迟到结果规模一致；这支持“derived 只按 charttime、raw 受 storetime 可用性门控”的解释，但不是逐 stay 的因果证明。
- 肌酐的 142 个 derived-only stay 同样均伴随 contract-ok raw 迟到记录。
- 乳酸仅 4 个 derived-only stay 伴随迟到 raw；另有 549 个 stay 为 raw-only。由于 derived `bg` 不暴露 specimen/storetime，raw-only 不能单独归因于某一条清洗规则。
- both-unequal 被保留为“尚未归因”的聚合差异；本轮不依据差异方向或模型表现修改合同。

## 4. 判断与影响

本轮把“差异存在”进一步拆成了可由 raw 记录直接观察的原因维度。对项目最有帮助的结论是：BUN 与肌酐的 derived-only 覆盖缺口主要与 T12 后才可用的 raw 结果共同出现；如果只按 charttime 使用 derived 值，可能把当时尚不可用的结果纳入 T12 特征。乳酸的 raw-only 规模较大，必须保留 raw/derived 双向对账，不能把 derived `bg` 当作完整真值。

这些数字只描述本次 5,549-stay 审计快照和 max 聚合，不是最终建模队列、模型性能或论文结果。

## 5. 新增或确认的研究决策

- 新增 `119_audit_raw_vs_derived_cause_phase_c_bq.sql`，登记为 `AUDIT_ONLY`，`allow_final_run=false`。
- 以 `specimen_id`/`charttime` 的实际派生表能力选择对账键，不伪造乳酸 specimen 关联。
- raw-only、derived-only、both-unequal 只作为差异审计标签；不自动回填、不自动删除、不自动晋级规则。
- `both-unequal` 需要后续独立的受控原因审计，当前不把它归因于某个单一清洗规则。

## 6. 未决问题、阻塞项和假设

- 119 审计比较的是 max 聚合；delta、first/last 口径仍需在最终特征冻结时单独验证。
- derived 表没有 raw 的 storetime 和完整合同元数据；derived-only 与 unequal 的解释仍受信息缺失限制。
- v3.3 完整上游依赖、DHF 表型、T12 风险集和三态结局仍未冻结，正式路径继续 fail-closed。
- raw 事件原因计数允许同一事件同时落入多个维度，报告时必须保留该定义。

## 7. 下一步动作

1. 对 both-unequal stay 做仅聚合的第二层分解：derived max 是否能在 raw 合约值集合中找到、是否存在同一 specimen/charttime 的聚合口径差异。
2. 在最终队列冻结后，分别验证 max 与 delta 的时间/聚合合同，并重跑 119。
3. 只有在完整依赖链、数据库 QC 和研究定义冻结后，才讨论候选 SQL 是否进入 `ACTIVE`。

## 8. 本轮修改文件

- `sql_v3_3/bigquery/audits/119_audit_raw_vs_derived_cause_phase_c_bq.sql`
- `project_control/bigquery/run_mimic_raw_derived_cause_bq.py`
- `project_control/bigquery/tests/test_mimic_lab_phase_c_bq.py`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/audits/bigquery_raw_derived_cause_20260920/run.json`
- `project_control/audits/bigquery_raw_derived_cause_20260920/aggregate_qc.csv`
- `project_control/task_reports/TASK_REPORT_20260920_MIMIC_BIGQUERY_RAW_DERIVED_CAUSE.md`
- `project_control/task_reports/README.md`

## 9. 可重复性信息

- 本机原始运行目录：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/bq_raw_derived_cause_20260920_live_02/`。
- 可提交的脱敏证据目录：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/bigquery_raw_derived_cause_20260920/`。
- 脱敏 `run.json` SHA-256：`4cadac34aa759b00360527da9c9e71bb0c4f0df4eb0c533a055fa1aae673cae7`。
- 聚合 CSV SHA-256：`a7424ed48d51fea0d2be24d77b384bb93769c9418c2ce6c9c8058d6133ed47e0`。
- 运行无随机过程，不涉及 seed；所有输出均为聚合计数或差异摘要。
