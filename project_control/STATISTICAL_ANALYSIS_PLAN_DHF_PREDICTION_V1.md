# DHF ICU 血流动力学恶化预测：统计分析计划 v1.0

更新时间：2026-09-01  
状态：用于最终 DHF 表型冻结后的建模合同；在锁模后不得根据结果临时改换主模型或筛选规则

2026-09-15执行对照补记（不改变既有SQL）：当前MIMIC的`061C_create_pre12_overt_cs_flags.sql`主排除标志为前12h血管活性药使用且乳酸最大值>=2，`061D_create_landmark12_riskset.sql`据此构造T12风险集；不能把旧文中“pre-T0”泛称当成实际代码窗口，也不能推断IABP/ECMO单独构成该排除标志。院内以现有文书/医嘱先形成同口径代理和缺失标志，缺乳酸不证明无休克；机械支持、已存在的恶化状态及相对基线升级须分别审计。未修改或重跑最终模型，旧样本量/性能均为可行性资料。当前队列与开题正文见`RESEARCH_DASHBOARD.md`和`PROPOSAL_METHODS_DRAFT_20260915.md`。

## 1. 先回答核心问题：为什么不是把所有模型都跑一遍

本研究是临床预测模型开发，不是寻找某个方法得到最小 P 值的模型比赛。模型必须回答同一个、预先定义的预测问题：

> 在 T0=首次 ICU 入科、T0-T12 的信息可用后，预测 T12 至 60 h 内治疗升级相关 ICU 血流动力学恶化或 ICU 内死亡的累积发生风险；alive ICU discharge 是竞争事件。

因此主模型必须与结局的时间结构和竞争事件一致。Fine-Gray 直接建模目标事件的累积发生函数（CIF），所以作为主模型有明确的估计对象。增加大量不同模型并不会自动提高论文档次，反而会带来：

- 同一数据反复试错造成乐观偏倚；
- 多重比较和模型选择不确定性没有被反映；
- 普通二分类模型忽略提前出 ICU 的竞争事件；
- 不同模型实际上回答不同问题，却被放在同一 AUC 表中比较；
- 小事件数下高维树模型的结果不稳定、难以外推。

本研究采用“一个与临床问题匹配的主模型 + 一个时间离散化补充模型 + 少量预先说明的敏感性/基准模型”的结构。模型多样性服务于验证假设，不服务于挑选最好看的数字。

## 2. 分析对象、时间和结局

| 项目 | 预设定义 |
|---|---|
| 分析单位 | 每名患者的首次 index ICU stay；每 stay 一行用于 stay-level 模型 |
| 入组表型 | DHF operational phenotype；candidate、radiology-supported、multidomain 三层先经人工标注和导师确认 |
| 预测窗口 | `[T0,T12)`；所有插补、标准化和变量选择只能使用训练折内资料 |
| 风险窗口 | `T12` 起至 `min(T60, alive ICU discharge)` |
| 主事件 | treatment-escalation-based ICU hemodynamic deterioration + ICU 内死亡的 composite |
| 竞争事件 | alive index-ICU discharge |
| 行政删失 | T60 仍在 ICU 且尚未发生事件 |
| 主估计量 | 48 h 目标事件 CIF 及其个体风险排序 |

ICU 内死亡保留在 composite 主事件中，因为本研究的临床问题是识别随后进入严重循环支持/死亡状态的患者；component-specific event、strict shock/CS-like proxy 和去除死亡的结局作为预设次要/敏感性分析，而不是临时改写主终点。

## 3. 变量进入模型的规则

### 3.1 变量选择的第一层：研究合同，而非 P 值

候选变量先按以下顺序冻结：

1. 临床合理性：年龄、入口类型、T0-T12 生理状态、灌注/肾功能、呼吸支持、液体/尿量和支持治疗结构。
2. 时间合理性：变量必须在 T12 前可获得，且不能复述 T12 后结局或其计算基线。
3. 数据质量：报告测量频率、缺失率、异常值规则和单位转换。
4. 相关性管理：同一生理域保留少量互补摘要，避免将同一信号的 `mean/min/max/delta` 全部机械堆入模型。
5. 复杂度门槛：最终表型冻结后重新计算事件数、有效参数数、收缩程度和校准精度；不能因为 broad 队列可容纳 45 个特征，就把同样数量搬到更小的 multidomain 队列。

