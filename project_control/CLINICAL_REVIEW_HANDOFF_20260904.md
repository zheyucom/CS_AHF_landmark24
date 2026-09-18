# DHF 主窗口临床标注交接（2026-09-04）

## 只需要打开这个文件

`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_draft.csv`

这 300 条报告来自完整的 `[T0-24 h,T12)` 主窗口。不要使用旧的 `controlled_annotation_20260830_v2` 标注包估计当前主窗口性能。

## 每行填写

- `reviewer_id`：例如 `human_1`
- `final_congestion_label`
- `final_alternative_explanation_label`
- `final_comments`
- `review_status`：完成该行后填 `human_reviewed`

`final_report_available_pre_t0_label` 和 `final_report_available_by_t12_label` 通常采用文件中的 Codex 草标；如发现时间判断错误，再按时间字段修正。不要修改任何 `codex_draft_*` 列。

## 标签取值

`final_congestion_label` 只能填写：

- `definite_congestion`：明确肺水肿、间质性水肿或肺血管充血
- `possible_congestion`：可能/疑似水肿或不能排除充血
- `no_congestion`：明确无肺水肿、无肺血管充血或肺野清晰
- `indeterminate`：只有胸腔积液/心影增大、非胸部检查、技术限制或无法判断

`final_alternative_explanation_label` 只能填写：

- `none_apparent`
- `pneumonia_ards`
- `pulmonary_embolism_or_rv_strain`
- `postoperative_or_technical`
- `other`
- `unclear`

胸腔积液或心影增大不能单独证明肺充血；非胸部检查应标为 `indeterminate`，并在备注写明“不用于肺充血判断”。不确定时保留 `possible_congestion` 或 `indeterminate`，不要为了提高阳性率强行判定。

## 完成标准

300 行都必须有 reviewer、合法 final 标签、非空 comments，并将 `review_status` 改为 `human_reviewed`。完成后无需手工复制文件；告知 Codex 后运行：

```sh
cd /Users/zheyu/Desktop/CS_AHF_landmark24
python3 project_control/bigquery/merge_dhf_annotation_review.py
```

如需正式一致性分析，第二位临床人员应在以下文件中独立盲法填写 60 条，不能先看第一轮结果：

`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round2_blinded.csv`

## 研究边界

人工标注用于验证影像筛查器和构建 DHF 证据层，不等于单凭影像确诊 DHF。最终患者级表型仍需结合时间可追溯的 HF anchor、临床失代偿/充血和治疗或管理强化证据；报告文本不会进入 T0-T12 主预测器。
