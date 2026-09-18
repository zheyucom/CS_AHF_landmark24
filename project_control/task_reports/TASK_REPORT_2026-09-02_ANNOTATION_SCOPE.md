# 任务报告：影像类型、心超复核和 final_comments 说明

日期：2026-09-02  
状态：已完成范围修正和用户操作说明

## 本次确认

1. 当前 106/107 使用的是 MIMIC-IV-Note 的放射科报告文本，不是下载的原始影像/DICOM；报告中主要包含胸片，也可能有胸部 CT 和其他部位影像。
2. `congestion_label` 的确是肺充血/肺水肿标签，用于提供 pre-T0 客观肺部充血证据；它不能单独确诊 DHF，仍需结合 HF anchor、治疗/管理证据及必要的其他域信息。
3. 发现原 300 条抽样中包含非胸部检查后，已在草标文件增加 `report_scope`：`chest_radiology` 185、`chest_radiology_inferred` 15、`mixed_or_unclear` 19、`non_chest_radiology` 81。非胸部报告自动草标为 `indeterminate`/`unclear`，不作为肺充血证据。
4. 心超如果将来用于 DHF 入组，必须建立独立的心超标签体系并对抽样结果进行临床复核，不能把心超直接套用肺充血标签；但当前 MIMIC-IV-Note 这条 radiology 管线尚未获得或验证独立、完整的心超报告字段，因此暂不把心超写成已完成数据源。

## final_comments 的用途

`final_comments` 是人工确认后的可追溯理由，不是写完整病历或下最终临床诊断。建议一句话记录：使用的关键英文证据、为何接受/修改草标、是否有替代解释。非胸部报告写“非胸部检查，不用于肺充血判断”。

## 关键文件

- 草标工作副本：`project_control/bigquery/controlled_annotation_20260830_v2/dhf_radiology_annotation_round1_codex_draft.csv`
- 中文快速指南：`project_control/templates/DHF_RADIOLOGY_ANNOTATION_QUICKSTART_ZH.md`
- 范围识别脚本：`project_control/bigquery/make_dhf_annotation_draft.py`
- 回写与 QC：`project_control/bigquery/merge_dhf_annotation_review.py`
