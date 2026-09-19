# MIMIC 实验室流水线阶段 C：PostgreSQL 执行与差异审计

日期：2026-09-19

## 1. 用户问题与本轮范围

用户授权直接实施阶段 C，并要求实验室清洗逻辑可验证、可复现、能主动发现遗漏。本轮在本机 PostgreSQL `mimiciv31` 实际执行阶段 B 的 raw 合同层和下游路径，新增 fail-closed 合同审计、raw-vs-derived 聚合差异审计及可复现 runner。历史 SQL 未改写，患者级结果未导出或提交。

## 2. 使用的文件、版本和数据状态

- 数据库：PostgreSQL 12.18，database=`mimiciv31`，user=`postgres`，`transaction_read_only=off`。
- 数据源：MIMIC-IV v3.1 本机 PostgreSQL；raw `mimiciv_hosp.labevents`/`d_labitems` 为实验室权威来源。
- 执行工作树：`/Users/zheyu/Desktop/CS_AHF_landmark24/.worktrees/mimic-lab-phase-c/`。
- 主运行记录：`project_control/database/runs/phase_c_20260919_02/`。
- 修复后恢复运行：`project_control/database/runs/phase_c_20260919_03_resume_063a/`。
- 聚合 QC：`project_control/database/runs/phase_c_20260919_03_resume_063a/qc/lab_contract_qc.csv` 与 `raw_vs_derived_qc.csv`。

## 3. 已验证事实与证据

### 3.1 raw 合同层与 116 硬门

- `lab_event_classified_v1`：37,778,198 行。
- `lab_eligible_v1`：37,732,919 行；差额 45,279 行等于已隔离的 44,924 条错误体液、347 条反向存储时间和 8 条未知单位记录。
- 14 个允许概念和 8 个 BUN 错误体液 itemid 均与合同一致。
- 12 个硬门全部通过：eligible 错误体液、反向时间、缺 specimen、`specimen_id × itemid` 重复、非 INR 空单位、INR 非空单位、重复 `labevent_id`、合同 metadata 不符均为 0；classified 行数守恒差为 0。
- BUN eligible 只保留 `51006 / Blood / Chemistry / mg/dL`。错误体液分布：尿液 44,833、腹水 31、其他体液 58、胸液 2，共 44,924。
- 结果分布：exact numeric 37,445,280、missing 332,345、non-numeric text 517、右删失 51、左删失 5；官方分析范围外标志 184。范围外只影响连续分析值，不删除 raw 原值，也不解释为物理不可能。

### 3.2 下游结构检查

- 061A：22,715 行，实验室 episode 多匹配 0；NT-proBNP definitely-above-300 为 2,266，删失不确定为 0。
- 061C：6,418 行，episode 多匹配 0；pre-T12 overt-CS 候选 738。
- 061E：5,564 行，episode 多匹配 0；post-T12 overt-CS 候选 213。
- 063A：5,564 行，合同 episode 多匹配 0；乳酸确认的候选恶化 171。
- 090B：5,555 行，与建模 base 5,555 完全一致；45 个预测变量已登记，实验室 episode 多匹配 0。

以上人数和事件数仅用于结构/QC，不是冻结队列或论文结果。

### 3.3 raw-vs-derived 聚合差异

117 生成 31 条聚合审计记录，结构硬门通过：base、raw 模型和 derived 模型均为 5,555 行，实验室 episode 多匹配为 0。

| 指标 | raw 可用 | derived 可用 | derived-only | 同时可用但值不同 | 平均绝对差 | 最大绝对差 |
|---|---:|---:|---:|---:|---:|---:|
| BUN max | 4,991 | 5,133 | 142 | 222 | 0.137 | 44 |
| creatinine max | 4,993 | 5,135 | 142 | 163 | 0.006 | 0.9 |
| creatinine delta | 4,993 | 5,135 | 142 | 336 | 0.015 | 3.2 |
| lactate max | 2,909 | 2,914 | 5 | 11 | 0.002 | 2.2 |
| lactate delta | 2,909 | 2,914 | 5 | 28 | 0.007 | 2.9 |

采样在 `[T0,T12)` 但结果到 T12 后才可用的 raw 事件包括：BUN 644/7,569、creatinine 649/7,593、lactate 38/4,975、NT-proBNP 146/785。旧 derived 路径没有等价 `storetime` 可用时间门控；覆盖率和值差异与更严格的可用时间、体液、单位、删失及范围合同有关，但各原因所占比例尚未分解，不能把全部差异归因于单一规则。

### 3.4 完成前验证

