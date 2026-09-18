# 任务报告：成人分母锁定与 Gate 3 续行

日期：2026-09-13

## 已完成

- 用户裁决患者 `9204020`（男，出生日期 `2006-01-01`，2023-01-09 就诊，年龄 17 岁）按年龄 `<18` 排除。
- 院内成人 index ICU 分母正式锁定为 8,385 名患者、8,653 个候选就诊号；性别分层为女 2,842、男 5,543。
- 原始 `DHF_SRR` 未修改；分母差异病例保留在 `denominator_discrepancy_9204020.csv` 作为审计证据。
- Gate 3 50 例人工裁决已叠加到全 ICU 三级表型审计表：50 例已审核，8,335 例仍为 `pending_human_review`。
- 已生成 45 例 Gate 3 语义优先队列；仅包含 HF 锚点、失代偿、管理强化或综合层级仍需临床确认的病例，不重复请求已确认的 T0/episode 信息。

## 当前可用的三级审计数字

- 窗口内床旁心超完成：2,519/8,385。
- 结果可用：2,517/8,385。
- 文本异常支持草稿：2,475/8,385；仍不是人工金标准。
- 50 例用户裁决层级：`multidomain_draft` 4、`echo_supported_draft` 30、`unknown` 15、`not_supported` 1。
- 全量表当前层级计数：已审核草稿 50 例，`pending_human_review` 8,335 例；未将自动规则结果冒充最终 DHF 标签。
- 全量 event/competing/censor 仍不能计算，因当前导出未提供可审计的执行级治疗升级和完整 ICU 结局编码。

## 下一执行顺序

1. 临床完成 50 例 HF anchor、失代偿、管理强化和 ICU 结局语义确认；不再重复询问已裁决的 T0、G3-001、G3-043 或四例 ICU 时间。
2. 以 50 例裁决结果修订规则，保留版本号、证据句和替代诊断标签。
3. 对 8,385 名成人 index ICU 患者全量运行同一规则，输出 DHF 三级表型、心超三态和人工复核抽样框。
4. 在结局字段补齐后重算 event、竞争事件、删失，并据事件数冻结 MIMIC 主模型预测器数量。
5. 锁定 MIMIC 开发模型后，原样映射到院内 `echo-supported DHF` 外部验证队列，并报告全 ICU 分母到严格队列的选择性。

## 交付文件

- [全 ICU 三级表型审计表](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_dhf_three_tier_audit_20260913.csv)
- [三级表型 QC](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_dhf_three_tier_audit_qc_20260913.json)
- [50例 reviewed 表](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_reviewed.xlsx)
- [Gate 3 语义优先队列](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_semantic_priority_queue_20260913.csv)
- [研究总览](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/RESEARCH_DASHBOARD.md)
