# MIMIC 清洗 skill 接入项目 SQL 的 preflight 报告

日期：2026-09-19
状态：完成（只读静态审计；未执行数据库或患者级查询）

## 目的

本报告是项目内部质量控制记录，不是论文正文。MIMIC 清洗 skill 只保存可复用的规则、审计器和回归夹具，防止下次处理同类数据时重复犯错。论文仅在方法部分按实际执行情况描述清洗原则、数据版本和质量控制，不需要引用或附上整个 skill 包。

## 扫描范围

对项目中的 23 个 SQL 文件执行只读静态 preflight，使用规则包 `mimic-iv-lab-rules.json`。审计器只读取 SQL 文本和规则包，不连接 BigQuery，不读取或导出患者级数据，也不改写历史 SQL。

## 结果

| 状态 | 数量 |
| --- | ---: |
| pass | 22 |
| warning | 1 |
| blocked | 0 |

唯一 warning：

- `sql_v3_3/executable/060_create_raw_lab_contract_layer_v1.sql`
- `MIMIC007`：该 SQL 是 raw 实验室合同层，包含 raw labevents、精确字典和 quarantine 逻辑，但自身不负责 raw↔derived 双向覆盖对账。
- 这不是错误体液纳入，也不是 SQL 需要重写；阶段 C 已有 `117_audit_raw_vs_derived_phase_c.sql` 专门承担双向对账，且该审计 SQL 本次为 pass。

此前扫描器把 quarantine 合同中的 8 个错误体液 itemid 误判为正式纳入，也把依赖 `lab_eligible_v1` 的下游 SQL 误判为 derived-only。已修正扫描器并重新运行，当前不再产生这些误报。

## 结论

当前 SQL 清单没有触发 MIMIC skill 的硬阻断项。BUN 血液规则、体液隔离、可用时间和 raw/derived 对账已经在合同层及阶段 C 审计中分工落实。060 的 warning 保留，作为职责边界提示，不自动改写或晋级历史 SQL。

## 产物完整路径

- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/run_mimic_skill_preflight.py`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/mimic_skill_preflight_20260919.json`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/mimic_skill_preflight_20260919.csv`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/task_reports/TASK_REPORT_20260919_MIMIC_SKILL_PREFLIGHT.md`

## 后续

下一步可以基于这份 preflight 结果继续做已授权 MIMIC 表的连接/权限预检；若目标表返回 `Access Denied`，仍必须记录 `not_run_access_denied`，不能用连接成功或 SQL dry-run 代替数据授权证明。
