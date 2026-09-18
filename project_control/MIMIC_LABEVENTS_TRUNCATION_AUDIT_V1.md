# MIMIC `labevents` 截断值审计 v1（历史）

状态：`superseded_not_run`。

本模板已被以下文件取代：

- 候选发现：`MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql`，只读 `d_labitems`。
- 正式审计：`MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql` 与配套说明。

V1 用名称正则直接形成 `labevents` 范围，未强制精确 itemid、fluid/category/unit、结果可用时间和 raw/derived 双向对账，因此不得再用于实验室特征冻结。保留本文件仅为历史追溯。

SQL 开头已加入 `ASSERT FALSE`，误执行时会在读取患者级表之前硬停止并指向 V2。

## V1 中仍有效的原则

- `>x` 保存 lower bound，不能改写为精确值。
- `<x` 保存 upper bound，不能补为 0。
- 区间值保留上下界，不能静默取中点。
- 原始 `value`、`valuenum`、`valueuom` 与来源键必须保留。
- 未执行的模板只能标记 `not_run`，不能写成实际数据审计结果。

以上原则已经纳入 V2 的可测试合同；后续修改只进入 V2 或其继任版本。