当前 `FEATURE_FREEZE_V33.md` 中的资格变量、结局列、时间锚点、pre-T0 overt CS 资格列和 outcome-derived support 聚合列继续属于黑名单。

### 3.2 单因素分析不用于筛选预测变量

基线表用于描述入组人群和不同结局状态的分布：连续变量报告均值/标准差或中位数/四分位数，分类变量报告计数/百分比，并优先报告标准化差异。单因素 P 值不是变量进入多因素模型的门槛。

原因是单因素筛选会漏掉联合预测、放大选择偏倚，使模型性能和系数在新样本中下降；“单因素 P<0.05 后多因素”也不能解决事件数不足或时间依赖问题。

Fisher 精确检验只在描述性表格中存在小期望频数时使用。它不用于挑选特征，也不用于证明某变量具有独立预测价值。

### 3.3 主模型的候选集

主模型使用锁定的紧凑候选集。对当前 broad v3.3 队列，45 个候选变量约对应 `454/45=10.1` 个名义事件/变量；这只是警戒性审计，不替代 Riley 等现代样本量框架。DHF 表型确定后必须重新计算。

若最终队列仍能支持紧凑候选集，则主分析使用临床预先指定变量的 Fine-Gray 模型，并通过内部验证估计过拟合和校准。若事件数下降导致复杂度不足，按预先规则减少“有效参数”或增加收缩，不允许先跑完全部模型再挑结果。

## 4. 主模型与其他模型的分工

### 4.1 主模型：Fine-Gray

Fine-Gray 用于直接估计目标事件在存在 alive ICU discharge 竞争风险时的 CIF。主文报告：回归系数/亚分布风险比及 95% CI、48 h CIF、校准、时间依赖 AUC、Brier 分数、风险分层和决策曲线。

它是本研究的主模型，不是因为它“高级”，而是因为它与预先写定的 estimand 一致。解释应使用“累积发生风险/风险排序”，不把 subdistribution HR 写成病因学因果效应。

### 4.2 补充模型：1 h person-period

将风险窗口拆成 1 h 区间，使用离散时间多状态/多项 hazard 结构，检查 Fine-Gray 的时间聚合结论是否稳健，也可以展示风险随时间变化。它是结构验证和时间分辨率补充，不是第二个可自由调参的主模型。

### 4.3 Cause-specific Cox：可做，但定位必须清楚

可将目标事件和 alive discharge 分别作为 cause-specific hazard，作为机制/组件分析或敏感性分析。它回答的是“在仍处于风险集中的患者中，当前原因特异事件速率如何变化”，与 Fine-Gray 的 CIF 不是同一个估计对象。两者结果不应只按 HR 大小横向排名。

### 4.4 Logistic 回归：不是主分析的替代品

普通多因素 Logistic 只有在明确把问题改写成“48 h 内是否发生事件”的固定二分类目标时才适用。若忽略 alive ICU discharge，它会把不同观察机会的患者混在一起，不能替代竞争风险分析。

可以预先保留一个固定 48 h 的 Logistic/penalized Logistic 作为可读性或外部工具兼容性敏感性分析，但必须明确 discharge 的处理方法（排除、竞争事件编码或 IPCW），并单独报告其 estimand；不能把普通 Logistic AUC 与 Fine-Gray CIF AUC 当作同一指标。

### 4.5 LASSO、elastic net、ridge：用于收缩和高维敏感性

