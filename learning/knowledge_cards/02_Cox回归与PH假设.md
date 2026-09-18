# 知识卡 02｜Cox 回归与 PH 假设

> 来源：第 1 周第 2 课（2026-08-27）· 项目：CS_AHF 血流动力学恶化预测

## 一句话本质

Cox 回归给出的是"协变量每变化一单位、瞬时风险乘多少倍"（HR），但这个倍数只有在**不随时间改变**（比例风险 PH）时才是一个有效的单一数字。

## 核心概念

- **HR 的解读**：HR = exp(β)，连续变量表示"每 +1 单位风险的倍数"，分类变量表示"相对参照组的倍数"。HR 是**瞬时风险**之比，不是概率之比。
- **PH 假设**：两组（或任意 X 取值）的风险比在随访期内恒定，即 h(t) 曲线等比例。PH 成立时，KM 曲线不交叉、log-log 图平行。
- **cox.zph()**：Schoenfeld 残差与时间的相关性检验。输出每变量 rho（相关系数，接近 0 好）、chisq、p，及 GLOBAL 整体检验。p<0.05 = 违反。
- **log-log 图**：横轴 log(时间)、纵轴 log(−log(S(t)))。PH 成立 → 各层曲线平行；相交或发散 → 违反。
- **处理方案**：
  - `strata(x)`：分层，允许各层基线风险形状不同，但**不报告 x 的 HR**；
  - `tt(x)` 时间交互：如 `tt = function(x,t,...) x*log(t)`，报告"HR 随时间变化"；
  - 分段（piecewise）：`survSplit()` 按时间切段，各段分别估计 HR。
- **log-rank 的局限**：两曲线交叉时，log-rank 对各时刻加权后可能"正负相消"，导致检验失效——此时应报告两段各自的 HR 或时间交互项。

## R 代码模板

```r
library(survival)

fit <- coxph(Surv(time, status) ~ age + sofa + group, data = df)
summary(fit)                 # HR 与 95%CI
print(cox.zph(fit))          # PH 检验

# 方案 A：分层
fit_strat <- coxph(Surv(time, status) ~ age + sofa + strata(group), data = df)

# 方案 B：时间交互
fit_tt <- coxph(Surv(time, status) ~ age + sofa + group + tt(group),
                tt = function(x, t, ...) x * log(t), data = df)

# 方案 C：分段
df2 <- survSplit(Surv(time, status) ~ ., data = df, cut = c(24, 48))
fit_piece <- coxph(Surv(time, status) ~ group:segment, data = df2)
```

## 项目应用（CS_AHF）

- 项目的 T12 landmark 结构天然提示"风险可能两段式"：T12 前是预测窗口（不建模），T12-T60 是随访窗口——这就是隐式的分段思想。
- 若某个预测变量（如 SOFA、血管活性药基线水平）的 PH 检验显著，主分析 Fine-Gray 也需同样检查（竞争风险下可用 Schoenfeld 类似方法或分层），并在论文中报告。
- 时间交互项特别适合本项目：血流动力学恶化的风险很可能"随时间衰减"（早期窗口最危险）。

## 易错点与审稿人常见问题

| 问题 | 后果 | 应对 |
|---|---|---|
| HR 当成"概率比/相对风险" | 临床解读错误 | 强调是瞬时风险之比 |
| PH 违反仍报单一 HR | 结果无意义、审稿人必拒 | 先 cox.zph，违反则分层/交互/分段 |
| log-rank 在交叉时下"无差异"结论 | 假阴性 | 用 weighted log-rank 或分段分析 |
| 只报 P 不报 HR/CI | 信息不足 | 报告 HR 与 95%CI |

## 一句话总结

"PH 成立时一个 HR 讲完整故事；PH 违反时我们不用单一 HR 硬撑，而是分层、时间交互或分段，把'风险随时间怎么变'如实报告出来。"
