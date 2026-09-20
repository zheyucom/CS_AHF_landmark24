# MIMIC lactate raw-only：BigQuery 聚合原因分解

日期：2026-09-20

## 1. 用户问题与本轮范围

本轮继续分解 119 审计中 549 个 lactate stay-level max `raw-only` stay，判断
公开 derived `bg.lactate` 缺失是否由同 specimen PO2、官方乳酸范围、blood-gas
specimen 聚合时间窗或公开表不一致造成。

本轮新增版本化 121 审计，不修改 119/120，不创建患者级永久表，不导出
subject/hadm/stay/labevent/specimen 标识，不因 derived 缺失删除 raw 乳酸，也不将
内部 QC 数字作为论文结果。

## 2. 使用的文件、版本和数据状态

- MIMIC-IV：3.1。
- cohort：不可变 `dhf_lab_audit_cohort_snapshot_20260918`，5,549 个 stay。
- raw：`mimiciv_3_1_hosp.labevents`、`d_labitems`。
- derived：`mimiciv_3_1_derived.bg`。
- 官方代码：`mimic-code@303d26c623dcc9c49cc0f204468d4acc2f063797`。
- raw 窗口：采样 `[T0,T12)`；可用时间
  `GREATEST(charttime, COALESCE(storetime, charttime)) < T12`。
- derived 重建：按官方完整 blood-gas itemid 集合和 `specimen_id` 聚合，使用
  `MAX(charttime)`；乳酸 itemid 50813、`valuenum <= 10000`，并要求同 specimen
  PO2 itemid 50821 非空。
- SQL 权威状态：`AUDIT_ONLY`、`allow_final_run=false`。

## 3. 已验证事实与证据

### 3.1 作业与质量门

- BigQuery dry-run：9,628,527,308 bytes，低于 20 GB 上限。
- 正式运行：退出码 0，输出 22 行 aggregate-only 结果。
- runner 状态：`passed_aggregate_qc`。
- 119 的 lactate `raw-only` 参考数严格复现为 549。
- 既有 9 个实验室合同 hard gate 和新增结构门均为 0。
- 五类互斥原因合计为 549，无 unresolved。

### 3.2 互斥原因

| 原因 | stay 数 | raw max 均值 | raw max 最大值 |
| --- | ---: | ---: | ---: |
| 所有 lactate specimen 均无非空 PO2 | 549 | 1.9325 | 10.4 |
| 有 PO2 但乳酸均超官方范围 | 0 | — | — |
| 窗口内官方候选不在公开 `bg` | 0 | — | — |
| 官方候选聚合时间全部移至 T12 后 | 0 | — | — |
| 未解释 | 0 | — | — |

结论为 549/549：这些 stay 的 lactate specimen 均没有同 specimen 非空 PO2，
因此官方 `bg.sql` 在 `WHERE bg.po2 IS NOT NULL` 阶段不保留对应 blood-gas row。

### 3.3 非互斥 membership

以下六类 membership 均为 0：raw-max specimen 有 PO2、任一 lactate specimen
有 PO2、任一官方 BG 候选、候选时间在窗口内、候选时间在 T12 后、候选能在公开
`bg` 任意时间匹配。结果排除了官方乳酸上限、`MAX(charttime)` 窗口偏移和公开表
漂移作为这 549 个 stay 的解释。

## 4. 判断与影响

derived `bg.lactate` 缺失是官方 blood-gas 派生表的 PO2 条件所导致的选择差异，
不是 raw 乳酸的污染证据。合同正确、按 T12 可用的 raw 血乳酸不能因不在 `bg`
中就被删除或设为缺失。

结合 120：另有 126 个 both-unequal stay 的 raw 最大乳酸 specimen 同样缺 PO2。
119 的 coverage 类别互斥，因此共有 675 个不同 stay 的 raw/derived 差异与这一
PO2 条件有关。该数字只描述固定审计快照，不是论文结论。

