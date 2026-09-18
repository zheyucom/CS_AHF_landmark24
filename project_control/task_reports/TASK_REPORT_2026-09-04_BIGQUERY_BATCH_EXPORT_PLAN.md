# 任务报告：主窗口全文分批导出方案（2026-09-04）

## 结论

可以分批导出。网页控制台一次本地下载最多保存 7,558 行，而主窗口真实结果为 7,828 行；将结果按 2,000 行分成四批可避开该限制。

## 执行方式

使用 `project_control/bigquery/112_query_landmark12_radiology_batch.sql`，四次分别使用 offset `0`、`2000`、`4000`、`6000`，固定 `ORDER BY stay_id, charttime, note_id`。每批导出 CSV 后运行 `merge_landmark12_radiology_batches.py`。

## 验收标准

- 四批合计恰好 7,828 行；
- 表头完全一致；
- `(stay_id, note_id)` 无重复；
- 合并后按 `stay_id, charttime, note_id` 排序；
- 再与 110 患者级汇总逐 stay 对账，确认每例报告数一致。

## 研究边界

当前 7,558 行全文文件只能作为不完整诊断材料；在四批合并通过前，CXR/胸部 CT 模态分层、影像阳性率和 DHF 纳入名单均不得冻结。
