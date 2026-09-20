# MIMIC 实验室特征来源与时间合同

日期：2026-09-20

## 结论

- 建立 29 行机器可读特征矩阵，覆盖当前 v3.3 候选主线的实验室 `max/min/first/last/delta`。所有行均规定 raw `lab_eligible_v1` 为主源，derived 仅用于对账，缺失不得补零或由 derived 静默回填。
- 发现 `063A...v2.sql` 的窗口漏洞：pre-T12 乳酸按 `charttime` 分窗，但未把 `availability_time` 同时限制在 T12 前。
- 历史 v2 保持不变；新增 v3，将 pre/post 两侧的采样时间和可用时间分别锁在同一窗口。
- 新增 122 聚合审计，并把 Phase-C runner 改为运行 v3 后立即执行 122。v3、122 均未获得正式运行权限。
- MIMIC cleaning skill 增加同窗规则：T12 前采样、T12 后才可用的结果既不能进入 pre-T12 特征，也不能被重分类为 post-T12 生理样本。

## 旧结论 → 新结论 → 原因

- 旧结论：063A v2 已通过阶段 C 数据库执行，可作为候选结局路径继续复核。
- 新结论：v2 的 SQL 语法和运行本身通过，但 pre-T12 乳酸时间合同不完整，继续保持历史阻断；当前候选改为 v3。
- 修正原因：既有测试只确认存在 `availability_time` 门，没有确认它与 `charttime` 落在同一个 pre/post 子窗口。119–120 已证明迟到 raw 结果真实存在，因此该缺口会造成 landmark 信息泄漏风险。

## PostgreSQL 聚合验证

在本机 `mimiciv31` PostgreSQL 12.18 中，将 v3 与 122 放入同一事务执行，随后显式 `ROLLBACK`；确认 v3 表未保留。最终输出仅为聚合计数：

| 指标 | 计数 |
| --- | ---: |
| T12 前采样、T12 后才可用且 episode 唯一的乳酸事件 | 38 |
| 受影响 stay | 38 |
| v2/v3 成功配对 stay | 5,564 |
| pre12 max / min / last 改变 | 16 / 13 / 33 |
| post12 max 改变 | 0 |
| new ≥2 / 2→4 / delta ≥2 标志改变 | 1 / 1 / 2 |
| 候选复合结局标志改变 | 0 |

这些数字仅是固定数据库快照的内部 QC，不是最终队列人数、事件数或论文结果。复合标志本次未变化也不能证明旧时间合同可接受；特征定义必须先满足时间因果顺序。

## 验证与边界

- 两轮 TDD 均完成 RED→GREEN：来源矩阵/v3/manifest 缺失时 5 项预期失败；122 缺失时 1 项预期失败；修复后目标测试通过。
- 最终 116 项回归全部通过；v3 与 122 静态扫描均为 0 finding；仓库质量门为 181 SQL / 181 manifest / 106 条历史或审计 finding / 0 blocker。
- PostgreSQL 实际解析、建表、聚合比较和回滚均成功；本机缺少 `pglast` 不影响真实数据库验证，但不把静态扫描冒充数据库执行。
- v2 SHA-256 保持 `99e5bd01e752c77c0d81b1f710967c542ffa752f9320fb259998b24d15969966`。
- v3 SHA-256：`6e351018d3cdab4c85e1af97cc7017d53fc621865c5d7c9cf92d299cd5395d12`。
- 122 SHA-256：`e5f7dcfa420026619a88712e80548439b2b198c280416dbe022d9f4f76780df2`。
- 矩阵 SHA-256：`f8608603c4f83125be8798517aa8574ef90082aaf5075432c6aea557b8ce68a0`。
- 不导出患者级数据，不修改历史 v2，不自动晋级 `ACTIVE`。

## 本轮文件

- `docs/superpowers/specs/2026-09-20-mimic-lab-feature-source-contract-design.md`
- `project_control/MIMIC_LAB_FEATURE_SOURCE_DECISION_MATRIX_V1.csv`
- `sql_v3_3/executable/063A_create_candidate_hd_outcomes_overall_v3.sql`
- `sql_v3_3/audits/122_audit_lactate_window_contract_v3.sql`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/database/mimic_lab_phase_c.py`
- `project_control/database/tests/test_mimic_lab_phase_c.py`
- `project_control/quality_gates/mimic_lab/tests/test_feature_source_decision_matrix.py`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/workflow.md`
- `phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/scripts/test_fixtures.py`
- `project_control/RESEARCH_DASHBOARD.md`
- `project_control/task_reports/README.md`
- `project_control/task_reports/TASK_REPORT_2026-09-20_MIMIC_LAB_FEATURE_SOURCE_CONTRACT.md`

## 下一步

最终 DHF 表型、T12 风险集和结局冻结后，用同一冻结 run 正式重建 v3 路径并重跑 116、117、122；在此之前维持 `allow_final_run=false`。