当前修订后的 v3.3 主线已经使用 raw `labevents` 合同层，方向正确；本轮不需要
为追求与 derived `bg` 一致而修改 raw 特征。历史 derived-only 路径继续保持 blocked。

## 5. 新增或确认的研究决策

- lactate 项目特征继续以 raw itemid 50813 的精确合同和可用时间为准。
- `bg.lactate` 只用于对账，不作为 raw 血乳酸完整真值或污染判定器。
- raw-only 必须先解释官方派生选择条件；不能自动等同于错误、异常或应删除数据。
- 121 保持 `AUDIT_ONLY`，不自动晋级正式执行入口。
- MIMIC skill 已追加 549/549 finding，并由 patient-free fixture 锁定。

## 6. 未决问题、阻塞项和假设

- 本轮只验证 lactate max 的 raw-only；delta、first/last 仍需随最终特征合同验证。
- 本轮重建官方 BG 中影响 lactate 存在性和时间窗的字段，没有复制与乳酸存在性无关的
  SpO2、FiO2 和 A–aDO2 派生。
- v3.3 完整上游依赖、表型、T12 风险集与结局尚未冻结，正式路径继续 fail-closed。
- 其他实验室、尿量、药物和生命体征仍需各自的来源与时间合同，不能直接套用乳酸规则。

## 7. 下一步动作

1. 将 119–121 的结论整理为最终实验室特征来源决策矩阵：raw 主源、derived 对账、
   可用时间、范围和缺失解释。
2. 对最终使用的 max/delta/first/last 逐项复核聚合目的与时间合同。
3. 继续扫描候选主线和历史 SQL，确保没有 derived `bg` 被重新用于正式乳酸特征。

## 8. 本轮修改文件

- `docs/superpowers/specs/2026-09-20-mimic-bigquery-lactate-raw-only-decomposition-design.md`
- `sql_v3_3/bigquery/audits/121_audit_lactate_raw_only_phase_c_bq.sql`
- `project_control/bigquery/run_mimic_lactate_raw_only_bq.py`
- `project_control/bigquery/tests/test_mimic_lab_phase_c_bq.py`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/audits/bigquery_lactate_raw_only_20260920/run.json`
- `project_control/audits/bigquery_lactate_raw_only_20260920/aggregate_qc.csv`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/derived-reconciliation.md`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/scripts/test_fixtures.py`
- `project_control/task_reports/TASK_REPORT_20260920_MIMIC_BIGQUERY_LACTATE_RAW_ONLY.md`
- `project_control/task_reports/README.md`

## 9. 可重复性信息

- 本机正式运行目录：
  `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/mimic_lactate_raw_only_20260920_01/`
- 可提交脱敏证据目录：
  `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/bigquery_lactate_raw_only_20260920/`
- SQL 模板 SHA-256：`5c9093db09d06b608fdd4b31a97a34f966fd44431523696d96e912617961d756`。
- 执行 SQL SHA-256（替换 billing project 后）：
  `adc52bd7a9e28b5d680ecbeddb4ab892238b9d0bb8b49c993c46751ceeb2d181`。
- runner SHA-256：`5383dbb4f49fea1968265ac4770a84a969cf8cd53ec55cfb39b5a332cf4efff4`。
- 规则包 SHA-256：`9f0fd0eca70dbd8e08ea3d17367b382154f9f961e817127443dfc9037aa1f720`。
- derived reconciliation 参考 SHA-256：
  `35df6442c565b0ab93c2b0df6cba2d908a81dd7aa13e36b88d89166728e81385`。
- 脱敏 `run.json` SHA-256：
  `16769caf367bb0f0e3c701a1bdb6c06492abfc70fd862eafe8fd05386cb60ea5`。
- 聚合 CSV SHA-256：
  `946456ec206a8b135b24d427e9be555d3426d91d25ab2687c793aa3ea6584ab6`。
- 无随机过程，不涉及 seed。
