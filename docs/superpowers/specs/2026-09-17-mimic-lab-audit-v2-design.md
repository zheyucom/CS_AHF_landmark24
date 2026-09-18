# MIMIC-IV 实验室审计 V2 设计

日期：2026-09-17

## 决策

保留 V1 作为历史模板，新建 V2 并将项目入口切换到 V2。名称正则与患者级提取物理分离：前者只查询数据字典并提出候选，后者只接受精确数据合同。

## 数据流

1. 字典候选发现：`d_labitems` → active/known quarantine/proposed candidate，不读取患者行。
2. 精确合同校验：运行时用目标库 `d_labitems` 对比 itemid、label、fluid、category，不匹配即 `ASSERT` 失败。
3. 当前审计框架：从现有 `dhf_radiology_candidates` 取唯一 stay，构建 `[T0,T12)`。
4. raw 审计：保留来源字段，以结果可用时间门控，按显式 reason code 隔离语义、单位、时间、episode 和重复问题。
5. 覆盖审计：BUN/乳酸分别对账 raw-only、derived-only、both；derived 不替代 raw 可用时间。
6. 聚合输出：只输出合同、隔离与覆盖计数，不默认输出患者标识。

## 规则学习

新论文、公开代码或本地异常只能产生 `proposed` 规则。激活顺序固定为：来源核验、最小失败夹具、修复后回归、相邻规则检查、人工批准。数据集字典和官方 `mimic-code` 决定 MIMIC 语义；论文方法只能补充流程或候选，不能覆盖目标 release 的真实字段。

## 验收

- 结构测试覆盖精确合同、BUN 错误体液、T12 可用时间、原值/删失、重复、quarantine 和双向覆盖。
- 清洗 Skill 静态扫描无硬失败。
- BigQuery dry-run 通过后才能声明语法验证；正式汇总执行后才能填患者级计数。
- 网络或权限不可用时保持 `not_run`。
