# 任务报告：胸部 CT 证据域决策与研究总览同步

日期：2026-09-05 Asia/Shanghai  
阶段：阶段 3，DHF 表型验证与冻结准备

## 本次完成

1. 在 `RESEARCH_DASHBOARD.md` 正式确认胸部 CT/CTA 纳入 DHF 相关肺部证据域。
2. 明确 CT 的作用：支持肺水肿/肺充血、肺间质改变和胸腔积液判断，同时记录 PE、肺炎、ARDS 等替代或并存解释。
3. 明确 CT 不是每例必需的检查，也不能单独确诊 DHF；未做 CT 不能编码为 CT 阴性或无 DHF。
4. 冻结影像审计分层：`CXR OR CT` 为主肺部证据层；`CXR-only`、`CT-only` 和 `CXR AND CT` 为来源/敏感性层，不改变主入组硬门槛。
5. 明确人工复核只对胸部影像判读肺充血；非胸部影像不进入肺充血 PPV 分母，最终使用人工确认后的 `final_report_scope`、`final_modality` 和 `final_congestion_label`。
6. 将新主窗口 300 条报告的人工复核加入未来 7 天执行清单。

## 人工复核文件

本轮 300 条报告的可填写文件为：

`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_draft.csv`

只填写 `reviewer_id`、`final_report_scope`、`final_modality`、`final_congestion_label`、`final_alternative_explanation_label` 和 `final_comments`。旧 `controlled_annotation_20260830_v2` 包及旧 `dhf_radiology_annotation_round1.csv` 不用于本轮主窗口最终复核。

## 当前结论

胸部 CT 应纳入，但应作为与胸片互补的肺部证据来源，而不是新的强制检查条件。DHF 最终操作性表型仍需结合 HF anchor、临床失代偿/肺部证据和治疗或管理强化证据；心超在院内严格验证层仍承担结构/功能支持作用。

## 验证与未完成

- 文档规则已完成一致性同步；当前主窗口影ni像人工最终标签仍未完成。
- 现有自动模态和关键词结果只能作为草筛查，不能替代临床标注。
- 下一步完成 300 条报告复核后，重新估计 CXR-only、CT-only、`CXR OR CT`、`CXR AND CT` 和 Echo-supported 层的覆盖率、事件率及选择性。
- 本报告不改变 MIMIC Echo 覆盖率、主模型事件数或既有 45 特征结果；最终建模仍需等 DHF 表型冻结后重跑。
