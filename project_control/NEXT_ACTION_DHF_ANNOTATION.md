# 下一步行动：DHF 影像表型验证

更新时间：2026-09-04 Asia/Shanghai

> 当前口径更新：院内外部验证主队列为严格 `echo-supported DHF ICU cohort`。本文件早期关于“multidomain 为主队列”的流程文字仅适用于宽口径桥接审计；最终严格队列必须通过心超三级 QC。

## 你现在需要做什么

当前不需要继续运行 BigQuery，也不需要重新下载数据。你不必独自从零完成 300 条标注；可以采用“Codex 先草标 + 临床人员复核”的方式。推荐流程如下：

1. 由 Codex 对 `dhf_radiology_annotation_round1.csv` 做 AI-assisted 草标，并为每条记录保留简短判读理由。
2. 打开 `dhf_radiology_annotation_round1_codex_draft.csv`，优先阅读 `key_evidence_text_en` 和 `key_evidence_text_zh_assist`，以 `report_text` 英文原文为准，依次确认/填写 `final_report_scope`、`final_modality`、`final_congestion_label`、`final_alternative_explanation_label`、`final_report_available_pre_t0_label` 和 `final_comments`。胸片填 `cxr`，胸部 CT/CTA 填 `chest_ct`；非胸部检查填 `non_chest_radiology` + `non_chest` + `indeterminate`/`unclear`。
3. 由另一位临床人员独立完成 `dhf_radiology_annotation_round2_blinded.csv` 中 60 条报告；不要先查看第一轮标签。Codex 不能同时承担这一独立复核角色。
4. 不能确定时标为 `indeterminate` 或 `unclear`，不要为了提高阳性率强行判定。
5. 两份表保留原列名、行数、`annotation_id` 和 `report_text`；AI 草标和临床最终确认应在字段或审计日志中区分。胸部 CT 与胸片均可作为肺部充血候选证据，但不要求同一患者两种检查都完成。

特别注意：本轮报告集合不全是胸部影像。请查看 `report_scope`，但它只是 Codex 草分类，最终以 `final_report_scope`/`final_modality` 为准；`non_chest_radiology` 必须标为 `indeterminate`/`unclear`，`mixed_or_unclear` 或 `chest_radiology_inferred` 需人工确认检查类型后再决定。胸部 CT 需额外记录 PE、右心负荷、肺炎/ARDS 等并存或替代解释。

主窗口完整导出已生成新的受控抽样包：
`bigquery/controlled_annotation_20260904_landmark12_complete_v2/`

第一轮文件：
`bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1.csv`

第二位标注者的 60 条盲法复核文件：
`bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round2_blinded.csv`

本包来自完整 7,828 条主窗口报告，三层各抽 100 条；同时保存 `T0 前可见` 与 `T12 前可见` 两个时间字段。不要再使用旧 pre-T0 抽样包估计当前主窗口性能。

请不要修改 `codex_draft_*` 列，也不要把草标直接复制到 `final_*` 列；只有完成人工复核的行才填写 `final_*`，并将 `review_status` 改为 `human_reviewed`。
填完后不需要手工复制回原表；通知 Codex 或运行 `bigquery/merge_dhf_annotation_review.py`，它会先做标签/ID/空值 QC，再生成 `dhf_radiology_annotation_round1_completed.csv`。

## 这一步的目的

这不是最终建模，也不是把放射科关键词直接当成诊断金标准。它用于估计 106 规则的 PPV、否定/不确定表达误触发和漏检风险，并据此决定最终 DHF 表型的证据层级。AI 草标只能减少人工工作量，不能替代临床复核。

当前可用规模：5,549 个有效候选 stay、7,828 条 `[T0-24 h,T12)` 报告、3,886 个有报告 stay、300 条新主窗口第一位标注报告、60 条待独立复核报告。旧 300 条只作为历史 pre-T0 规则审计；60 条待独立复核，不能复制第一位标签后计算一致性。

## 你完成后我会自动接着做

1. 校验两份 CSV 的列、行数、ID、时间边界和空白字段。
2. 计算规则筛查的 PPV、分层一致率、Cohen's kappa，并整理分歧案例；PPV 分母只纳入最终确认的胸部影像，非胸部报告只用于范围分类审计。
3. 生成 patient-level 的 `candidate`、`radiology-supported`、`multidomain` 三层 DHF 表型。
4. 重算每层的样本量、主事件、竞争事件、删失和 EPV。
5. 在导师确认主队列后，冻结最终低维特征并重跑 Fine-Gray 主模型、person-period 补充模型和预设敏感性分析。

## 目前不要做的事

- 不要把 `dhf_radiology_patient_summary_v1.csv` 用于最终审计；它未排除 6 个异常时间边界。
- 不要把报告文本放进 T0-T12 预测器。
- 不要使用 T12 后信息判断入组。
- 不要把 NT-proBNP 单独视为 DHF 确诊证据。
- 不要在表型冻结前把 5,555 例 broad v3.3 或历史 650 例直接写成最终主队列。

## 周二周报

项目总览主入口是 `RESEARCH_DASHBOARD.md`。每周二 16:00 的“CS_AHF 周二研究进展周报”自动任务已经启用，会读取总览、最新任务报告和周报，并生成供周三组会使用的周报。周报只报告已完成、当前阻塞、预计工时和需要导师决定的事项，不提前把未冻结数字写成最终结果。
