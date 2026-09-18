# 任务报告：MIMIC-IV-Echo 权限核验与 T12 心超审计实测结果

日期：2026-09-03  
状态：已完成 BigQuery 权限核验、真实 schema 查询、行级时间窗审计与结果表创建

## 本轮完成

1. 通过用户已登录的 BigQuery 控制台确认可访问：
   - `physionet-data.mimiciv_echo.echo_record_list`
   - `physionet-data.mimiciv_echo.echo_study_list`
   - `physionet-data.mimiciv_echo.structured_measurement`
2. 核实真实 schema：
   - `echo_record_list`：`subject_id`、`study_id`、`acquisition_datetime`、`dicom_filepath`；
   - `echo_study_list`：`subject_id`、`study_id`、`study_datetime`、`measurement_id`、`measurement_datetime`、`note_id`、`note_seq`、`note_charttime`；
   - `structured_measurement`：`subject_id`、`measurement_id`、`measurement_datetime`、`test_type`、`measurement`、`measurement_description`、`result`、`unit`。
3. 修订并运行 [`113_query_mimic_echo_strict_candidate.sql`](../bigquery/113_query_mimic_echo_strict_candidate.sql)：
   - 用 `study_datetime` 作为检查时间；
   - 用关联 `note_charttime` 作为结果可用时间代理；
   - 分开记录检查完成、结构化结果记录、note 在 T12 前以及异常支持；
   - 输出表已在 BigQuery 创建：`project-9386bb9f-de39-47eb-886.ahf_work.echo_result_audit_v1`。

## QC 实测结果

窗口严格为 `[T0-24 h,T12)`；有效候选为 5,549 个 stay。

| 指标 | 结果 |
|---|---:|
| 输出行 / 唯一 stay | 5,549 / 5,549 |
| 链接 TTE/TEE study | 61 |
| 有非空结构化结果 | 61 |
| 关联 Echo note `charttime < T12` | 9 |
| 结构化 draft abnormal-support | 41 |
| 同时具 T12 前 note 与异常支持的 strict draft | 6 |
| 检查在窗内但 note 在 T12 后或缺失 | 52 |

本窗内实际发现的检查类型为 TTE；没有 TEE 行。`note_charttime` 是报告可用性的保守代理，不能写作独立的报告签署时间。

## 方法学结论

“所有 ICU 内 DHF 患者都会在 12 h 内留下可用心超结果”在 MIMIC 中不成立，或至少不能被该数据集证明。若把 `echo result available + abnormal support by T12` 作为 MIMIC 主开发队列硬门槛，只有 6 个 draft stay，不能进行有效的竞争风险预测建模，也会造成严重的检查选择性。

因此，方案调整为：

- **MIMIC 主开发队列**：预先冻结、时间可追溯、经抽样临床复核的多域 DHF 操作性表型。它至少需要 HF anchor、独立肺充血或临床失代偿证据、管理/治疗强化证据；BNP、利尿剂、单张胸片、CT 或 Echo procedure 均不可单独确诊。
- **MIMIC Echo 层**：病例级规则验证和高特异性敏感性层。`strict_echo_supported_draft_flag` 不能在人工复核前用于最终入组或建模。
- **院内外部验证**：保留 `echo-supported DHF ICU cohort identified by T12` 严格层，接受 TTE、TEE 和心脏 POCUS；同时需报告与 MIMIC 可桥接的多域层，不能将两者混作同一目标人群。

这不是降低科学标准，而是把“临床上最可信的确证层”与“在 MIMIC 中可有效建模的操作性表型”明确分开，并如实报告覆盖率与选择性。

## 已更新入口

- [`RESEARCH_DASHBOARD.md`](../RESEARCH_DASHBOARD.md)
- [`study_definition_v5_pre_t0_dhf_landmark12.md`](../../study_definition/study_definition_v5_pre_t0_dhf_landmark12.md)
- [`113_query_mimic_echo_strict_candidate.sql`](../bigquery/113_query_mimic_echo_strict_candidate.sql)

## 下一步

1. 从 61 个 Echo-linked study 中按“note 在 T12 前、draft abnormal、其余/不确定”分层抽取 20-50 条，人工复核心超结果与异常规则。
2. 利用已可见的 `mimiciv_note` 进一步建立有时间戳的临床失代偿证据，并与 300 条影像标注共同冻结 MIMIC 多域主表型。
3. 在该主表型上重新计算事件数与 EPV，冻结低维预测变量，再运行最终 Fine-Gray 主模型。
4. 院内提取时保留 `echo_performed`、`echo_result_available`、`echo_abnormal_support`、检查时间、结果/报告时间和 POCUS 来源字段。

预计主动工作量：Echo 抽样复核与规则定稿 1-3 h；多域表型冻结与 EPV 复算 2-4 h；最终特征重建和模型重跑 4-8 h。
