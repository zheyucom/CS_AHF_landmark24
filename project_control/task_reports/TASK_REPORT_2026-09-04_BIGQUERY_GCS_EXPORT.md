# 任务报告：BigQuery 全文 GCS 导出路径（2026-09-04）

## 结论

GCS 中转导出已成功完成。当前 BigQuery 网页查询可以运行；网页结果本地下载曾受长文本行数限制，但 GCS 导出已绕过该限制并保留完整报告文本。无需再为 Codex 账号申请额外 Google API 权限。

## 已新增

- `project_control/bigquery/114_export_landmark12_radiology_to_gcs.sql`
- BigQuery README 的 GCS 导出和权限说明

## 用户侧需要准备

1. 在 Cloud Storage 创建或选择与 BigQuery 数据集同区域的私有 bucket；当前查询区域为 `US`。
2. 对自己的账号授予目标 bucket 的对象写入权限（通常为 `Storage Object Creator`；若要覆盖旧文件才需要更高的删除/覆盖权限）。
3. 在网页 BigQuery 中将 `YOUR_BUCKET` 替换为 bucket 名称，运行 114 SQL。
4. 从 GCS 下载生成的 Parquet 分片，并在本地核对 7,828 条报告、`(stay_id, note_id)` 唯一。

## 备用路径

若暂时无法创建 bucket，继续使用 112 SQL 的四批网页 CSV 导出；这不会改变研究设计，只是操作较慢。

## 当前边界

完整全文已从 `gs://ahf_bigquery_export/dhf_landmark12/radiology_raw_v1_000000000000.parquet` 下载并校验：7,828 行、27 列，`stay_id` 和 `note_id` 无空值，`text` 无空值，`(stay_id,note_id)` 无重复，唯一 stay 数 3,886；与 110 患者级汇总逐 stay 对账无差异（窗口报告总数 7,828，T12 前可见 6,415）。

本地已生成：

- `project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`
- `project_control/bigquery/dhf_radiology_report_audit_landmark12_v1.csv`
- `project_control/bigquery/landmark12_audit_20260904/`

完整文件校验：

- Parquet：`gs://ahf_bigquery_export/dhf_landmark12/radiology_raw_v1_000000000000.parquet`；SHA256 `f74bf81d98d351a8d4e47bbac867084509d26f1853b4ad444938c6a4ce78d214`
- 完整 CSV：`project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv`；SHA256 `bf742833fd2ba708fad9e20a0884636a2b02e6b80fbaef61679fcc41f40048e6`
- 两者均为 7,828 条报告、27列；`(stay_id,note_id)` 无重复；3,886 个 stay；与患者级汇总逐 stay 对账一致。

自动模态规则计数为 CXR 1,534、胸部 CT 315、其他/未分类 5,979；影像规则阳性和 DHF 表型仍需结合已完成的 300 条人工标注及人工 adjudication，不能把规则阳性直接写成确诊。

## 当前边界

`bq` CLI 查询仍可能在 BigQuery API 调用处超时，但 GCS storage 读写已经正常，且这不再阻塞本轮全文导出和本地审计。若后续必须把本地紧凑审计表回写 BigQuery，再处理 CLI/API 网络问题；当前研究分析可继续在本地完成。

300 条人工标注来自早期 pre-T0 抽样框。与新的 `[T0-24 h,T12)` 完整报告按 `(stay_id,note_id)` 仅重合 145/300；因此旧标注不能直接充当新主窗口的无偏验证集，链接审计见 `project_control/bigquery/landmark12_audit_20260904/DHF_ANNOTATION_LANDMARK12_LINKAGE_2026-09-04.md`。
