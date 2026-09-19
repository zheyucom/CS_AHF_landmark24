# MIMIC 实验室流水线阶段 B 任务报告

日期：2026-09-19

## 1. 用户问题与本轮范围

用户授权直接实施阶段 B，并要求清洗逻辑严谨、可追溯、可复现。本轮建立版本化 raw 实验室合同层，复制修订 NT-proBNP、乳酸结局及 45 变量建模路径；不原地修改历史 SQL，不重跑或冻结最终研究队列和模型。

## 2. 使用的文件、版本和数据状态

- Git 工作分支：`codex/mimic-lab-phase-b-20260919`，起点 `319cf0979d01a1cf6ad2514345e761e0751a84ec`。
- 数据字典：MIMIC-IV v3.1 `d_labitems`，BigQuery `physionet-data.mimiciv_3_1_hosp`。
- 官方方法：`mimic-code` commit `303d26c623dcc9c49cc0f204468d4acc2f063797` 的 `bg.sql`、`chemistry.sql`、`complete_blood_count.sql`、`coagulation.sql`。
- PostgreSQL：本机无 `psql`、无连接配置；患者级建表与结果 QC 为 `not_run`。
- BigQuery：只执行聚合 QC，不导出患者级数据。

## 3. 已验证事实与证据

### 3.1 合同与 SQL

- 正式合同覆盖 14 个实验室概念，其中项目下游使用 13 个：base excess、lactate、pH、bicarbonate、creatinine、NT-proBNP、potassium、sodium、BUN、hemoglobin、INR、platelet、WBC；另保留 troponin T 合同。
- BUN 正式纳入仅允许 `51006 / Urea Nitrogen / Blood / Chemistry / mg/dL`；8 个尿液、腹水、CSF、关节液、胸液、粪便或其他体液 itemid 进入明确隔离表。
- INR `51237` 为无量纲结果，MIMIC v3.1 中单位为空是字典内正常形态；仅该精确合同允许 `dimensionless_null`，其他空单位继续隔离。
- `availability_time = GREATEST(charttime, COALESCE(storetime, charttime))`；`storetime < charttime`、缺 specimen、`specimen_id × itemid` 重复、metadata/单位不符均明确隔离。
- 原始 `value/valuenum/valueuom`、上下界、删失类型、参考范围、flag、priority 和 comments 全部保留；连续特征只用 exact numeric `analysis_value`。
- 官方范围仅用于 `outside_official_analysis_range` 标志和连续分析排除；原值不删除，也不称其为“物理不可能”。pH、base excess、INR 没有自行添加范围。
- NT-proBNP 300/900/1800 阈值均支持 definitely above / definitely below / indeterminate censored；`>x/<x/区间` 不被伪装为精确值。
- 所有修订路径同时限制采样时间 `charttime` 与结果可用时间 `availability_time`，并审计一个 lab event 是否匹配多个研究 episode。

### 3.2 测试与静态质量门

- 新增阶段 B 回归测试先红后绿；最终阶段 A+B 质量门测试 39/39 通过。
- 6 个新 PostgreSQL SQL 均通过 `pglast 7.10` parser。
- 全仓静态质量门：173/173 个 Git 跟踪 SQL 已登记，0 个阻断项；100 条仍属于历史/审计风险，不代表历史 SQL 已修复。
- 正式入口仍为 fail-closed：`ACTIVE=0`，新 SQL 全部为 `LEGACY_BLOCKED`、`allow_final_run=false`。
- 既有验证：正式入口 2/2、V2 实验室审计 8/8、院内语义 11/11、标注准备 1/1、ML event merge 1/1 通过。ML 测试须在项目目录使用 `PYTHONPATH=src`；首次从仓库根运行的 import 失败是调用路径问题，不是代码回归。

### 3.3 BigQuery 聚合 QC

作业：`phase_b_lab_contract_aggregate_qc_20260919`，位置 `US`，状态 `DONE`，`cacheHit=false`。

- 扫描合同及已知错误体液 itemid：37,778,198 行。
- 已知错误体液 BUN：44,924 行，应隔离。
- `storetime < charttime`：347 行，应隔离。
- `specimen_id × itemid` 重复：0 行。
- INR 空单位：1,783,315 行，符合无量纲例外。
- 非 INR 空单位：8 行，应隔离。
- 右删失字符串：51 行；左删失字符串：5 行；`valuenum` 空但原始 value 非空：573 行。
- 处理字节 7,665,139,499，计费字节 7,666,139,136。

这些是源数据聚合事实，不等于 PostgreSQL 新合同层已经建表成功。

