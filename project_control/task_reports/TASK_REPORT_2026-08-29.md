# 任务报告：2026-08-29

## 本轮完成

1. 运行 `sql_v3_2/audits/104_audit_ntprobnp_rulein_refinement.sql`。
2. 完成 AHF 表型、文献依据、低维建模和敏感性分析的正式设计说明。
3. 建立 strict AHF 低维候选特征清单和可执行建表 SQL。
4. 运行 105A 并完成唯一性、标签和缺失性 QC。
5. 更新研究总览，将 650/66 明确为 pragmatic strict operational AHF 主候选，而不是临床金标准。

## 关键结果

| 项目 | 结果 |
|---|---:|
| 当前 strict pre-T0 候选 | 650 stays / 66 events |
| 年龄分层 NT-proBNP rule-in | 484 stays |
| 实际 IV loop eMAR | 146 stays |
| loop + 年龄分层 rule-in | 36 stays / 1 event |
| loop 或年龄分层 rule-in | 594 stays / 61 events |
| 105A 低维输入 | 650 stays / 66 events |
| 105A alive ICU discharge competing events | 317 |
| 105A administrative censoring | 267 |

## 科学结论

- `NT-proBNP >=300` 不能写成 AHF 确诊或 rule-in 标准，只能作为与 HF ICD 锚点结合的支持性证据。
- ACS/AMI、CKD/AKI、房颤、COPD 和肺炎不应凭共病编码全部排除；它们可能是 AHF 诱因或并存病。
- PE、BNP-only、最近 24 h 和双证据是敏感性/审计分析，不是默认主队列排除标准。
- 650 例只有 66 个事件，原 45 个特征的名义 EPV 约 1.47；105A 先提供 6 参数候选，名义 EPV 约 11，但仍须折内处理和内部验证。

## 新增/更新文件

- `project_control/reports/2026-08-29_ahf_design_decisions_and_literature_basis.md`
- `project_control/FEATURE_FREEZE_AHF_STRICT_CANDIDATE_V1.md`
- `sql_v3_2/modeling/105A_create_strict_ahf_lowdim_candidate_v1.sql`
- `project_control/runs/20260829_ahf_phenotype_refinement/logs/104_ntprobnp_rulein_refinement.log`
- `project_control/runs/20260829_ahf_strict_lowdim_candidate/logs/105A_create_strict_ahf_lowdim_candidate_v1.log`
- `project_control/RESEARCH_DASHBOARD.md`

## 尚未完成

1. 导师确认 pragmatic strict operational AHF 是否作为论文主队列。
2. 冻结或修改 6 参数候选清单。
3. 在确认后的 strict 队列上运行 Fine-Gray 主模型、person-period 补充模型、IPCW/complete60 和表型敏感性分析。
4. 用户在 BigQuery 使用版本化数据集名测试权限并运行 103 radiology 查询；之后进行覆盖率和人工抽样验证。

## ESC 2026 DHF 方案更新

- 已核验 2026 ESC 指南（doi:10.1093/eurheartj/ehag100；PMID:42661420）及 ESC 官方新闻稿：DHF 取代 acute HF。
- 已新增 `project_control/reports/2026-08-29_ESC2026_DHF_implications_and_protocol_update.md` 与 `study_definition/study_definition_v5_pre_t0_dhf_landmark12.md`。
- 已明确入组 DHF 与 T12 后 hemodynamic deterioration 的时间分离：前者只用 pre-T0 多域证据，后者只用 post-T12 相对基线的循环支持升级/NEE/ICU death；主结局不称为纯 CS。
- 已新增并运行 `sql_v3_2/audits/106_export_dhf_radiology_candidates_for_bigquery.sql`：导出 5,555 个 HF ICD anchors，CSV 5,556 行含表头，8 列 QC 无错误。
- 已新增 `project_control/bigquery/106_query_pre_t0_dhf_radiology.sql`。下一步应上传 `dhf_radiology_candidates.csv` 并运行 106，而非只运行原 650 例的 103。
- 原 650/66 与 105A 低维表降为 legacy DHF candidate，待多域 DHF 验证后不直接作为最终主模型输入。

## DHF NLP 与时间序列准备

- 已新增 `project_control/reports/2026-08-29_dhf_phenotyping_nlp_and_time_series_protocol.md`：明确现阶段优先进行规则型文本筛查、双时间戳审计和人工验证，不直接训练复杂 NLP 模型。
- 已升级 106 至 v2：同时输出 `charttime`（检查发生）和 `storetime`（报告可用）相关标记，防止将 ICU 后才可见的报告作为可部署的 pre-T0 证据。
- 已新增 107 patient-level 汇总查询：在保存 106 raw output 后输出每位候选的报告覆盖、可用性、阳性/不确定筛查和首次时间。
- 已新增 `project_control/templates/DHF_RADIOLOGY_ANNOTATION_GUIDE.md`：定义盲法临床标注、分层抽样、双人复核和裁决流程。
- `dhf_radiology_candidates.csv` 是 5,555 个候选患者及其时间锚点，不是最终 DHF 入组名单。

## 预计投入

- 导师决策：约 0.5 h。
- 特征冻结和 QC：约 2-4 h。
- strict 队列模型及敏感性矩阵：约 8-16 h 主动工时，计算可能持续数小时。
- Note radiology 查询结果到位后：约 2-4 h 完成表型验证报告。