- 阶段 C runner/SQL 回归 11/11、实验室质量门回归 39/39、正式入口 2/2、V2 语义审计 8/8、院内语义 11/11、标注准备 1/1、ML event merge 1/1 通过，共 73/73。
- 8 份 `sql_v3_3` SQL 通过 `pglast` parser；全仓静态质量门为 175 SQL / 175 清单 / 100 条历史或审计风险 / 0 阻断。
- 既有 `phase2_edit/.../test_fixtures.py` 空骨架仍为 1 通过、9 失败、3 错误，原因是该独立 skill 草案缺少 rule pack、`validate_rule_pack.py` 等实现文件；这不是阶段 C 回归，不能据此声称全仓测试全部通过。

## 4. 判断与影响

阶段 C 证明 raw 合同层可在 PostgreSQL 全库实际运行，BUN 错误体液会被自动隔离，且下游行数和 episode 粒度保持稳定。最直接的新帮助是确认旧 derived 路径存在真实的可用时间差异：若仅按采样时间纳入，部分 T12 后才可得结果可能进入 T12 模型，形成信息可用性偏倚。

raw 与 derived 的最大值差异中，BUN max 最大绝对差 44、lactate max 2.2，需要在正式冻结前按 episode 做受控、患者本地的原因分类审计；不能因差异方向或模型表现调整合同。

## 5. 新增或确认的研究决策

- raw 合同和数据库 QC 已通过，但不自动晋级 `ACTIVE`；完整 v3.3 依赖链、DHF 表型、结局及特征仍未冻结。
- 063A 的 raw 重算字段使用 `*_contract_*`/`overlap_*` 命名，不覆盖同表中的历史 derived 字段，便于并列审计。
- BUN 只允许血液 51006；错误体液、反向时间、单位不符、重复 specimen 均 fail-closed。
- `storetime` 决定结果可用性；删失结果只用于单向阈值确定，不进入连续 rollup。

## 6. 未决问题、阻塞项和假设

- `LEGACY_BLOCKED` 保留：新 SQL 仍消费部分 `study_ahf_v3_2` 上游表，完整 v3.3 传递依赖尚未复制和晋级。
- `phase2_edit` 中拟议的通用 MIMIC 清洗 skill 尚未完成实现，其失败夹具需在独立 skill 阶段按测试先行补齐。
- 117 只给出聚合差异；BUN/creatinine/lactate 的 derived-only 和值差异尚未按原因分解。
- 061C/061E/063A 的候选结局尚未经过正式表型、可观察性和临床定义冻结。
- 阶段 C 不包含最终模型拟合、性能估计或论文结果冻结。

## 7. 下一步动作

1. 对 BUN、creatinine、lactate 的差异 episode 做患者本地原因分层：迟到结果、范围标志、删失、单位、重复和 derived 聚合口径分别计数，只提交聚合结果。
2. 补齐 v3.3 上游依赖，并为每个晋级候选建立数据库硬门；在此之前保持 `allow_final_run=false`。
3. 完成 DHF 表型、T12 风险集和三态结局冻结后，用同一冻结 run 重建 45 变量数据集和最终模型。

## 8. 本轮修改文件

- `project_control/database/mimic_lab_phase_c.py`
- `project_control/database/tests/test_mimic_lab_phase_c.py`
- `project_control/database/runs/phase_c_20260919_01/`
- `project_control/database/runs/phase_c_20260919_02/`
- `project_control/database/runs/phase_c_20260919_03_resume_063a/`
- `sql_v3_3/audits/116_audit_raw_lab_contract_phase_c.sql`
- `sql_v3_3/audits/117_audit_raw_vs_derived_phase_c.sql`
- `sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v2.sql`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_phase_c_20260919.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_phase_c_20260919.md`
- `project_control/RESEARCH_DASHBOARD.md`
- `project_control/task_reports/README.md`
- `project_control/task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_PHASE_C.md`

## 9. 可重复性信息

- 主运行：`phase_c_20260919_02`，2026-09-19T14:44:51Z 至 15:07:37Z。060、116、061A、061C、061E 通过；063A 因历史字段重名 fail-closed，090B/117 未运行。
- 恢复运行：`phase_c_20260919_03_resume_063a`，15:12:00Z 至 15:12:41Z。修复后的 063A、090B、117 全部通过并导出聚合 QC。
- 初次运行：`phase_c_20260919_01` 因本机执行通道 300 秒时限中断；对应 PostgreSQL 孤立事务已精确终止并回滚，未留下半成品。
- 修复后 SHA-256：063A=`99e5bd01e752c77c0d81b1f710967c542ffa752f9320fb259998b24d15969966`；090B=`e2b320a2fcf686aa8653c078c4daf553e6a188bd451a589cb6003a1feab71923`；117=`161d09275c04a7199b7e817302274145e10d9b12610f2fd6f9b5f401e797be0a`。其余 SQL 哈希、退出码和时间见各 `run.json`。
- runner 固定使用 `psql -X -w -v ON_ERROR_STOP=1 --single-transaction`；不接受命令行密码。
