# 任务报告：BigQuery 主窗口结果导出审计（2026-09-04）

## 已完成

- 在 BigQuery 网页控制台成功运行主窗口查询 109/110。
- 下载患者级汇总：`dhf_radiology_patient_summary_landmark12_v1.csv`，5,549 行，覆盖全部有效时间边界候选。
- 尝试下载原始报告全文，网页提示只能保存 `7,558/7,828` 行；本地文件确为 7,558 行，少 270 行。
- 未将 7,558 行误当成全量。新增紧凑报告审计输入和主窗口本地审计脚本，显式记录 `report_extract_complete_flag=0`。
- 重新生成患者级审计：5,549 stay；结局守恒为 452 event、2,934 competing alive ICU discharge、2,163 censor。

## 当前结果边界

患者级汇总确认主窗口 `[T0-24 h,T12)` 有 7,828 份报告、3,886 个 stay 有报告、3,542 个 stay 的报告在 T12 前可见，`storetime` 缺失为 0。这些数字可用于覆盖率 QC。

网页全文下载只得到 7,558 份报告；该文件已被 GCS 完整导出 `7,828/7,828` 所替代。当前模态/胸片-胸部CT分类和阳性层审计应使用 `dhf_radiology_raw_landmark12_v1_complete.csv`，不能再引用 7,558 行文件。

## 新增文件

- `project_control/bigquery/111_query_landmark12_radiology_report_audit.sql`
- `project_control/bigquery/build_landmark12_radiology_audit.py`
- `project_control/bigquery/dhf_radiology_report_audit_landmark12_v1.csv`
- `project_control/bigquery/landmark12_audit_20260904/`

## 下一步

1. 使用已下载的 GCS 完整 Parquet/CSV，要求后续所有模态分类和文本规则审计引用该版本。
2. 已完成完整报告层的行数、唯一键和 stay-level 对账；下一步是把完整主窗口规则结果与新窗口人工抽样结果对应，不能把旧 pre-T0 300 条标注直接重命名为主窗口验证集。
3. 在最终 DHF 表型冻结后，重新计算事件数、候选预测器上限和最终模型 manifest。

## 结论

BigQuery 网页路径可用；CLI/API 超时不是账号或 SQL 权限问题。当前唯一未完成点是浏览器本地下载的行数限制，已被审计脚本捕获，未污染最终研究数字。
