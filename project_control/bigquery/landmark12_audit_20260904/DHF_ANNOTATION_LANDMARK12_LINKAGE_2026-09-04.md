# 300条人工标注与 landmark-12 完整报告库链接审计

日期：2026-09-04

## 目的与边界

300条人工标注来自较早的 pre-T0 影像抽样框。本审计仅按 `(stay_id, note_id)` 与已验证完整的 `[T0-24 h,T12)` 报告导出进行精确链接，不对旧抽样重新加权，也不把链接子集的标签比例写成 landmark-12 窗口的 PPV、敏感度或特异度。

## 完整性与重合

| 项目 | 数量 |
|---|---:|
| 已完成人工标注 | 300 |
| landmark-12 完整报告 | 7828 |
| 精确链接成功 | 145 |
| 未在 landmark-12 窗口出现 | 155 |
| 链接率 | 48.3% |

## 链接子集描述（不是主窗口性能估计）

人工标签：definite_congestion=69, indeterminate=50, no_congestion=18, possible_congestion=8。

原始筛查层：negated_or_uncertain_screen=24, no_hit_screen=43, positive_rule_screen=78。

未链接记录按原始筛查层：negated_or_uncertain_screen=43, no_hit_screen=57, positive_rule_screen=55。

## 解释

这145条记录可用于检查旧规则与主窗口字段是否能稳定对接，并可作为报告级语义示例；但155条记录不在新窗口，说明 pre-T0 证据窗与 `[T0-24 h,T12)` 证据窗不是同一抽样总体。因此，最终主窗口影像规则验证需要从7,828条完整报告中按主窗口规则分层重新抽样，并由临床人员进行盲法标注。现有300条标注保留为历史规则验证和可迁移性审计。

## 产物

- 链接明细：`project_control/bigquery/landmark12_audit_20260904/dhf_annotation_landmark12_linkage_20260904.csv`
- 主窗口完整文本来源：GCS 导出的 Parquet，经本地行数、键唯一性和 stay-level 对账验证。
