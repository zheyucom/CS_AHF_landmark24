# 任务报告：DHF BigQuery 查询执行

日期：2026-08-30  
状态：106/107 云端表已成功创建；原始报告和患者级汇总均已下载并通过本地 QC；盲法标注包已生成。

## 本轮完成

1. 通过已登录的 BigQuery 控制台确认候选表存在：
   `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_candidates`。
2. 第一次提交 106 暴露类型错误：Note radiology 的 `charttime/storetime` 为 `DATETIME`，候选表时间为 `TIMESTAMP`。
3. 修正本地 106 SQL，将候选时间边界转换为 `DATETIME`，重新提交成功。
4. 成功创建：
   `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_raw_v2`
5. 成功创建患者级汇总：
   `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_patient_summary_v1`
6. 下载并保存 [患者级汇总 CSV](../bigquery/dhf_radiology_patient_summary_v2.csv)，本地连接 QC 通过：5,549 个有效候选、5,549 个唯一 `stay_id`、无缺失候选、无重复。
7. 发现并核实 6 个 `admittime > intime` 的原始时间边界异常；未人为修正，已在 106/107 中显式排除，保留 5,549 个有效候选。
8. 下载 [4,303 条报告级原始记录](../bigquery/dhf_radiology_raw_v2.csv) 和 300 条分层抽样记录，生成完整导入 QC、每层 100 条盲法标注表和 60 条（20%）第二标注者复核表。

## 当前结果

| 指标 | 数值 |
|---|---:|
| HF anchor 候选 | 5,555 |
| 有效 admission/ICU 时间边界候选 | 5,549 |
| 排除的无效时间边界候选 | 6 |
| 有 pre-T0 radiology 报告 | 1,637 |
| 有 ICU 前可见报告（`storetime < intime`） | 1,346 |
| pre-T0 报告总数 | 4,303 |
| ICU 前可见报告总数 | 3,593 |
| 规则阳性患者 | 997 |
| 非不确定词的确定性筛查阳性患者 | 877 |
| ICU 前可见确定性筛查阳性患者 | 769 |

上述为 regex screening 数字，不是最终 DHF 诊断或主队列数字。

## 当前未完成

1. 对 `project_control/bigquery/controlled_annotation_20260830_v2/` 中 300 条报告完成临床标注和 20% 双盲复核。
2. 用最终人工标签评估规则筛查的 PPV、漏检风险、否定/不确定误触发和替代解释。

```sh
project_control/bigquery/controlled_annotation_20260830_v2/
```

3. 完成临床标注后，建立最终 `DHF candidate`、`radiology-supported DHF` 和 `multidomain DHF` 分层，重算事件数和 EPV。

## 研究边界

106/107 只构建 pre-T0 DHF 表型证据，不向 T0-T12 预测器加入报告文本，也不读取或使用 T12 后结局。影像 regex 仍需人工验证，不能直接作为金标准。
