# MIMIC-IV 实验室语义与可用时间审计 V2：不可变 cohort 快照重跑报告

日期：2026-09-18

## 结论

审计状态：**passed**。本次将审计输入从可变的候选表替换为不可变快照后重跑成功；结果与此前候选表审计按规范化行排序后完全一致。

该快照是“实验室审计用 cohort”，不是最终模型 cohort 冻结。DHF A/B/C 表型、T12 风险集、结局与医嘱代理等阻塞门控完成前，仍不得生成或宣称正式 `cohort_freeze.csv` 或最终模型性能。

## 输入快照

- 候选源表：`project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_candidates`
- 源表行数：5,555；其中 `admittime <= intime` 的有效边界行：5,549。
- 快照表：`project-9386bb9f-de39-47eb-886.ahf_work.dhf_lab_audit_cohort_snapshot_20260918`
- 快照唯一 stay：5,549；字段为 stay/subject/hadm、admittime/intime 及三项候选标志。
- 快照内容指纹：`0e45841c8593460108ca0208f20ef52737d80c98f4c12845624c5e966871dcd1`（按 stay_id 排序后串联 8 个字段计算 SHA-256）。

## 执行证据

- MIMIC release：3.1。
- SQL SHA-256：`fbf97b9d85197aac4c5a1060129e492ec8d4acf7702af0a74203d43c5bbc1ba3`。
- BigQuery job：`bqjob_r17bb02d22a10b0c_000001a0b3db8bfd_1`，区域 US。
- 处理字节：15,924,400,093；计费字节：16,104,030,208；slot-ms：215,358。
- 输出：32 行聚合结果；不含 subject_id、hadm_id、stay_id 或 labevent_id。
- 规范化结果 SHA-256：`50c5e85d9c991764709e22ca5fda41fa55f720905c0632513be8e7ae97e59d96`。
- 中间 scratch 表已由 runner 清理；`ahf_work` 中只保留快照及原有业务表。

## 核心质量结果

| 概念 | raw 合同内且早于 T12 | quarantine | raw/derived 覆盖 |
| --- | ---: | ---: | --- |
| BUN | 6,918 | 1,028（644 late；384 尿液） | both 6,917；derived_only 644；raw_only 0 |
| 乳酸 | 4,932 | 38 late | both 3,803；derived_only 29；raw_only 1,128 |
| 肌酐 | 6,937 | 649 late | 本次未做 derived 对账 |
| pH | 6,413 | 46 late | 本次未做 derived 对账 |
| NT-proBNP | 639 | 146 late | 本次未做 derived 对账 |
| Troponin T | 3,384 | 416 late | 本次未做 derived 对账 |

6/6 字典合同匹配。BUN 的 `itemid=51104`（尿液）384 条全部隔离为 `wrong_fluid_urine`，没有进入血 BUN。derived chemistry 没有 storetime，不能绕过 raw 的 T12 可用时间门控。

## 代码与回归修订

- `MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql` 现在只读快照表。
- `MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.md` 已记录快照审计边界。
- 项目回归测试的 derived 数据集断言已兼容 MIMIC-IV 2.2 与 3.1；当前 3.1 测试通过 8/8。
- 输出文件：`MIMIC_LAB_AUDIT_V2_RESULT_20260918_COHORT_SNAPSHOT.csv`；运行日志：`MIMIC_LAB_AUDIT_V2_RUN_20260918_COHORT_SNAPSHOT.log`。

## 冻结规则

后续正式特征只能从 raw 中选择：

1. 精确 itemid × fluid × category × unit 合同匹配；
2. `availability_time < T12`；
3. 不属于 late、wrong-fluid、unknown-unit、duplicate 或其他 quarantine；
4. raw/derived 差异不静默回填；derived 仅用于覆盖审计和预设敏感性分析。

最终 DHF 队列冻结后，必须复制快照、更新 cohort 引用、重算同一 SQL/hash，并重新保存本报告中的审计证据。
