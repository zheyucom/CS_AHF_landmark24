# MIMIC both-unequal 第二层分解：BigQuery 聚合审计

日期：2026-09-20

## 1. 用户问题与本轮范围

本轮继续解释 119 审计中 BUN、肌酐和乳酸 stay-level max 的
`both-unequal`，区分结果可用时间、raw quarantine、官方 derived 选择条件、
specimen 选择和未解释差异。

本轮新增版本化 120 审计，不修改 119，不创建患者级永久表，不导出
subject/hadm/stay/labevent/specimen 标识，不自动删除或回填数据，也不把 QC
数字写成论文结果或晋级为正式生产规则。

## 2. 使用的文件、版本和数据状态

- MIMIC-IV：3.1。
- 队列：不可变 `dhf_lab_audit_cohort_snapshot_20260918`，5,549 个 stay。
- raw：`mimiciv_3_1_hosp.labevents`、`d_labitems`。
- derived：`mimiciv_3_1_derived.chemistry`、`bg`。
- 官方代码：`mimic-code@303d26c623dcc9c49cc0f204468d4acc2f063797`。
- 窗口：采样 `[T0,T12)`；raw 可用时间为
  `GREATEST(charttime, COALESCE(storetime, charttime)) < T12`。
- 数值匹配：绝对容差 `1e-9`。
- SQL 登记：`AUDIT_ONLY`、`allow_final_run=false`。

## 3. 已验证事实与证据

### 3.1 作业与质量门

- BigQuery dry-run：9,837,904,284 bytes，低于 20 GB 上限。
- 正式运行：退出码 0，输出 51 行 aggregate-only 结果。
- runner 状态：`passed_aggregate_qc`。
- 9 个既有合同 hard gate 全为 0。
- `precision_only` 三个概念均为 0。
- 120 的互斥原因计数逐概念与 119 `both-unequal` 完全守恒。

### 3.2 互斥原因

| 概念 | 119 both-unequal | derived 较高且命中晚回报 raw | raw 较高且乳酸 specimen 缺 PO2 | 其他/未解释 |
| --- | ---: | ---: | ---: | ---: |
| BUN | 222 | 222 | 不适用 | 0 |
| 肌酐 | 162 | 162 | 不适用 | 0 |
| 乳酸 | 136 | 10 | 126 | 0 |

- BUN 222/222 与肌酐 162/162 的 derived 最大值都能在合同正确、采样时间位于
  `[T0,T12)`、但 `storetime` 使其在 T12 后才可用的 raw 值中找到。
- 乳酸 126/136 为 raw 最大值更高，且该 raw-max specimen 没有官方 `bg.sql`
  保留 blood-gas row 所要求的同 specimen 非空 PO2（itemid 50821）。
- 乳酸另 10/136 为 derived 最大值更高且命中晚回报 raw。
- `other_quarantine`、derived 值完全不在 raw、specimen 其他缺失、聚合选择未解释和
  unresolved 均为 0。

### 3.3 非互斥 membership

| 概念 | derived max 在任意 raw | derived max 在 eligible raw | derived max 在晚回报 raw | raw max 在 derived 事件集 |
| --- | ---: | ---: | ---: | ---: |
| BUN | 222 | 0 | 222 | 222 |
| 肌酐 | 162 | 0 | 162 | 162 |
| 乳酸 | 136 | 125 | 11 | 9 |

membership 可重叠，不能横向相加。乳酸晚回报 membership 为 11，而互斥的
`derived_higher_matches_late_raw` 为 10，是因为其中 1 个 stay 的方向为 raw-higher，
按预设优先级归入 raw-max specimen 缺 PO2。

## 4. 判断与影响

结论一：本项目若直接用 derived `chemistry` 的 T12 前 `charttime` 最大值，会把当时
尚未由 `storetime` 证明可用的 BUN/肌酐结果纳入预测特征。BUN 和肌酐应继续以 raw
合同层及可用时间门控为主，derived 只用于对账。

结论二：`bg.lactate` 是带同 specimen PO2 条件的 blood-gas 子集。合同正确且按时
可用的 raw 血乳酸即使不出现在 `bg`，也不能据此认定为污染值或自动删除；否则会把
官方派生选择条件误当成 raw 数据质量问题。

