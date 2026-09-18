# MIMIC-IV 实验室语义与可用时间审计 V2：正式执行报告

日期：2026-09-18

## 状态

审计状态：**passed**（已完成授权表读取、实际患者级聚合、结果回收和中间表清理）。

这不是“所有实验室字段都可直接冻结”的结论；模型特征仍必须使用通过合同和时间门控的 raw 结果，并保留 quarantine 与 raw/derived 差异。

## 执行证据

- MIMIC release：3.1。
- BigQuery 源表：`physionet-data.mimiciv_3_1_hosp`、`physionet-data.mimiciv_3_1_derived`。
- 活动账号：`zheyu.sy@gmail.com`。
- 审计队列：5,555 个唯一 stay。
- SQL SHA-256：`bfba5fd2334811dbf98245989e827dc777f654054861cc3a9069dcda86867722`。
- BigQuery job：`bqjob_r3188fcdd209c181f_000001a0b3a0460e_1`，区域 `US`。
- 处理字节：15,924,400,333；计费字节：16,104,030,208；slot-ms：235,312。
- 输出：32 行聚合结果，未导出 subject_id、hadm_id、stay_id 或 labevent_id。
- 结果文件：[MIMIC_LAB_AUDIT_V2_RESULT_20260918.csv](MIMIC_LAB_AUDIT_V2_RESULT_20260918.csv)。
- 运行日志：[MIMIC_LAB_AUDIT_V2_RUN_20260918.log](MIMIC_LAB_AUDIT_V2_RUN_20260918.log)。

## 关键结果

| 概念 | raw 合同内且早于 T12 | quarantine | raw/derived 覆盖 |
| --- | ---: | ---: | --- |
| BUN | 6,918 | 1,028（644 late；384 尿液） | both 6,917；derived_only 644；raw_only 0 |
| 乳酸 | 4,932 | 38 late | both 3,803；derived_only 29；raw_only 1,128 |
| 肌酐 | 6,937 | 649 late | 未做 derived 对账 |
| pH | 6,413 | 46 late | 未做 derived 对账 |
| NT-proBNP | 639 | 146 late | 未做 derived 对账 |
| Troponin T | 3,384 | 416 late | 未做 derived 对账 |

字典合同 6/6 匹配：BUN 51006、乳酸 50813、肌酐 50912、pH 50820、NT-proBNP 50963、Troponin T 51003。

BUN 的 51104（尿液）全部进入 `wrong_fluid_urine`，没有混入血 BUN。BUN 的 `derived_only` 不能直接解释为 raw 缺失：derived chemistry 没有 storetime，而 raw 审计要求结果在 T12 前可用；因此不能用 derived 值绕过可用时间门控。

## 执行环境限制与处理

该 GCP 项目禁止 BigQuery 脚本自动创建 `_script...` 临时数据集，因此原 SQL 的 `CREATE TEMP TABLE` 在正式执行时触发 IAM policy 错误。没有绕过该策略；本次使用项目 `ahf_work` 中受控的永久 scratch 表执行，输出完成后立即删除全部 15 张中间表，并复核为空。

为保证后续可复现，新增 [run_mimic_lab_audit_v2.sh](../run_mimic_lab_audit_v2.sh)。脚本将 SQL 转为项目受控 scratch 执行形式，设置 20 GB 计费上限，保存聚合 CSV/日志，并通过 trap 清理中间表。

## 决策

1. 实验室语义合同和 BUN 体液污染隔离通过。
2. raw 特征只能使用 `eligible` 且 exact contract 的记录；late、wrong-fluid、未知单位、重复等继续隔离。
3. raw/derived 不得静默互相回填；BUN 与乳酸覆盖差异要作为敏感性或数据来源说明。
4. 审计已通过，但在最终模型队列冻结前仍需固定最终 cohort 快照，并重新运行同一 SQL/hash。