- 变量高度相关（同一生命体征、实验室和支持治疗摘要）时，优先考虑 elastic net；它比纯 LASSO 更不容易在相关变量中任意选中一个。
- 若候选变量已由临床和时间合同压缩到 30-45 个，主模型不需要再用单因素筛选。可将 ridge/elastic net 作为预设收缩或敏感性分析。
- 本研究预设的惩罚回归比较只选 elastic net，`alpha=0.5` 在看结局前冻结；ridge (`alpha=0`) 或 LASSO (`alpha=1`) 不是必做模型，只有在事件数不足需要更强收缩，或导师/审稿问题明确要求时才作为单独敏感性分析，不同时扩展成模型竞赛。
- `lambda` 用训练折内部的 10 折交叉验证确定；外层 5 折或重复 5 折只用于无偏估计性能。`lambda.min` 和更保守的 `lambda.1se` 可作为预先定义的两个选择规则，但不能根据最终测试折表现挑一个。
- 插补、缺失指标、中心化、标准化、变量选择和 lambda 选择均必须在外层训练折内完成。任何全数据预处理后再交叉验证都属于泄露。

Fine-Gray 的实现若不支持直接惩罚，应把 penalized cause-specific model 或离散时间模型标注为不同的补充估计框架，不把它伪装成与主 Fine-Gray 完全等价的“Fine-Gray LASSO”。

### 4.6 随机森林、gradient boosting 和 XGBoost：只作为有条件的基准模型

标准随机森林不能自然处理本研究的三态竞争风险结构。若要加入机器学习比较，应使用可处理生存/竞争风险的实现，或明确定义固定 horizon target 并通过 IPCW 处理竞争事件。模型必须使用与主模型相同的 outer folds、相同的 T0-T12 信息边界和嵌套调参。

这类模型可以回答“非线性/交互是否带来有意义的增量预测”，但不是当前主模型的必需组成部分。只有在：

- 最终 DHF 事件数和每折事件数足以稳定训练；
- 超参数、特征集和评价指标在锁模前写定；
- 与 Fine-Gray 的比较使用同一 OOF 预测和置信区间；
- 校准不明显变差且临床净获益有预设改善；

时才值得加入论文正文。否则放入补充材料或不做，结论仍然完整。

## 5. 内部验证和性能评价

推荐的最终闭环如下：

```text
锁定 DHF 表型和候选变量
  -> 外层 5 折（按 event/competing/censor + sepsis 分层）
      -> 每个训练折内：插补/标准化/变量选择/10 折 CV 选 lambda/拟合
      -> 外层验证折：只生成 OOF 风险
  -> 汇总 48 h CIF AUC、Brier、校准截距/斜率、校准图、DCA、风险富集
  -> bootstrap 或重复外层折估计不确定性和选择稳定性
  -> 用全数据按已锁定规则拟合最终模型，仅用于模型系数和部署文件
```

外层 5 折是内部验证；内层 10 折是超参数选择。它们不是“十折 + K 折越多越好”，而是各自承担不同任务。若最终事件数允许，再增加重复 5 折或 500 次 bootstrap；若不允许，优先保证一次严格的嵌套验证和校准报告。

必须报告：事件/竞争事件/删失数、每折分布、有效参数数、收缩规则、缺失处理、OOF AUC（或 competing-risk AUC）、Brier、校准、95% CI 和模型收敛/方向稳定性。AUROC 单独不能证明临床可用性。

## 6. 缺失、非线性和解释

- 主分析：以训练折拟合的预设插补和缺失处理为准；最终代码必须保存每折转换参数。
- 若关键变量缺失率高，先在数据审计阶段决定删除、合并为可解释域特征或保留缺失指示；不能在看到性能后随意选择。
- 连续变量优先保留连续形式；若有足够信息支持非线性，可预先指定限制性立方样条，样条自由度计入有效参数。不要用大量任意分组制造非线性。
- Fine-Gray/Logistic 等线性预测器以系数、标准化效应、局部效应和校准展示为主，不强行套 SHAP。
- 若最终加入树模型，SHAP 只在每个外层验证折的 OOF 预测上计算，再汇总全体患者的全局重要性和个体解释；SHAP 不是因果解释，也不能用训练集 SHAP 排名后再回头删变量。

## 7. 预先定义的分析层级

