# Pre-T0 AHF Cohort Screening Audit

日期：2026-08-25  
审计对象：MIMIC-IV v4/v4.2 队列构建  
目的：核查“ICU 入科前已存在 AHF”筛选是否正确，以及解释 v4.2 的 452 例。

## 结论先行

研究原则没有问题：

> 若研究问题是“入 ICU 前已经存在 AHF 的患者，在 ICU 最初 12 h 信息基础上预测随后 48 h 恶化”，则 AHF 的时间证据必须发生在 ICU `intime` 之前。

但 v4.2 的 `452` 例不能直接作为最终正式队列，原因是当前 `093A` 实现存在时间边界问题：

1. `093A` 没有显式连接 `cohort_061D_landmark12_riskset_main_v1`，虽然审计发现 452 例最终全部属于该 risk set，未造成实际行数差异；
2. `093A` 只限制了证据时间早于 ICU `intime`，没有限制证据时间晚于本次住院 `admittime`；
3. 因此，部分 NT-proBNP/eMAR 记录发生在 `admittime` 之前，却被当作本次住院的 pre-T0 AHF 证据。

所以，452 例是一个**历史 v4.2 探索性结果**，需要标记为 superseded，不能直接作为最终论文队列。

## 当前筛选流程

| 步骤 | 条件 | stays |
|---|---|---:|
| 1 | 成人、每位患者首次 ICU stay | 65,366 |
| 2 | HF ICD candidate | 14,877 |
| 3 | strict AHF 12 h candidate | 7,749 |
| 4 | ICU stay 达到 12 h landmark | 7,543 |
| 5 | 排除 0-12 h pre-overt-CS proxy | 6,462 |
| 6 | strict pre-T0 AHF，原 v4.2 24 h 写法 | 452 |

上述前 5 步没有发现重复 stay 或 SQL 执行错误。真正需要修正的是第 6 步的时间边界。

## 452 例的组成

在原 v4.2 队列中：

- 452 stays；
- 34 个主结局事件；
- 452 例均达到 12 h landmark；
- 452 例均未触发 pre12 overt-CS 排除；
- stay_id 无重复；
- 81 例有 pre-T0 IV loop eMAR；
- 380 例有 pre-T0 NT-proBNP `>=300`；
- 9 例同时具备两类证据。

但部分证据早于该次住院 `admittime`，因此需要重新界定为合法的 index-hospital evidence。

## 校正后的两个可执行口径

### 推荐主口径：本次住院入院至 ICU 入科前

```text
T0 = ICU intime
pre-T0 evidence window = [hospital admittime, T0)

acute/acute-on-chronic HF ICD
AND HF ICD sequence <= 5
AND (
    actual IV loop diuretic eMAR before T0
    OR NT-proBNP >= 300 before T0
)
```

在当前 6,462 例 landmark risk set 中：

- 562 stays；
- 57 个主结局事件；
- 事件率 10.14%；
- 268 例 ICU 观察达到 60 h。

该口径最符合“入 ICU 前已经存在 AHF”，也最容易与本院按住院号、给药时间和检验时间复刻。

### 严格敏感性口径：ICU 入科前 24 h

```text
pre-T0 evidence window = [T0 - 24 h, T0)
```

在当前 risk set 中：

- 280 stays；
- 29 个主结局事件；
- 事件率 10.36%；
- 134 例 ICU 观察达到 60 h。

该口径更严格，但样本量和事件数明显不足，不建议作为主模型开发队列。

## 为什么人数会少

人数减少不是因为 AHF 研究方向本身错误，而是因为同时叠加了多个合理但严格的条件：

1. 只保留成人首次 ICU stay；
2. 必须有较靠前的 HF ICD；
3. 必须有 acute/acute-on-chronic HF ICD；
4. 必须有 ICU 入科前的客观时间证据；
5. 必须达到 12 h landmark；
6. 必须排除 0-12 h 已有 overt shock proxy。

其中最主要的收缩来自“pre-T0 客观证据”要求，而不是 landmark 设计本身。

## 是否需要改变研究方向

不建议放弃“pre-T0 AHF + ICU 0-12 h 预测未来 48 h”的核心方向。这个时间逻辑是正确且具有临床意义的：

```text
入 ICU 前已经是 AHF
        ->
观察 ICU 0-12 h 动态状态
        ->
预测 12-60 h 后续血流动力学恶化
```

需要改变的是队列的操作化实现：

- 主分析采用 `[admittime, T0)`；
- `[T0-24h, T0)` 作为严格敏感性分析；
- 不再使用含有 pre-admittime 记录的历史 452 例；
- 最终 discharge ICD 只作为回顾性 phenotype anchor，不作为实时预测变量。

## 对 early sepsis 主研究的影响

在同一 corrected AHF 逻辑下：

- strict pre-T0 AHF 24 h + 当前 early-sepsis 条件：约 53 stays，8 events；
- strict pre-T0 AHF admission-to-T0 + 当前 early-sepsis 条件：约 73 stays，10 events。

这两个样本量都不足以支撑稳定的高维机器学习主模型。因而当前最稳妥的研究分层是：

1. **主要模型开发/可行性分析**：strict pre-T0 AHF-only，admission-to-T0，约 562 stays、57 events；
2. **AHF + early sepsis**：作为预设的高特异性目标亚群/敏感性分析，约 73 stays、10 events；
3. 待本院数据或更宽但仍可复刻的 sepsis 定义确认后，再决定是否把 AHF + early sepsis 提升为主模型。

## 必须执行的下一步

1. 新建校正后的 pre-T0 AHF SQL：
   - 显式连接 `cohort_061D_landmark12_riskset_main_v1`；
   - 所有 eMAR/lab 证据限制在 `[admittime, T0)`；
   - 输出 admission-to-T0 主队列和 24 h 敏感性队列。
2. 重新生成 AHF-only modeling dataset；
3. 暂不使用旧 452 例结果作为正式模型结果；
4. 先用低维、预先指定特征重跑 AHF-only feasibility model；
5. 将 AHF + early sepsis 结果保留为特异性亚组，不因样本量不足而放弃 AHF pre-T0 核心定义。

## 最终判断

`T0 前已经存在 AHF` 这个条件应当保留，而且是研究设计的关键。  
问题不在研究方向，而在旧 v4.2 SQL 把部分 `admittime` 之前的记录纳入了 pre-T0 证据，并将其结果直接称为 452 例。正式分析应以校正后的 562 例 admission-to-T0 队列为候选主队列，以 280 例 24 h 队列为严格敏感性分析。
