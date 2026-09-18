# 任务报告：完整主窗口影像标注包已生成

日期：2026-09-04 Asia/Shanghai

## 本次完成

- 使用 GCS 下载并校验的完整主窗口 CSV：`7,828` 行、`3,886` 个 stay。
- `(stay_id, note_id)` 全部唯一；`storetime` 无缺失。
- 影像报告窗口：`[T0-24 h, T12)`；报告在 T12 前可见：`6,415` 条，T12 后才可见：`1,413` 条。
- 从完整主窗口按三层重新抽样：规则明确阳性、否定/不确定、无命中，各 `100` 条。
- 生成第二位标注者的 `60` 条盲法复核抽样框，占第一轮 `20%`。

## 产物

- 标注包目录：`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/`
- 第一位标注者：`dhf_radiology_annotation_round1.csv`；同时保留 T0 前与 T12 前可见性字段
- 第二位标注者：`dhf_radiology_annotation_round2_blinded.csv`
- 受限抽样键：`dhf_radiology_sampling_key_restricted.csv`
- 包内 QC：`README.md`

## 脚本修复

批量导出列名是 `report_available_by_t12_flag`，旧准备脚本要求不存在的 `report_available_pre_t0_flag`，已改为兼容完整批量导出。标注包中的 T0 前可见性由 `storetime < intime` 独立计算，不复用错误的派生列。

完整导出自身携带 `admittime/intime/window_start/landmark12_time`，脚本已使用这些经过主窗口审计的边界；旧 pre-T0 候选 CSV 不再用于验证新窗口。

## 数据质量发现

旧候选时间表有 `stay_id=30054141` 的 `admittime > intime` 异常，但该 stay 不在完整 7,828 条主窗口报告中。不能据此修改或填补时间；本次标注包按完整导出内的主窗口边界完成，包内有效窗口边界 stay 数为 `3,886`。

## 下一步

1. 第一位标注者完成 300 条：按指南填写 `congestion_label`、`alternative_explanation_label`、`comments`。
2. 第二位标注者独立、盲法完成 60 条；不能复制第一位标签。
3. 回收后运行 QC/合并脚本，计算报告级 PPV、分层结果和独立一致性。
4. 依据人工结果冻结 DHF 证据层级，再重算最终建模队列、事件数、EPV 和模型输入。

## 边界

这 300 条是主窗口的规则验证样本，不是 7,828 条报告的人工全量确诊。心超、临床失代偿和治疗强化仍需在患者级多域表型中独立整合；放射科文本不能单独替代 DHF 临床诊断。
