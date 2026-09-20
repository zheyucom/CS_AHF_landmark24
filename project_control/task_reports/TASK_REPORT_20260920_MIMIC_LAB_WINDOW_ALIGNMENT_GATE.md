# MIMIC 实验室 landmark 窗口自动对齐质量门

日期：2026-09-20

## 结论

- 已把“按 `charttime` 划分 landmark 前后实验室窗口，却未同步约束
  `availability_time`”固化为自动静态检查，不再依赖人工重复发现。
- 通用 MIMIC skill 使用 `MIMIC010`；项目质量门使用
  `LAB_WINDOW_ALIGNMENT_MISSING`。当前或未来 `ACTIVE` 工件触发时会阻断正式运行；
  历史、已替代和审计工件仅进入风险账本。
- 真实 `063A...v2.sql` 触发新规则，真实 v3 通过。历史 v2 未改写，v3 未自动晋级
  `ACTIVE`。
- 全部 181 个 Git 跟踪 SQL 扫描后，仅新增 v2 的 1 条非阻断 finding；总计
  107 条历史/审计 finding、0 blocker。

## 旧结论 → 新结论 → 修正原因

- 旧结论：扫描器能识别是否存在 availability 表达式及 landmark 比较。
- 新结论：对显式 `charttime < landmark → pre / else post` 的实验室分窗，扫描器还必须
  确认同一个 landmark 同时存在 `availability < landmark` 与
  `availability >= landmark`。
- 修正原因：全局存在 availability 终点门不等于 pre/post 子窗口对齐；旧 v2 正是因此
  让 T12 前采样、T12 后才可用的结果进入 pre 特征。

## 规则边界

候选 SQL 必须同时满足：

1. 读取 raw `labevents`，或读取 `lab_eligible[_vN]` /
   `lab_event_classified[_vN]` 合同层；
2. 明确出现 `CASE WHEN charttime < landmark THEN 'pre…' ELSE 'post…'`；
3. 对同一 landmark 缺少 availability 的 `<` 或 `>=` 任一侧。

availability 可使用合同层的 `availability_time`，也可直接使用
`GREATEST(charttime, COALESCE(storetime, charttime))`。该规则是 fail-closed 词法预检，
不替代对 CTE 数据流、窗口开闭、episode 归属和临床时间定义的人工复核。

## TDD 与验证证据

- RED：skill fixture 17 项中仅首个新增用例失败；项目质量门 25 项中仅两个新增断言失败；
  随后 BigQuery 全限定 raw 表名 fixture 也按预期先失败，证明测试确实捕获缺失行为。
- GREEN：实现后 skill 主 fixture 18/18、项目质量门 25/25 通过；包括真实 v2/v3
  对照及 ``project.dataset.labevents`` 表名。
- 可分发及本机安装 skill：主 fixture 18/18、边界 fixture 6/6、规则包校验通过，
  Codex `quick_validate.py` 返回 `Skill is valid!`。
- 项目与 skill 全量回归共 120/120 通过。
- 仓库扫描：`SQL=181 MANIFEST=181 FINDINGS=107 BLOCKERS=0`。
- 未连接患者级数据库、未导出患者级记录，也未把本轮静态扫描写成论文结果。

## 产物

- `project_control/quality_gates/mimic_lab/quality_gate.py`
- `project_control/quality_gates/mimic_lab/tests/test_quality_gate.py`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_window_alignment_20260920.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_window_alignment_20260920.md`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/`
- 本机安装目录：`/Users/zheyu/.codex/skills/mimic-iv-data-cleaning/`

`deliverables/mimic-iv-data-cleaning/` 已同步为可安装副本，但该目录按仓库既有
`.gitignore` 设计不入 Git；权威、可追踪实现位于上述 `phase2_edit` 路径。

## 下一步

继续按相同 TDD 机制扩展其他可证实的遗漏类型。新增规则必须有失败样例、通过回归、
来源或可复现实证，并保持“历史记录不冒充已修复、候选工件不自动晋级”的边界。