这两点已写入本地 MIMIC cleaning skill 的 derived reconciliation 参考，并由无患者
数据 fixture 锁定。该 skill 是内部清洗护栏，不是论文正文内容。

## 5. 新增或确认的研究决策

- 新增 120，只做 aggregate-only 第二层分解；119 保持历史不变。
- BUN/肌酐 T12 特征继续强制 raw `storetime` 可用性，不以 derived 覆盖率替代。
- 乳酸 raw-vs-derived 对账必须先检查同 specimen PO2 条件；缺 PO2 不等于 raw 污染。
- 无证据的差异必须保留为 unresolved，不根据范围、方向或模型表现猜测。
- 规则知识保持 `proposed`/审计用途，不自动晋级 `ACTIVE`。

## 6. 未决问题、阻塞项和假设

- 本轮只分解 119 的 `both-unequal` max；乳酸 549 个 raw-only stay 尚未做同样的
  PO2/官方选择条件聚合分解。
- delta、first/last 与最终特征合同仍需在正式特征冻结后独立验证。
- 乳酸 reconstruction 只复现了与本问题直接相关的 itemid、上限和同 specimen PO2
  条件，不宣称复制整个 `bg.sql`。
- v3.3 完整上游依赖、表型、风险集与结局仍未冻结，正式路径继续 fail-closed。

## 7. 下一步动作

1. 新增版本化 aggregate-only 审计，分解乳酸 549 个 raw-only stay 是否主要由同
   specimen PO2 条件解释。
2. 将 raw 可用时间与 derived reconciliation 规则接入最终实验室特征冻结检查。
3. 在论文撰写前按权威清单逐一复核完整代码链、版本、输入指纹和 QC 证据。

## 8. 本轮修改文件

- `docs/superpowers/specs/2026-09-20-mimic-bigquery-unequal-decomposition-design.md`
- `sql_v3_3/bigquery/audits/120_audit_raw_vs_derived_unequal_phase_c_bq.sql`
- `project_control/bigquery/run_mimic_raw_derived_unequal_bq.py`
- `project_control/bigquery/tests/test_mimic_lab_phase_c_bq.py`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/audits/bigquery_raw_derived_unequal_20260920/run.json`
- `project_control/audits/bigquery_raw_derived_unequal_20260920/aggregate_qc.csv`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/SKILL.md`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/derived-reconciliation.md`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/scripts/test_fixtures.py`
- `project_control/task_reports/TASK_REPORT_20260920_MIMIC_BIGQUERY_UNEQUAL_DECOMPOSITION.md`
- `project_control/task_reports/README.md`

## 9. 可重复性信息

- 本机正式运行目录：
  `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/mimic_raw_derived_unequal_20260920_01/`
- 可提交脱敏证据目录：
  `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/bigquery_raw_derived_unequal_20260920/`
- SQL 模板 SHA-256：`a7615af3a5a3a360d5f34fcc1e95c1e6a75f99b2d003437f9301f452c7ae2cfd`。
- 执行 SQL SHA-256（替换 billing project 后）：
  `e76b0d225770dbe8b4b4b663a192956e9f058bd695da215fe4e6f9b6ab69c1c5`。
- runner SHA-256：`e01a950d933d233f96f1d4edb8f6321dfdfa6e4739fba9907607a2c4a560ddaa`。
- 规则包 SHA-256：`9f0fd0eca70dbd8e08ea3d17367b382154f9f961e817127443dfc9037aa1f720`。
- derived reconciliation 参考 SHA-256：
  `e206f4662d7bdd3d528b19f7ca7bb35c5786d12b0f41dfff3136f62114f73fd5`。
- 脱敏 `run.json` SHA-256：
  `56004861b03654c8abc016e81b8579d02ca5fdd62e72f68eb114b8702d0d5f5e`。
- 聚合 CSV SHA-256：
  `fb0fbd35265335580cbb3a9b4eb1950e4373f7604ec3c3601493ccde091ff663`。
- 无随机过程，不涉及 seed。
