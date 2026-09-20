# MIMIC BigQuery Phase-C 最小聚合审计设计

日期：2026-09-20

## 目标与边界

将 PostgreSQL Phase-C 中已验证的实验室合同，适配成 BigQuery Standard SQL 的 cohort-scoped 聚合审计。审计队列固定为 `ahf_work.dhf_lab_audit_cohort_snapshot_20260918` 的 5,549 个有效 stay。输出不得含 `subject_id`、`hadm_id`、`stay_id`、`labevent_id` 或 `specimen_id`，不得生成患者级永久表，也不得把结果解释为冻结队列或论文最终结果。

## 方案比较与决定

采用聚合-only 方案：查询 PhysioNet MIMIC-IV 3.1 的 `labevents` 与 `d_labitems`，按不可变 cohort 的 `subject_id × hadm_id` 和 `[intime, intime+12h)` 采样窗选择候选，并以 `GREATEST(charttime, COALESCE(storetime, charttime)) < intime+12h` 判定结果在 landmark 前可用。

不采用完整患者级合同层镜像，因为本地 PostgreSQL 已完成逐行 Phase-C 验证；BigQuery 当前任务只需独立复核 cohort 范围内的聚合门控。也不只重复旧 6 概念审计，因为 Phase-C 合同有 14 个允许概念和 8 个 BUN 错误体液 itemid。

## 组成

1. `sql_v3_3/bigquery/audits/118_audit_raw_lab_contract_phase_c_bq.sql`
   - BigQuery Standard SQL。
   - 使用 `YOUR_BILLING_PROJECT` 占位符引用 cohort 快照。
   - 以 CTE 声明 14 个精确 allow 合同和 8 个 BUN quarantine itemid。
   - 保留 raw 值、单位、字典 metadata、charttime/storetime、specimen 和重复计数仅用于查询内部分类。
   - 最终仅返回 `check_group/concept/reason_code/row_count` 等聚合列。

2. `project_control/bigquery/run_mimic_lab_phase_c_bq.py`
   - 从本机 gcloud 配置读取作业项目，但不记录活动账号、token 或凭据。
   - 将 SQL 中唯一允许的项目占位符替换为已配置项目。
   - 先执行 dry-run 并拒绝超过 20 GB 的查询。
   - 正式运行只将聚合 CSV、匿名化运行 JSON 和 stderr 日志写入忽略目录。
   - 运行记录包含 SQL SHA-256、规则包 SHA-256、作业项目是否已配置、MIMIC release、字节数、退出码和状态；不含患者 ID 或密钥。

3. `project_control/bigquery/tests/test_mimic_lab_phase_c_bq.py`
   - 先测试文件存在、SQL 为 BigQuery 方言、输出投影不含患者标识、14+8 合同完整、时间与重复规则存在。
   - 测试 runner 的占位符替换、命令参数、20 GB 上限、无凭据字段和失败即停止。

## 数据流

不可变 cohort 快照 → 精确 itemid 候选 → 字典/单位/时间/specimen/重复分类 → cohort 与概念级聚合 → 本地 CSV/JSON 审计工件。

不会创建 `_script` 临时数据集，不会写 `ahf_work` 患者级表，不会导出任何患者级样例。字典查询和聚合执行均使用个人项目创建查询作业，源表仍为 `physionet-data.mimiciv_3_1_hosp`。

## 失败处理

- 未配置作业项目、bq 不存在、占位符残留、dry-run 失败或估算超过 20 GB：状态为 `not_run`，不执行正式查询。
- PhysioNet 表 `Access Denied`：状态为 `not_run_access_denied`。
- 查询成功但任一硬门计数非零：状态为 `failed_qc`。
- 查询和硬门均通过：状态为 `passed_aggregate_qc`；该状态不等于患者级合同层已在 BigQuery 冻结。

## 成功标准

- 合成测试先失败后通过，项目现有回归保持全绿。
- BigQuery dry-run 成功且估算不超过 20 GB。
- 正式输出只包含聚合字段。
- BUN 51006 血液合同与 8 个非血液 itemid 的字典分类可复核。
- 运行记录、SQL、聚合结果和任务报告具有稳定的绝对路径与哈希。