| 层级 | 内容 | 是否进入主文 |
|---|---|---|
| 主分析 | DHF 主队列 + 紧凑 Fine-Gray + 严格 OOF 内部验证 | 是 |
| 结构补充 | 1 h person-period；必要时 cause-specific Cox | 是/补充材料 |
| 表型敏感性 | candidate、radiology-supported、multidomain；BNP-only、最近 24 h、PE/替代诊断分层 | 是/补充材料 |
| 缺失/删失敏感性 | MICE 或缺失指示、IPCW、complete60 | 补充材料 |
| 方法学基准 | 预设 elastic net；有条件时竞争风险树模型 | 补充材料优先 |
| 不做 | 单因素 P 值筛选、反复挑 lambda、普通 RF 直接忽略竞争风险、训练集 SHAP 选变量 | 不允许 |

## 8. 650 例到底是什么

历史严格 AHF candidate 队列为 `650` stays、`66` events。它曾用于检查严格口径下模型是否具有基本可行性，但 45 个候选变量只有约 `1.47` 个事件/变量，不能支持把全套变量直接用于最终预测模型。

它不是“先用 650 例测试、再用 5,555 例正式建模”的必经实验设计。最终应在 DHF 表型确定后，以最终主队列重新计算事件数和模型复杂度；如果 multidomain 队列接近或小于 650，必须进一步降维、增强收缩，或将结果标注为探索性/可行性分析。

## 9. 文献与规范依据

1. Fine JP, Gray RJ. A proportional hazards model for the subdistribution of a competing risk. *J Am Stat Assoc*. 1999;94:496-509. 竞争风险 subdistribution hazard 的原始方法。
2. Collins GS, Reitsma JB, Altman DG, Moons KGM. Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis (TRIPOD): The TRIPOD Statement. *Ann Intern Med*. 2015;162:55-63. doi:10.7326/M14-0697. 预测模型透明报告规范。
3. Wolff RF, Moons KGM, Riley RD, et al. PROBAST: a tool to assess the risk of bias and applicability of prediction model studies. *Ann Intern Med*. 2019;170:51-58. doi:10.7326/M18-1376. 预测模型偏倚与适用性审查。
4. Riley RD, Snell KIE, Ensor J, et al. Minimum sample size for developing a multivariable prediction model: PART II - binary and time-to-event outcomes. *Stat Med*. 2019;38:1276-1296. doi:10.1002/sim.7992. 样本量、过拟合和性能精度框架。
5. van Smeden M, Moons KGM, de Groot JAH, et al. Sample size for binary logistic prediction models: Beyond events per variable criteria. *Stat Methods Med Res*. 2019;28:2455-2474. doi:10.1177/0962280218784726. 说明 EPV 不是充分的现代样本量标准。
6. Steyerberg EW. *Clinical Prediction Models*. 2nd ed. Springer; 2019. 预测模型开发、验证、校准和收缩的系统框架。
7. Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. *Med Decis Making*. 2006;26:565-574. doi:10.1177/0272989X06295361. 临床净获益评价。
8. Lundberg SM, Lee SI. A unified approach to interpreting model predictions. *Adv Neural Inf Process Syst*. 2017;30. SHAP 方法原始论文；仅支持模型贡献解释，不支持因果推断。
9. Collins GS, Dhiman P, Andrayas A, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*. 2024;385:e078378. doi:10.1136/bmj-2023-078378. 回归与机器学习预测模型的更新报告规范。

## 10. 当前执行顺序

1. 完成 300/60 DHF 影像报告标注及裁决。
2. 冻结 candidate、radiology-supported、multidomain 的主队列口径，重算事件数和有效参数上限。
3. 按最终事件数更新白名单/黑名单和 compact manifest；不再使用旧 650/66 作为最终样本量依据。
4. 先完成主 Fine-Gray 的严格嵌套/重复内部验证；再运行 person-period、表型/删失/缺失敏感性。
5. 只有在锁模前预设条件满足时，才添加 elastic net 或竞争风险机器学习基准；ridge/LASSO 不作为常规必做项目。
6. 依据 TRIPOD+AI 报告，依据 PROBAST+AI 做开发阶段偏倚审计，并准备院内外部验证字段。

本文件是统计分析计划，不替代临床标注指南或最终导师决策；它的作用是让每个决策在看见最终性能前已有可复核理由。
