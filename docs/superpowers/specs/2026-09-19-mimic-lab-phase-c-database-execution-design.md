# MIMIC 实验室流水线阶段 C：数据库执行与差异审计设计

日期：2026-09-19

## 目标与边界

阶段 C 把阶段 B 的静态 SQL 候选放入本机 PostgreSQL `mimiciv31` 实际执行，验证 raw 合同层、下游 NT-proBNP/乳酸/建模路径及其与历史 derived 路径的差异。阶段 C 不改变既定队列、时间窗、阈值、变量或结局定义，不冻结最终论文结果。

数据库写入仅限版本化 schema `study_ahf_v3_3`。源 schema `mimiciv_hosp`、`mimiciv_icu`、`mimiciv_derived` 和历史 `study_ahf_v3_2` 只读；历史 SQL 和历史表不改写。

## 已核实执行环境

- 本机数据库：PostgreSQL 12.18，database=`mimiciv31`，user=`postgres`。
- `transaction_read_only=off`，对新 schema 具备创建权限。
- `study_ahf_v3_2` 有 34 张既有表；`study_ahf_v3_3` 初始不存在。
- 数据库约 141 GB，`mimiciv_hosp.labevents` 约 27 GB，数据卷可用空间约 580 GiB。
- 连接入口：`/Library/PostgreSQL/12/bin/psql -X -w -h localhost -U postgres -d mimiciv31`。

## 方案选择

### 方案 A：全库合同层物化（采用）

对合同 itemid 与已知错误体液 itemid 的全部 `labevents` 建立 classified/eligible 表，再由项目 episode 消费。

优点：一次物化后可复用；wrong-fluid、late、unknown-unit、duplicate 和删失边界都可全库审计。缺点：首次运行较慢，占用较多磁盘。

### 方案 B：仅项目 episode 物化（回退方案）

只处理当前候选住院与时间窗。速度快，但无法证明全库合同逻辑完整，也较难推广到其他 MIMIC 项目。仅在全库方案因资源约束失败时启用，并必须另行版本化，不能静默替代方案 A。

### 方案 C：BigQuery 运行后导回聚合值（不采用）

不能验证 PostgreSQL SQL、权限、索引及下游依赖，因此只保留为独立 parity 审计来源。

## 执行组件

1. `project_control/database/mimic_lab_phase_c.py`
   - 预检数据库身份、版本、schema 和所需源表；
   - 读取固定顺序的 SQL 计划，记录每个文件 SHA-256；
   - 使用 `psql -X -w -v ON_ERROR_STOP=1`，单文件失败即停链；
   - 保存结构化 JSON 运行记录和纯文本日志；
   - 不接受命令行密码，不输出凭据。
2. `sql_v3_3/audits/116_audit_raw_lab_contract_phase_c.sql`
   - 核对 classified/eligible 行数、隔离原因、单位、反向时间、重复 specimen、删失和范围标志；
   - 硬门：eligible 中错误体液、未知单位、反向时间、缺 specimen、重复 specimen 必须为 0。
3. `sql_v3_3/audits/117_audit_raw_vs_derived_phase_c.sql`
   - 在同一历史建模 base 和 `[T0,T12)` 窗口比较 raw 与旧 derived 的可用率、值差异、迟到结果及特征差异；
   - 仅输出聚合结果，不提交患者级数据。
4. `project_control/database/runs/<run_id>/`
   - 保存 `run.json`、`execution.log`、`qc/*.csv` 和 SQL 哈希；
   - 只提交小型聚合 QC 与元数据，不提交患者标识或患者级结果。

## 执行顺序和门控

```text
数据库/源表预检
→ 060 raw 合同层
→ 116 合同层硬门 QC
→ 061A NT-proBNP
→ 061C pre-T12 乳酸
→ 061E post-T12 乳酸结局
→ 063A 候选结局
→ 090B 45 变量
→ 117 raw-vs-derived 聚合审计
```

任一步失败时：停止后续步骤、保存退出码与日志、状态标记 `failed` 或 `blocked`，不修改权威状态。只有数据库执行、聚合 QC、完整依赖链和复现性记录均通过后，才另行评估 `ACTIVE`；阶段 C 本身不自动晋级。

## 测试策略

- 测试先行验证：连接参数不含密码、SQL 顺序固定、SHA-256 可复算、失败即停、运行记录原子写入、QC 硬门失败会阻断下游。
- 用临时假 `psql` 测试 runner，不依赖患者数据。
- 6 个阶段 B SQL 继续通过 PostgreSQL parser。
- 实际数据库执行后检查表存在、主键粒度、行数、eligible 不变量和 episode 多匹配。
- raw/derived 差异必须按预设指标报告；不因差异方向调整合同。

## 隐私、复现性与交付路径

- Git 中只保存 aggregate QC、SQL、日志摘要、版本、哈希与任务报告。
- 患者级表只留在本机 PostgreSQL，不导出到仓库。
- 每次交付同时报告：本机完整绝对路径、仓库相对路径、Git SHA。
- 本项目的本机绝对路径根固定为 `/Users/zheyu/Desktop/CS_AHF_landmark24/`。

## 完成定义

阶段 C 只有在以下条件同时满足时才可称为完成：

1. runner 回归测试和既有质量门全部通过；
2. 所有实际执行 SQL 的 SHA、顺序、数据库版本和退出码已记录；
3. 060 与 116 实际运行并通过硬门；
4. 可满足依赖的下游 SQL 已实际运行，不能运行的项目明确标记；
5. 117 聚合差异审计生成且研究解释不越界；
6. 任务报告和研究看板更新；
7. Git 提交推送后，本地与远端 SHA 一致。
