# MIMIC 实验室流水线阶段 C：BigQuery 聚合复核

日期：2026-09-20

## 1. 用户问题与本轮范围

用户授权继续修订 MIMIC 审计 SQL，并要求清洗规则有明确逻辑、统计与数据来源依据，能够通过 skill 和回归测试持续防止同类遗漏。本轮将 PostgreSQL Phase-C 已验证的实验室合同适配到 BigQuery，对固定的 5,549-stay 审计快照执行 cohort-scoped、aggregate-only 复核。

本轮不创建患者级永久表，不导出患者、住院、stay、labevent 或 specimen 标识，不改写历史 SQL，不冻结最终队列，也不把 QC 计数解释为论文结果。

## 2. 使用的文件、版本和数据状态

- 数据源：PhysioNet BigQuery MIMIC-IV 3.1，`mimiciv_3_1_hosp.labevents` 与 `d_labitems`。
- 审计队列：`ahf_work.dhf_lab_audit_cohort_snapshot_20260918`；5,549 个有效 stay，仅在查询内部使用标识。
- 时间窗：`[intime, intime + 12h)`；结果可用时间为 `GREATEST(charttime, COALESCE(storetime, charttime))`，末端严格 `<`。
- 合同：14 个允许概念与 8 个 BUN 非血液 quarantine itemid；规则包 SHA-256 为 `9f0fd0eca70dbd8e08ea3d17367b382154f9f961e817127443dfc9037aa1f720`。
- BigQuery SQL 模板 SHA-256 为 `bb09950c642c7a62108ca77fefc10f896e2cd24c8f2a517ce93e5f6c4223c640`；替换计费项目占位符后的运行 SQL SHA-256 为 `c30fcb51e908995662e80da946122e1d00c0b6dec200cecb8a4a2140fb021106`。

## 3. 已验证事实与证据

### 3.1 BigQuery 执行

- dry-run：`bq_phase_c_20260920_dry_02`，预计处理 10,876,276,916 bytes，低于 20 GB 上限。
- 正式运行：`bq_phase_c_20260920_live_01`，BigQuery job `bqjob_r5a3c19075156d33d_000001a0bc9386da_1`。
- 2026-09-20 重新读取 job metadata：状态 `DONE`、无 `errorResult`、处理 10,876,276,916 bytes、计费 10,876,878,848 bytes、685,528 slot-ms、未命中缓存。
- 输出 81 行聚合结果；运行状态 `passed_aggregate_qc`。提交版证据已将个人计费项目名替换为 `BILLING_PROJECT_REDACTED`，其余查询与哈希证据保留。

### 3.2 硬门与污染隔离

以下 9 个 hard gate 均为 0：allow/quarantine 字典不匹配、cohort 重复 stay、无效时间边界、缺关键键、eligible specimen 违规、eligible 时间违规、eligible 合同违规，以及 BUN eligible 非血液或错误 itemid。

BUN 的血液合同只允许 `itemid=51006 / Blood / Chemistry / mg/dL`。当前 cohort/window 内发现 384 条尿液 BUN，全部进入 `wrong_fluid_urine`；其余 7 个非血液 BUN itemid 均在字典中精确匹配，但本次窗口内为 0 行。零观察不代表删除规则，仍保留 quarantine 防线。

### 3.3 概念级结果

| 概念 | eligible | T12 后才可用 |
| --- | ---: | ---: |
| base excess | 6,204 | 45 |
| bicarbonate | 6,905 | 643 |
| BUN | 6,918 | 644 |
| creatinine | 6,937 | 649 |
| hemoglobin | 6,264 | 298 |
| INR | 4,916 | 317 |
| lactate | 4,932 | 38 |
| NT-proBNP | 639 | 146 |
| pH | 6,413 | 46 |
| platelet | 6,250 | 299 |
| potassium | 7,105 | 681 |
| sodium | 6,999 | 665 |
| troponin T | 3,384 | 416 |
| WBC | 6,201 | 297 |

旧 V2 cohort 快照审计中的 6 个重叠概念（BUN、creatinine、lactate、NT-proBNP、pH、troponin T）eligible 与 late 计数逐项一致。本轮新增覆盖另外 8 个 Phase-C 概念，不改变旧审计结论。

### 3.4 回归与静态门

