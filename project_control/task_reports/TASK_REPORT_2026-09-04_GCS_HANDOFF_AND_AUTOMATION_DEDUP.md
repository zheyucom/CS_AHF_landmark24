# 任务报告：GCS 导出交接与周报任务去重（2026-09-04）

## 本轮完成

1. 核对 GCS 完整主窗口 CSV：7,828 条数据行、27 列、3,886 个 stay；`(stay_id,note_id)` 唯一，报告正文和 `storetime` 无缺失。
2. 核对完整 CSV SHA256：`bf742833fd2ba708fad9e20a0884636a2b02e6b80fbaef61679fcc41f40048e6`，与既有导出审计一致。
3. 核对新主窗口人工标注包：第一轮 300 条、第二轮 60 条；第一轮仍为 `pending_human_review`，没有误生成最终临床标签。
4. 确认本轮不需要再次运行 BigQuery；当前瓶颈已经从数据导出转为临床标注、独立复核（如需要）和 DHF 表型冻结。
5. 保留固定每周二 16:00 的 cron 周报任务，并暂停重复的同主题 heartbeat，避免周报重复生成；cron prompt 已更新为读取新主窗口标注目录和 GCS 完整导出状态。

## 当前交接入口

- 主入口：`project_control/RESEARCH_DASHBOARD.md`
- 完整报告：`project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`
- 第一轮标注：`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_draft.csv`
- 标注说明：`project_control/CLINICAL_REVIEW_HANDOFF_20260904.md`
- 回写 QC：`project_control/bigquery/merge_dhf_annotation_review.py`

## 当前未完成

- 300 条第一轮报告的临床最终标签尚未填写。
- 60 条第二位标注者文件目前只是待复核框；若要报告 inter-rater kappa，必须由不同临床人员盲法完成，不能复制第一轮。
- DHF 主表型和最终低维预测器尚未冻结，因此不能把旧 v3.3 模型结果写成最终论文结果。

## 下一步

完成临床复核后运行回写 QC；随后由 Codex 计算报告级 PPV、分层结果、患者级 DHF 表型、事件数/EPV，并在冻结表型上重跑最终 Fine-Gray、1 h person-period、嵌套 MICE `m=20` 和预设敏感性分析。
