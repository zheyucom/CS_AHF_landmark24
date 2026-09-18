# TASK_REPORT — 2026-08-28

## 本轮完成

- 修正并运行 `099_create_ahf_phenotype_audit.sql`。
- 修正两个审计错误：
  - 主事件由 `final_state='event'` 判定，而不是错误使用 `event_type='event'`；
  - NT-proBNP 住院至 T0 和最近 24 h 窗口均限制在 `[admittime, intime)`，避免住院前检验混入。
- 建立审计表 `study_ahf_v3_2.audit_099_ahf_phenotype_v1`。
- 导出证据组合、BNP/loop 交叉表、共病分层、候选队列和 stay-level CSV。
- 完成 AHF 初筛方法学报告和文献依据汇总。

## 关键结果

- v3.3 broad cohort：5,555 stays / 454 events。
- 严格 pre-T0 AHF：650 stays / 66 events（10.15%）。
- 严格最近 24 h：378 stays / 34 events（8.99%）。
- strict pre-T0 中：loop+NT-proBNP 43，loop-only 103，NT-proBNP-only 504。
- strict pre-T0 排除 BNP-only 后：146 stays / 9 events。
- broad cohort 中：3,835 例 acute-HF ICD 但无合规 pre-T0 客观证据；1,070 例为非急性/其他 HF 锚点。
- 共病不能机械排除；PE、明确非心衰主导替代诊断和 BNP-only 进入预设敏感性分析。

## 当前判断

若论文必须称为 AHF 预测模型，650 例严格队列更符合目标人群，但只有 66 个事件，模型必须改为低维、强收缩或探索性分析。5,555 例可保留为 broad operational cohort，但不能直接宣称为临床确诊 AHF。

## 产物

- `sql_v3_2/audits/099_create_ahf_phenotype_audit.sql`
- `sql_v3_2/audits/099_export_ahf_phenotype_audit.sql`
- `project_control/runs/20260828_ahf_phenotype_audit/`
- `project_control/reports/2026-08-28_ahf_screening_and_literature_review.md`
- `project_control/RESEARCH_DASHBOARD.md`

## 本次继续处理：BigQuery 数据集名与权限阻塞

- 发现原 BigQuery 说明错误使用 `physionet-data.mimiciv_hosp` / `mimiciv_icu`；BigQuery 核心库应使用版本化名称 `physionet-data.mimiciv_3_1_hosp` / `physionet-data.mimiciv_3_1_icu`。
- 已修正 `project_control/bigquery/README.md` 中的核心表测试 SQL，并明确本地 PostgreSQL schema 名称不能直接当作 BigQuery 数据集名。
- 已修改 `sql_v3_2/audits/102_export_strict_ids_for_bigquery.sql`，导出 `stay_id/subject_id/hadm_id/admittime/intime` 五列。
- 已修改 `project_control/bigquery/103_query_pre_t0_radiology.sql`，使用上传表中的本地审计时间字段，只读取 `physionet-data.mimiciv_note.radiology`，保持 `admittime <= charttime < intime`。
- 已重新运行导出：`650` 条数据、`651` 行含表头、无字段数错误。

当前状态：正确的 core 数据集权限尚待重测；无论重测结果如何，radiology 验证也可使用本地导出的时间字段，仅依赖 Note 表。Note 表权限、BigQuery 作业项目和结果表写入权限仍需用户在控制台确认。

## BigQuery 修正（2026-08-28）

- 用户发现 BigQuery 核心表的正确版本化数据集名称为 `physionet-data.mimiciv_3_1_hosp` / `physionet-data.mimiciv_3_1_icu`。
- 原说明中的 `physionet-data.mimiciv_hosp` / `physionet-data.mimiciv_icu` 是错误的 BigQuery 名称；已修正 README 中的测试 SQL 和名称说明。原报错不能据此直接判定 core 权限不足，需用正确名称重测。
- 项目本地 PostgreSQL 审计 SQL 继续使用本地 schema `mimiciv_hosp` / `mimiciv_icu`，两者不能混用。
- 103 radiology 查询当前使用本地导出的 `admittime/intime`，只需 Note 表权限；核心表权限可作为后续扩展路径，不再是该验证查询的必需条件。

## 未完成与下一步

1. 导师确认严格 AHF 是否为论文主队列。
2. 若确认，建立 650 例低维建模输入，特征数按 EPV 重新冻结。
3. 输出排除 BNP-only、PE、最近 24 h 和双证据敏感性。
4. 在最终队列上重跑 Fine-Gray、person-period 和 IPCW/complete60。
5. 在 BigQuery 中先运行版本化核心表测试；再上传含五列时间边界的 strict cohort CSV，运行 103 radiology 验证查询。

## 2026-08-29 续办记录

- 已运行 `sql_v3_2/audits/104_audit_ntprobnp_rulein_refinement.sql`，日志位于 `project_control/runs/20260829_ahf_phenotype_refinement/logs/104_ntprobnp_rulein_refinement.log`。
- 结果：当前 650 例候选中年龄分层 NT-proBNP rule-in 484 例；实际 IV loop eMAR 146 例；loop+年龄分层 rule-in 36 例、1 个事件；loop 或年龄分层 rule-in 594 例、61 个事件。
- 科学修正：`NT-proBNP >=300` 是支持性阈值，不是单独 rule-in 或临床确诊标准；BNP-only、PE、最近24 h、双证据均为敏感性/审计，不默认作为主队列排除标准。
- 已新增 `project_control/reports/2026-08-29_ahf_design_decisions_and_literature_basis.md`，说明严格 AHF、650 例低维模型、共病处理、文献依据和导师决策点。
- 已更新 `project_control/RESEARCH_DASHBOARD.md`：将 650/66 改为 pragmatic strict operational AHF 主候选，并加入 104 审计结果。

### 当前未完成

1. 导师确认 pragmatic strict operational AHF 是否作为论文主队列。
2. 冻结约 5-6 个有效参数的 AHF-specific 低维预测器并重建特征输入。
3. 完成 strict 队列 Fine-Gray、person-period、IPCW/complete60 及表型敏感性分析。
4. 用户在 BigQuery 用版本化表名测试权限，并运行 103 radiology 查询；项目侧随后做覆盖率和人工抽样验证。