- BigQuery SQL/runner/证据工件回归：12/12；runner 要求 9 个 hard gate 完整且唯一，并拒绝任何额外输出列。
- 项目内 MIMIC 清洗 skill：规则包验证通过，基础夹具 13/13、边界夹具 6/6。
- PostgreSQL Phase-C runner/SQL：11/11。
- MIMIC 实验室质量门：39/39；正式入口：2/2；V2 语义审计：8/8。合计 91/91。
- PostgreSQL `sql_v3_3` 8 份 SQL 通过 `pglast`；BigQuery SQL 已通过真实 dry-run 与正式查询验证。
- 正式静态门：176 SQL / 176 manifest / 100 条历史或审计 finding / 0 blocker。

## 4. 判断与影响

本轮把“BUN 必须来自血液、错误体液必须隔离、结果必须在 T12 前真实可用”从本地 PostgreSQL 复核扩展到了 PhysioNet BigQuery 源表，并证明 14 个实验室合同在固定 cohort 内可执行且聚合硬门通过。对当前项目的直接帮助是：今后重建 T12 特征时，可以自动拦截错误体液、迟到结果、字典漂移、时间边界与 specimen 异常，不再依赖人工发现尿液 BUN 等遗漏。

但 `passed_aggregate_qc` 只说明该快照上的聚合合同没有触发硬门；它不证明 DHF 表型、风险集、结局、完整依赖链或最终模型已经冻结，也不能写成论文结果。

## 5. 新增或确认的研究决策

- 新 SQL 登记为 `AUDIT_ONLY`、`allow_final_run=false`，不自动晋级 `ACTIVE`。
- 历史 SQL 保留；BigQuery 适配使用新增 `118` 版本。
- BUN 8 个非血液 itemid 持续 quarantine；当前样本为 0 的类别不移除规则。
- skill 只作为项目内部清洗与防错机制；论文方法部分应描述实际数据合同和 QC，而不是写“使用了某个 skill”。
- 提交仓库的运行证据只保留聚合结果和脱敏 metadata；本地原始 run 目录继续由 `.gitignore` 隔离。

## 6. 未决问题、阻塞项和假设

- 当前 cohort 是实验室审计快照，不是最终模型 cohort。
- PostgreSQL Phase-C 已发现 raw 与 derived 的覆盖/数值差异；本轮未将每个差异分解为迟到、删失、范围标志、单位、重复或聚合口径的具体占比。
- v3.3 完整上游依赖、DHF 表型、T12 风险集和三态结局仍未完成正式冻结，因此相关 SQL 继续 fail-closed。
- 其他数据库可以复用规则生命周期和测试框架，但不能直接复用 MIMIC itemid；需建立独立 adapter 与证据包。

## 7. 下一步动作

1. 继续对 BUN、creatinine、lactate 的 raw-vs-derived 差异做聚合原因分层，不导出患者级记录。
2. 补齐 v3.3 上游传递依赖与数据库硬门，再决定哪些候选 SQL 可晋级 `ACTIVE`。
3. 冻结 DHF 表型、T12 风险集与三态结局后，用同一冻结 run 重建特征并重跑 118 审计。

## 8. 本轮修改文件

- `sql_v3_3/bigquery/audits/118_audit_raw_lab_contract_phase_c_bq.sql`
- `project_control/bigquery/run_mimic_lab_phase_c_bq.py`
- `project_control/bigquery/tests/test_mimic_lab_phase_c_bq.py`
- `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
- `project_control/audits/bigquery_phase_c_20260920/run.json`
- `project_control/audits/bigquery_phase_c_20260920/aggregate_qc.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_ledger_bigquery_phase_c_20260920.csv`
- `project_control/quality_gates/mimic_lab/reports/sql_risk_summary_bigquery_phase_c_20260920.md`
- `project_control/task_reports/TASK_REPORT_20260920_MIMIC_BIGQUERY_PHASE_C.md`
- `project_control/task_reports/README.md`

## 9. 可重复性信息

- runner 固定使用 BigQuery Standard SQL、区域 US、20 GB 最大计费门限，并先 dry-run 后正式执行。
- 正式运行的本机原始目录：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/bq_phase_c_20260920_live_01/`。
- 可提交的脱敏证据目录：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/bigquery_phase_c_20260920/`。
- 脱敏 `run.json` SHA-256：`7c004f9baa899c8f2b0381d8bbfd4f2a57154155fee4b0d295e51f6c361d64b6`。
- 聚合 CSV SHA-256：`75fe1459f4afb48465e061811b614bde97346232767d0f640bb039bebe8250ec`。
- 本轮无随机抽样或模型拟合，不涉及 seed。
