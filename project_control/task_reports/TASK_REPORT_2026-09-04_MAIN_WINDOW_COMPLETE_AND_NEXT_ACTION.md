# 任务报告：主窗口完整导出审计与下一步交接（2026-09-04）

## 本轮完成

1. 使用 GCS 完整导出的主窗口 radiology CSV 重新运行紧凑报告审计和患者级多域审计。
2. 核验解析后 `7,828` 条报告、`27` 列、`3,886` 个 stay；`(stay_id,note_id)` 唯一，正文和 `storetime` 无缺失；SHA256 为 `bf742833fd2ba708fad9e20a0884636a2b02e6b80fbaef61679fcc41f40048e6`。
3. 确认 `[T0-24 h,T12)` 内 `6,415` 条报告在 T12 前可见，`3,352` 条在 ICU 入科前可见；报告级模态规则计数为 CXR `1,534`、胸部 CT `315`、其他/未分类 `5,979`。
4. 患者级审计重跑并留档：5,549 个有效 HF anchor；definite CXR/CT 且 T12 前可见为 `625 stays / 78 events`；再加 pre-T0 IV loop 或 NT-proBNP 支持为 `83 stays / 15 events`。
5. 从完整主窗口重新生成三层各 100 条的人工标注包，以及 60 条第二轮盲法抽样框；已生成 300 条保守 AI 草标，仍全部为 `pending_human_review`。
6. 修正 `make_dhf_annotation_draft.py` 与 `merge_dhf_annotation_review.py` 默认目录，统一指向 `controlled_annotation_20260904_landmark12_complete_v2`。
7. 更新研究总览、BigQuery README 和人工标注行动说明；周二 16:00 周报自动任务已存在并启用。

## 研究判断

- 完整导出解决了网页全文下载截断问题，当前主窗口影像覆盖和阳性审计可以继续使用；此前 7,558 行文件仅保留为历史不完整尝试。
- 影像严格层只有 625 个 stay、78 个事件，按 45 个预测器计算 EPV 约 `1.73`；加入 loop/NT-proBNP 后反而只有 83 个 stay、15 个事件。因此不能把严格影像层直接作为当前 45 特征主模型开发队列。
- 单张胸片、胸部 CT、BNP/NT-proBNP、IV loop 或“做过心超”均不能单独确诊 DHF。MIMIC 主开发端仍应使用多域、时间可追溯的操作性表型；院内外部验证保留 `echo_performed + result_available + abnormal_support` 严格层。
- 这 300 条标注必须由临床人员确认；AI 草标只用于提高阅读效率。旧 pre-T0 300 条与新主窗口仅重合 145 条，不能合并估计新主窗口 PPV。60 条如果仍由第一位标注者复制，不能计算独立 inter-rater kappa。

## 当前阶段

阶段 3：完整影像表型验证与 DHF 表型冻结；院内外部验证处于字段语义和样例 QC 阶段。最终模型尚未因本轮审计自动重跑，避免在主表型未冻结时产生不可比结果。

## 下一步

### 需要用户/临床标注者完成

1. 在 `project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_draft.csv` 中逐条核对英文原文，填写 `final_congestion_label`、`final_alternative_explanation_label`、`final_comments`、`reviewer_id`，并将 `review_status` 改为 `human_reviewed`。
2. 若需要独立一致性，由第二位临床人员盲法填写同目录的 `dhf_radiology_annotation_round2_blinded.csv`；不要复制第一轮标签。若按原计划继续同标注者复制，只能作为重复性/流程记录，不能报告为独立 kappa。
3. 向信息科回填字段语义清单，优先确认 ICU `intime/outtime`、心超检查/结果可见时间、检验采样时间、eMAR/输液泵和 ICU 出科生命状态。

### Codex 可继续完成

1. 收到人工标注表后运行 QC、合并、分层 PPV/一致性和患者级表型审计。
2. 收到字段映射与正式 20-50 例样例后执行院内时间线/单位/连接键 QC。
3. DHF 主队列证据层冻结后，按事件数重新冻结低维特征，运行最终 Fine-Gray 主模型、1 h person-period 补充模型、折内 MICE `m=20` 和预设敏感性分析。

## 关键文件

- 主入口：`project_control/RESEARCH_DASHBOARD.md`
- 主窗口完整原始报告：`project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`
- 主窗口紧凑审计：`project_control/bigquery/dhf_radiology_report_audit_landmark12_v1.csv`
- 患者级审计：`project_control/bigquery/landmark12_audit_20260904/`
- 新主窗口标注包：`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/`
- 院内字段语义清单：`project_control/INTERNAL_HOSPITAL_FIELD_SEMANTICS_CONFIRMATION_CHECKLIST_V1.md`

## 结论

本轮没有权限或导出阻塞。研究已推进到“临床标注/字段语义确认 -> 表型冻结 -> 最终模型重建”的交接点；当前最重要的下一项不是再次运行 BigQuery，而是完成新主窗口标注确认和院内字段语义回填。
