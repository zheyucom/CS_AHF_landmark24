# 清洗知识的证据政策

## 来源优先级

1. **目标数据库当前 release 的字典与 schema**：决定字段、itemid、单位和来源语义。
2. **固定 commit 的官方 `mimic-code`**：提供可复核派生概念与聚合方式。
3. **有代码的公共框架**：用于比较流程设计；必须重新验证版本、队列、时间窗和缺失处理。
4. **同行评议论文**：用于提出方法候选和报告规范；论文发表本身不等于规则可直接激活。
5. **本地异常或模型观察**：只生成 `proposed` 规则，不能自动过滤数据。

数据访问权限是独立门控：能取得 OAuth token、执行 `SELECT 1` 或通过 SQL dry-run，只能证明连接/解析层可用，不能证明对 MIMIC 受控表有读取授权。目标表返回 `Access Denied` 时必须记录 `not_run_access_denied`，不使用未批准的镜像或导出绕过授权。

低层级来源不能覆盖高层级的目标数据库事实。任何来源发生冲突时，停止激活并记录冲突。

## 可迁移与不可直接迁移

通常可迁移的通用原则：

- 保留 raw provenance、单位和时间字段。
- 区分未测、结构性不可用、连接失败、超窗和派生表漏失。
- 在训练/验证划分后拟合插补与缩放，避免数据泄漏。
- 按患者或预注册分析单位分组拆分，避免同一人跨集合。
- 报告清洗前后计数、隔离原因、版本与代码 hash。

不能仅凭论文直接迁移：

- itemid、fluid、category、单位换算和 release 兼容性。
- 临床阈值、异常范围、winsorization 分位点和缺失补值。
- cohort、landmark、结局和 episode join。
- 把某篇论文的 derived 表、第一条/最后一条值或 24 小时窗口当作通用真值。

## 论文或公开代码纳入表

每个候选方法至少记录：来源、数据库/release、队列单位、index/landmark、变量时间窗、结局窗、原始表/derived 表、单位处理、异常值处理、缺失机制、数据拆分键、代码 commit、外部验证以及与当前项目的差异。

只有当差异已有明确处理，并完成失败夹具与回归测试，才可申请人工激活。

## 参考基线

- MIMIC-IV 数据说明：Johnson et al., *Scientific Data* 2023, <https://doi.org/10.1038/s41597-022-01899-x>。
- RECORD 常规医疗数据报告规范：Benchimol et al., *PLOS Medicine* 2015, <https://doi.org/10.1371/journal.pmed.1001885>。
- MICE 实践原则：White, Royston, Wood, *Statistics in Medicine* 2011, <https://doi.org/10.1002/sim.4067>。
- 官方派生概念：<https://github.com/MIT-LCP/mimic-code>，必须固定 commit。
- MIMIC-Extract、ricu、YAIB 等公共框架只作为可复核方法候选，不作为本项目自动真值。
