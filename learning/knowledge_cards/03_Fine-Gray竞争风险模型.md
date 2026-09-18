# 知识卡 03｜Fine-Gray 竞争风险模型

> 来源：第 3 课（2026-09-15）· 项目：CS_AHF 血流动力学恶化预测
> 本卡含**你自己 090 脚本的逐段精读**，可直接作为论文 Methods 的写作用料。

## 一句话本质

Fine-Gray 直接建模**累计发生率 CIF**：它的分母把"已发生竞争事件的人"以权重保留，因此回答的是"这位患者 48h 内的绝对风险是多少"，而不是"这个因素是否致病"。

## 核心概念

- **两种风险，差别只在分母**：
  - cause-specific hazard：分母 = 仍未发生任何事件的人（**排除**已发生竞争事件者）→ 机制/病因问题；
  - subdistribution hazard：分母 = 仍未发生事件的人 **+** 已发生竞争事件者（以权重保留）→ 预测/绝对风险问题。
- **CIF（累计发生率函数）**：竞争风险下要报告的绝对风险。把竞争当删失计算的 1−KM 会**系统性高估**（本项目竞争事件占 52.8%，高估幅度很大）。
- **`cmprsk::crr()` 参数**：`failcode = 1` 指定关心的事件，`cencode = 0` 指定行政截尾，其余编码（这里 2）按竞争事件处理。
- **`predict()` 返回 CIF 矩阵**：行 = 时间点，列 = 个体；取 48h 那一行即得预测绝对风险。
- **sHR（亚分布风险比）**：只能在同一模型内比较大小；论文中措辞必须写 subdistribution HR，不能简写成"HR"。

## R 代码模板

```r
library(cmprsk)
fit <- crr(ftime = df$time, fstatus = df$status, cov1 = X,
           failcode = 1, cencode = 0)      # 0=截尾, 1=事件, 2=竞争
sHR <- exp(fit$coef); se <- sqrt(diag(fit$var))

pred_cif <- predict(fit, cov1 = Xnew)      # 时间 × 个体 CIF 矩阵
cif_48   <- pred_cif[findInterval(48, pred_cif[, 1]), -1]

# 观测 CIF（校准/描述用，口径必须与模型一致）
est <- cmprsk::cuminc(ftime = df$time, fstatus = df$status, cencode = 0)
```

## 项目应用：090 脚本逐段精读

| 代码位置 | 做了什么 | 为什么必须这样 |
|---|---|---|
| 45 预测变量硬校验 | 变量数 ≠ 45 直接报错 | **预设定分析计划**，杜绝事后挑变量 |
| 分层 5 折（status × sepsis） | 按结局状态与脓毒症联合分层 | 事件仅 454 例，不分层可能某折事件只有个位数 |
| fold 内中位数填补 / 标准化 | 填补与缩放参数**只来自训练折** | 防止测试折信息泄露（嵌套 CV 的核心工程细节） |
| 4 个高缺失实验室指标 | 主模型不用，进预注册敏感性 | 保护 EPV（454/45 ≈ 10，已在及格线） |
| `failcode=1, cencode=0` | 明确事件与截尾编码 | 论文 Methods 必须交代清楚 |
| `predict()` → `step_cif_at()` | 取 48h 的 CIF 作为预测值 | 预测时点须预先固定（TRIPOD 要求） |
| 校准十分位 + `cuminc` | 分组内"平均预测 CIF vs 观测 CIF" | 分位数分组防小组；观测值用 CIF 保持口径一致 |
| 全样本拟合（注释 apparent） | 仅用于锁定/外部验证 | 表观性能 ≠ 内部性能，避免乐观偏倚 |

## 项目实测结果（v3.3）

- 样本：n = **5,555**；事件 454（8.2%）；竞争 2,935（52.8%）；截尾 2,166
- 判别（OOF）：48h time-dependent AUC = **0.762**
- 校准（OOF）：Brier = **0.0652**；Null model 0.0724（改善约 10%）
- 关键 sHR（连续变量为每 1 SD）：`bun_max` **1.148**（SE 0.058）、`chem_bicarbonate_min` **0.853**（SE 0.073）显著；`age` 1.019、`female` 0.879 不显著

## 易错点与审稿人常见问题

1. 把竞争当删失 → 高估绝对风险（本项目高估幅度会很大）；
2. 把 sHR 当普通 HR 解读 → 措辞错误，需明确写 subdistribution HR；
3. 校准用 1−KM 算观测 CIF → 与模型口径不一致；
4. 用全样本拟合的性能当内部性能 → 乐观偏倚；
5. 填补/标准化用全样本参数 → 信息泄露。

## Methods 段落模板（可改写直接使用）

> We analysed the association between pre-specified candidate predictors measured within the first 12 h after ICU admission and subsequent haemodynamic deterioration, accounting for the competing risk of alive discharge from the index ICU.
>
> The primary estimand was the cumulative incidence of haemodynamic deterioration between 12 h and 48 h, with alive ICU discharge treated as a competing event and administrative censoring at 48 h. We fitted a Fine-Gray subdistribution hazard model with 45 pre-specified predictors. Continuous predictors were standardised using training-fold means and SDs; missing values were imputed with training-fold medians. Missingness indicators for pre-specified high-missingness laboratory variables were examined in a sensitivity analysis.
>
> Internal validation used 5-fold cross-validation stratified jointly by outcome status and sepsis subgroup, with all preprocessing performed within training folds only. Out-of-fold predicted CIF at 48 h was used to estimate discrimination (time-dependent AUC) and calibration (decile-based calibration and Brier score benchmarked against a null model). The model was refitted on the full development cohort for future external validation; apparent performance was not used as a performance estimate. We report subdistribution hazard ratios (sHR) with 95% CI; cause-specific models are provided in the supplement.

## 一句话总结

"我们用 Fine-Gray 建模，是因为要预测的是患者的**绝对风险（CIF）**，而 **52.8% 的患者会活着离开 ICU**——这部分人不能从分母里被简单删掉。"
