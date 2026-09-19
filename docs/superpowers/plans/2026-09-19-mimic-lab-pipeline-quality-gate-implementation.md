# MIMIC 实验室流水线质量门：阶段 A 实施计划

日期：2026-09-19
范围：仅代码权威、静态扫描、依赖检查和合成夹具；不查询患者级数据。

## 目标

把已批准设计落实为 fail-closed 的项目内质量门：全部 Git 跟踪 SQL 必须逐文件登记；正式执行计划不能包含未登记、历史封存或被替代工件；实验室 SQL 的语义、单位、可用时间、标本重复、derived 使用及静默异常值删除风险可被机器识别。

## 已知基线

- 隔离分支：`codex/mimic-lab-quality-gate-20260919`。
- 现有 MIMIC 实验室 V2 审计回归 8/8 通过。
- 仓库已有的 `phase2_edit/.../test_fixtures.py` 缺少其对应实现与规则包，属于进入本阶段前已存在的失败；单独登记，不作为新质量门的通过证据。

## TDD 顺序

1. 先写“未登记 SQL 必须失败”的测试并确认 RED；实现最小清单校验。
2. 再逐项加入并确认 RED：重复登记、状态/最终运行矛盾、ACTIVE 引用 blocked 产物、正式角色直接使用 derived、raw 缺少 availability/unit/fluid/category/specimen、错误体液 itemid、模糊 label、缺失补零、`CASE ... ELSE NULL` 静默过滤。
3. 加入允许场景：AUDIT_ONLY 可做 derived 覆盖对账；合规 raw SQL 可通过。
4. 每个 RED 后只写使该行为通过的最小实现；全部转绿后再重构 CLI、报告格式和说明文档。

## 阶段 A 产物

- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/quality_gates/mimic_lab/quality_gate.py`
- `project_control/quality_gates/mimic_lab/lab_contract_v1.json`
- `project_control/quality_gates/mimic_lab/tests/test_quality_gate.py`
- `project_control/quality_gates/mimic_lab/README.md`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_20260919.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_20260919.md`

## 权威清单初始化原则

- 每个 Git 跟踪 SQL 恰好一行；未知或尚未完成依赖审计的执行链一律 fail-closed。
- `sql_v3_2` 当前主线执行/建模 SQL 在阶段 B 完成 raw 合同层重构前标记 `LEGACY_BLOCKED`，不能因为目录名而提前获得 ACTIVE 身份。
- `sql_v4_2` 敏感性候选同样先 blocked；通过同一质量门后再逐文件晋级。
- 当前正式语义审计、候选发现及明确的审计 SQL 标记 `AUDIT_ONLY`；V1 截断审计标记 `SUPERSEDED`。
- 其他历史目录保留原文件并标记 `LEGACY_BLOCKED`，不原地改写。

## 验证与交付

1. 新质量门测试全部通过，并保留 RED→GREEN 命令证据。
2. 对全仓 Git 跟踪 SQL 运行扫描：清单遗漏=0、重复=0。
3. 输出历史风险账本；blocked 文件中的发现用于阶段 B 排期，不修改历史文件。
4. 重新运行其余可执行基线测试；预先存在的失败单独报告。
5. 更新任务报告与研究总览；提交、推送并核对本地和远端分支 SHA。
