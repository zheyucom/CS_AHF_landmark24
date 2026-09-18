# 任务报告：近期文献与 MIMIC 清洗方法复核

日期：2026-09-17

## 1. 用户问题与本轮范围

复核近期 DHF/血流动力学恶化预测文献、公开 MIMIC 清洗框架和可复用 Skill，重点判断实验室标本污染能否被系统性阻断。本轮不运行患者级 BigQuery，不更改队列、结局或正式模型。

## 2. 使用的文件、版本和数据状态

- 项目合同：`project_control/RESEARCH_DASHBOARD.md`。
- 现有审计：`MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql/.md`，状态仍为 `not_run`。
- `MIT-LCP/mimic-code` commit `303d26c623dcc9c49cc0f204468d4acc2f063797`。
- 同步审阅 MIMIC-Extract、ricu、YAIB、MIMIC-IV Data Pipeline 和 BAN-ADHF 公开源码；未接触患者级数据。

## 3. 已验证事实与证据

- 官方 `chemistry.sql`：BUN 只用 `itemid=51006`，`0 < valuenum <= 300`，按 `specimen_id` 聚合。
- 官方 `bg.sql`：乳酸用 `itemid=50813`，保留标本描述、`charttime` 和最新 `storetime`，按 `specimen_id` 聚合。
- MIMIC-Extract 显式区分 blood BUN 与尿/其他体液/腹水项目；ricu 同样用固定 itemid 而非名称模糊匹配。
- YAIB 的 recipe 在训练集拟合后再应用到验证/测试集，但拆分键由 group 配置决定，不能默认等同患者级拆分。
- MIMIC-IV Data Pipeline 的多数单位保留和经验分位数截尾不满足本项目的 fail-closed 审计要求。
- TvHEWS 的 MIMIC 外部 recall 降至 0.36；病例/对照锚点不对称，且外部 alpha 调整不能作为严格锁模验证。

## 4. 判断与影响

当前最大风险不是缺少新算法，而是实验室概念污染、结果可用时间和 derived 覆盖漏失。公开框架只能提供零件，没有一个同时满足本项目的时间合同、标本合同、raw provenance 和双向对账。

## 5. 新增或确认的研究决策

1. 实验室特征采用预登记 `itemid × fluid × category × unit` allowlist；名称正则仅用于候选发现。
2. 变量门控至少要求 `GREATEST(charttime, COALESCE(storetime, charttime)) < T12`，并同时保留两种时间。
3. 核心变量必须做 raw→derived 与 derived→raw 双向 anti-join，按 stay/标本/时间窗报告。
4. 隔离异常值并记录 reason code；不静默截尾、删除、换算或把缺失当 0。
5. 动态模型仅作冻结后补充；严格外部验证不在目标库调阈值。

## 6. 未决问题、阻塞项和假设

- 患者级 BigQuery 审计仍未运行，当前结论是规则与源码审计，不是数据结果。
- `charttime/storetime` 空值和时间逆序分布仍需实际审计；异常行进入隔离表，不放宽上述可用时间门控。
- 乳酸 derived 漏失的 550 个 stay 需按标本、时间、单位和 join 路径分层定位。

## 7. 下一步动作

扩展并运行实验室审计，优先完成 BUN 和乳酸的精确 allowlist、结果可用时间、隔离原因和 raw/derived 双向覆盖；再将通过验证的规则纳入 MIMIC 清洗 Skill。

## 8. 本轮修改文件

- 新增本任务报告。
- 新增 Obsidian `近期文献与MIMIC清洗方法-2026-09-17.md`。
- 精简更新 Obsidian 文献知识地图和项目总览索引。

## 9. 可重复性信息

无模型运行、随机种子或患者级输出。公开源码 commit 与链接已记录在 Obsidian 方法复核中；项目审计 SQL 状态保持 `not_run`。