## 4. 判断与影响

阶段 B 已把“研究者提醒后才发现错误体液”转为可执行、会自动失败的合同和回归测试。旧 SQL 仍保留用于追溯，但 formal pipeline 不再应直接消费 derived laboratory 表或仅按 `charttime` 划窗。

本轮同时发现并修正两个容易隐蔽的逻辑风险：

1. NT-proBNP 900/1800 不能继续只依赖 exact maximum，否则明确 `>900` 的删失值会被误判；三个阈值现统一使用三态逻辑。
2. 结局路径的持续血管活性药必须按“输注区间是否与 pre/post 窗重叠”分别计算；不能只按 starttime 分组，否则跨 T12 持续输注会被错误归到单侧窗口。

## 5. 新增或确认的研究决策

- 历史 SQL 不原地重写；新实现统一进入 `sql_v3_3`。
- raw 原值与隔离原因永久保留；只有 exact numeric 且通过合同/官方分析范围的结果进入连续 rollup。
- 比较符号结果可用于单向确定的阈值分类，但不用于均值、最大值、最小值、delta 等连续特征。
- PostgreSQL 数据库实际执行和 episode/行数对账未完成前，任何新 SQL 都不得晋级 ACTIVE。
- BigQuery 聚合核验不替代 PostgreSQL 正式实现的执行验证。

## 6. 未决问题、阻塞项和假设

- `not_run`：PostgreSQL raw 层、下游 v2/v34 SQL 的实际建表、行数、唯一性、episode 多匹配、缺失率和新旧差异对账。
- `blocked`：完整上游 v3.3 主线尚未复制/晋级，新 SQL 仍依赖 `sql_v3_2` blocked 表；正式运行必须继续拒绝。
- `pending`：为 BigQuery 与 PostgreSQL 两套实现做同一批 aggregate parity QC；随后才评估是否逐文件晋级。
- 阶段 A 已登记的 `phase2_edit/.../test_fixtures.py` 遗留失败本轮未改，不能描述为全仓测试全部通过。

## 7. 下一步动作

1. 提供或恢复可执行 PostgreSQL 环境后运行 `060 → 061A/061C/061E/063A/090B`，保存数据库版本、SQL SHA-256、运行日志与聚合 QC。
2. 对比 raw 与历史 derived 的覆盖、迟到结果、单位/体液隔离、特征缺失及事件数变化；差异逐项解释，不以结果好坏调整合同。
3. 补齐 v3.3 传递依赖链和正式执行顺序；仅在依赖、数据库 QC 和冻结门控都通过后晋级 ACTIVE。

## 8. 本轮修改文件

- `docs/superpowers/plans/2026-09-19-mimic-lab-pipeline-phase-b.md`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/quality_gates/mimic_lab/lab_contract_v1.json`
- `project_control/quality_gates/mimic_lab/quality_gate.py`
- `project_control/quality_gates/mimic_lab/tests/test_quality_gate.py`
- `project_control/quality_gates/mimic_lab/tests/test_phase_b_sql_contract.py`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_phase_b_20260919.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_phase_b_20260919.md`
- `sql_v3_3/executable/060_create_raw_lab_contract_layer_v1.sql`
- `sql_v3_3/executable/061A_create_ahf_evidence_table_12h_v2.sql`
- `sql_v3_3/executable/061C_create_pre12_overt_cs_flags_v2.sql`
- `sql_v3_3/executable/061E_create_post12_overt_cs_future48h_v2.sql`
- `sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql`
- `sql_v3_3/modeling/090B_create_compact_predictors_v34.sql`
- `project_control/RESEARCH_DASHBOARD.md`
- `project_control/task_reports/README.md`
- `project_control/task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_PHASE_B.md`

## 9. 可重复性信息

核心命令：

```bash
python -m unittest discover -s project_control/quality_gates/mimic_lab/tests -v
python project_control/quality_gates/mimic_lab/quality_gate.py check \
  --project-root . \
  --manifest project_control/PIPELINE_AUTHORITY_MANIFEST.csv \
  --contract project_control/quality_gates/mimic_lab/lab_contract_v1.json \
  --report-csv project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_phase_b_20260919.csv \
  --summary-md project_control/quality_gates/mimic_lab/reports/sql_risk_summary_phase_b_20260919.md
python -c "from pathlib import Path; from pglast import parse_sql; [parse_sql(p.read_text()) for p in Path('sql_v3_3').rglob('*.sql')]"
```

BigQuery 聚合作业记录已保存在服务端 job metadata；本仓库不保存患者级输出。最终提交和远端 SHA 由推送后核验结果确定。
