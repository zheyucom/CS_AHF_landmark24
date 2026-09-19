# MIMIC 实验室流水线质量门阶段 A 任务报告

日期：2026-09-19

## 1. 用户问题与本轮范围

用户批准实施“当前主线修复 + 历史 SQL 不可变隔离 + 发文前全仓复现审计”。本轮只完成阶段 A：代码权威、静态质量门、依赖检查、合成失败夹具和全仓历史风险账本；未查询数据库、未读取患者级数据、未重跑队列或模型。

## 2. 使用的文件、版本和数据状态

- Git 隔离分支：`codex/mimic-lab-quality-gate-20260919`。
- MIMIC 合同版本：`lab_contract_v1.json`，适用 MIMIC-IV 3.1。
- 合同证据源：`MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql`、2026-09-18 正式执行报告及不可变 cohort 快照报告。
- 扫描输入：Git 跟踪的 167 个 SQL 文件。
- 数据状态：仅静态文本扫描，患者级数据库 `not_run`。

## 3. 已验证事实与证据

1. `PIPELINE_AUTHORITY_MANIFEST.csv` 已逐文件登记 167/167 个 Git 跟踪 SQL；遗漏 0、重复 0。
2. 初始权威状态为：`AUDIT_ONLY=36`、`LEGACY_BLOCKED=130`、`SUPERSEDED=1`、`ACTIVE=0`。
3. `start_run.py --run-class final` 已接入质量门。当前因没有任何获准的 ACTIVE SQL，会在创建运行目录前 fail-closed；不能用旧主线启动正式 run。
4. 合成回归覆盖未登记/重复清单、执行计划绕过、blocked 依赖、raw availability/unit/fluid/category/specimen 缺口、derived 正式来源、错误体液 itemid、模糊元数据、缺失补零、范围静默置空、未登记 itemid、合规 raw SQL 和 AUDIT_ONLY 对账。
5. 质量门单元测试 22/22 通过，正式入口集成测试 2/2 通过；正式执行计划中的每个 SQL 都会单独保存 SHA-256，生成的 CSV 固定使用 LF，重复扫描不会制造换行差异。
6. 全仓静态账本共有 103 条非阻断历史/审计发现：
   - `LAB_DERIVED_FORMAL_SOURCE=10`
   - availability/landmark/unit/fluid/category/specimen 合同缺口各 14
   - 未登记 itemid 3（均为历史血气审计中的 `50802`，base excess）
   - 模糊元数据纳入 1
   - 实验室范围外值 `CASE ... ELSE NULL` 静默置空 5
7. 当前阻断项显示为 0 的原因是正式允许列表为空，不代表上述历史问题已经修复；一旦相同 SQL 被提升为 ACTIVE，这些发现将变成硬失败。

证据文件：

- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_20260919.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_20260919.md`
- `project_control/quality_gates/mimic_lab/tests/test_quality_gate.py`
- `project_control/tests/test_start_run_quality_gate.py`

## 4. 判断与影响

阶段 A 已建立“不能误跑”的安全边界，但尚未建立“可以正式跑”的新主线。旧结论“V2 实验室审计通过即可认为旧模型 SQL 可继续使用”需要修正为：V2 审计证明了合同和污染隔离可行；旧模型/队列 SQL 仍存在 derived 绕过、结果可用时间和原值可追溯性缺口，必须在阶段 B 复制为新版本并重构后才能逐文件晋级 ACTIVE。

这使后续发文复核更可靠：历史代码和旧结果继续保留，最终论文运行只能来自明确批准的新执行链；代码、规则、输入和输出之间不会靠目录名或人工记忆维系。

## 5. 新增或确认的研究决策

1. 历史 SQL 不原地重写，统一保留并 fail-closed。
2. 当前 `sql_v3_2` 只是主线候选，不等于 ACTIVE；阶段 B 未完成前正式执行权限为零。
3. `sql_v4_2` 预设敏感性路径同样必须通过相同实验室质量门。
4. raw 是正式实验室事实源；derived 只允许审计/覆盖对账或预先登记的敏感性分析。
5. `50802` 不因在旧 SQL 中出现而自动加入 active 规则包；需先完成概念、fluid、category、unit、时间、重复和用途核验，再走规则生命周期。

## 6. 未决问题、阻塞项和假设

- 阶段 B 尚未实施：raw 合同层、eligible/quarantine 分流、正式 rollup、新版主线 SQL 和数据库级 QC 均未运行。
- 当前扫描器是保守静态规则，不替代 Postgres/BigQuery 解析器或实际数据库执行；语法、表权限和聚合计数仍需数据库验证。
- 仓库原有 `phase2_edit/.../test_fixtures.py` 在本轮开始前就缺少对应实现和规则包；其基线结果为 13 项中 1 通过、9 失败、3 错误。该遗留缺口不属于本轮新质量门，但需另行整理或补齐，不能伪报全仓测试全部通过。
- 最终 DHF 表型、T12 风险集、三态结局和正式模型仍未冻结。

## 7. 下一步动作

1. 阶段 B 先建立版本化 raw `lab_contract → classified → quarantine/eligible → rollup` SQL。
2. 优先复制并替代 `090B_create_compact_predictors_v33.sql` 及 NT-proBNP 表型链，不修改历史原件。
3. 对乳酸、BUN、肌酐、pH、base excess、电解质、血常规、INR、NT-proBNP 和 Troponin T 逐概念补齐合同与失败夹具；未核验概念保持 quarantine/blocked。
4. 在授权数据库中执行 Postgres/BigQuery 语法、计数、raw/derived 覆盖、late、wrong-fluid、unknown-unit 和 duplicate QC 后，才逐文件晋级 ACTIVE。

## 8. 本轮修改文件

- `docs/superpowers/specs/2026-09-19-mimic-lab-pipeline-quality-gate-design.md`
- `docs/superpowers/plans/2026-09-19-mimic-lab-pipeline-quality-gate-implementation.md`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/quality_gates/mimic_lab/README.md`
- `project_control/quality_gates/mimic_lab/quality_gate.py`
- `project_control/quality_gates/mimic_lab/lab_contract_v1.json`
- `project_control/quality_gates/mimic_lab/finding_schema.json`
- `project_control/quality_gates/mimic_lab/tests/test_quality_gate.py`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_20260919.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_20260919.md`
- `project_control/tests/test_start_run_quality_gate.py`
- `project_control/start_run.py`
- `project_control/RESEARCH_DASHBOARD.md`
- `project_control/task_reports/README.md`
- `project_control/task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_QUALITY_GATE_PHASE_A.md`

## 9. 可重复性信息

核心命令：

```bash
python3 project_control/quality_gates/mimic_lab/tests/test_quality_gate.py
python3 project_control/tests/test_start_run_quality_gate.py
python3 project_control/quality_gates/mimic_lab/quality_gate.py check \
  --project-root . \
  --manifest project_control/PIPELINE_AUTHORITY_MANIFEST.csv \
  --contract project_control/quality_gates/mimic_lab/lab_contract_v1.json \
  --report-csv project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_20260919.csv \
  --summary-md project_control/quality_gates/mimic_lab/reports/sql_risk_summary_20260919.md
```

合成测试无随机过程；未设置 seed。最终提交 SHA 和远端核验结果在提交推送后补记于 Git 历史和交付回报，不在提交前预填。
