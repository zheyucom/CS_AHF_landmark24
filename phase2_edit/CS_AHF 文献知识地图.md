# CS_AHF 文献知识地图

> 原生可视化：[[CS_AHF 文献知识图谱.canvas|CS_AHF 文献知识图谱]]；高亮与插件分工见 [[Zotero 高亮与插件协作规范]]。

## 课题锚点

**研究问题**：在成人 index ICU 的 operational DHF 表型患者中，T12 时仍存活且留在 index ICU 者，能否仅用 `[T0,T12)` 可得信息，预测 T12 后至 `min(T60, alive index-ICU discharge)` 的治疗升级型 ICU 血流动力学恶化，并在本院完成锁模外部验证？early sepsis 是预设亚组，不是主队列的强制纳入条件。

**当前研究合同（2026-09-16 Dashboard）**：MIMIC 用于开发/内部验证，本院用于锁模外部验证；Fine-Gray 为主模型，alive index-ICU discharge 为竞争事件，1 h person-period 为补充。双库最终 DHF 表型、同口径三态结局、候选参数和正式模型均未冻结。旧 `2,424/334`、elastic-net 主模型及旧宽口径性能只保留为历史可行性探索，不是当前研究事实。

## 核心 21 篇证据矩阵

| ID | 核心角色 | 人群/数据 | 时间设计 | 主要模型/方法 | 主要结局 | 对本课题的直接作用 |
| --- | --- | --- | --- | --- | --- | --- |
| R003 | endpoint definition | ADHERE-Medicare, n=63,727 | >12 h WHF | 回归关联 | WHF/死亡/费用 | 支持 12 h landmark 与治疗升级结局 |
| R004 | static benchmark | ADHERE n=23,696 + ASCEND-HF | >12 h WHF | logistic/LASSO | WHF | 内部 0.72-0.74，外部 0.63，提示运输性 |
| R019 | clinical spectrum | AHF 单中心 n=223 | 入院静态 | logistic/Firth | WHF + new CS | 连接 WHF 到 CS，提示肾/右心特征 |
| R020 | dynamic benchmark | MIMIC-III + NYU | 逐小时 | causal dilated CNN | new CS | 动态外部验证可行，ADHF 亚组较弱 |
| R021 | rare-event actionability | 三院 ADHF n=24,461 | 排除 6 h 早发 shock | logistic 为主 | new CS | AUC 尚可但 PPV 低，要求报警负担审计 |
| R022 | short-horizon benchmark | 30 医院 EHR | 干预前 2 h | XGBoost | CS | 干预锚点可复用，但 mixed shock 被排除 |
| R037 | population overlap | eICU + MIMIC, n=6,819 | 早期静态 | logistic 等 | 28 d death | 交叉人群可建模，外部 AUROC 降至 0.699 |
| R038 | mixed physiology | Mayo CICU sepsis n=605 | 首 24 h | SCAI/SOFA | mortality | 说明 mixed shock 分型需要独立审查 |
| R040 | treatment context | HF+sepsis n=671 | 初始 6 h | logistic | fluid/mortality | 液体量是严重度与治疗选择混合代理 |
| R049 | nonlinear treatment context | septic ADHF n=598 | 初始 3 h | GAM/logistic | fluid/mortality | 液体-风险可能非线性，但不能作因果剂量建议 |
| R055 | transport benchmark | MIMIC-IV + eICU, n=96,956 admissions | 首 24 h→后续 stay | random forest | strict HD composite | 双向外部验证先例；时间合同不如本课题固定 |
| R056 | continuous warning | HiRID + MIMIC-III | 每 5 min→8 h | LightGBM | circulatory failure | 区分时间点性能、事件级报警和迁移/微调性能 |
| R071 | design reference | 450 万 + 17,787 人 EHR 示例 | repeated landmark | landmark Cox | fracture/mortality | 支撑在险集重建、聚类方差和防止时点泄漏 |
| R083 | reporting standard | 国际 Delphi | 不适用 | consensus | reporting | 按 TRIPOD+AI 完整报告开发与评价 |
| R084 | bias standard | 国际 Delphi | 不适用 | consensus | RoB/applicability | 按 PROBAST+AI 预审和终审偏倚 |
| R085 | infection mortality benchmark | MIMIC-IV + eICU CHF+肺部感染 | 首24 h→15 d | XGBoost | mortality | 外部 AUC 0.718/recall 0.383，提示 case-mix 与阈值漂移 |
| R086 | ultra-early static benchmark | MIMIC-IV ICU HF n=12,110 | 0-6 h→院内 | XGBoost | mortality | 患者级拆分与完整校准可借鉴；alive discharge 不应普通删失 |
| R087 | text phenotyping reference | HF EHR NLP 叙述综述 | 任务依赖 | rule/ML NLP | phenotype/outcome | 支持多域文本证据，不支持 AI 草案替代临床金标准 |
| R088 | dynamic HF+sepsis benchmark | MIMIC/eICU sepsis | 滚动6-16 h | XGBoost+LSTM | ICD-AHF | AUPRC/utility 值得对照；动态部分仅内部验证且 onset 不透明 |
| R089 | biomarker interpretation | sepsis/septic shock n=23 | fluid challenge前后 | association | BNP/NEP/fluid response | BNP 高值可受清除下降影响，不能单项确诊 DHF 或容量无反应 |
| R090 | leakage warning | MIMIC-IV AHF n=4,467 | 首24 h/AKI前治疗→ICU AKI | LASSO+logistic | AKI | 变量时点未统一冻结；交互网页不等于动态预测 |

## 跨文献综合

### 1. 结局构念：从 WHF 到 mixed HD

R003/R004 将“入院后治疗升级”固定在早期复杂表现之后，R019/R021 再把终点推进到新发 CS。对当前课题最稳妥的做法不是复制任一单篇定义，而是用 **landmark 后治疗升级 + 持续低血压/低灌注证据** 形成 HD，并把 overt CS、septic-predominant 和 mixed physiology 留作次级分型。证据链见 [[R003 - DeVore 2014 - In-hospital worsening heart failure]]、[[R019 - Beer 2024 - Cardiac worsening to cardiogenic shock]] 和 [[R038 - Jentzer 2022 - Shock severity in CICU sepsis]]。

### 2. 时间合同：动态不等于无边界

R020/R056 证明高频更新风险可行，R071 提供重复 landmark 的方法学理由；R071 两个 Cox 示例的 c-statistic 仅由 0.797/0.68 提升至 0.813/0.70，进一步说明 landmark 的主要价值是时间合同、在险集和数据组织，而非保证性能提升。主课题当前应优先使用一个可审计的固定合同：`0-12 h predictors -> 12-60 h outcome`。只有当固定模型稳定后，才扩展到多个 landmark，并在每个时点重建在险集、排除既往事件且处理患者内相关性。

### 3. 模型选择：复杂算法没有自动优势

R004 与 R021 显示低自由度回归在小事件数场景仍可有竞争力；R020/R055/R056/R088 显示树模型或时序网络在大样本、高频数据中可以提高区分度。R086 的首 6 h XGBoost AUC 0.797、R085 的 XGBoost 从内部 0.968 降到外部 0.718，再次说明复杂模型不能替代正确表型、校准和运输性验证。当前事件数尚未冻结，候选参数和模型复杂度必须在冻结后限定；主 estimand 已确定使用 Fine-Gray，而不是继续沿用历史 elastic-net 合同。

### 4. 外部验证：区分度相近不等于可迁移

R004 和 R037 在外部数据中明显降级，R055 则报告双向跨库相对稳定。R056 的 compact model 从 HiRID 直接迁移至 MIMIC-III 时 AUROC/事件级 AUPRC 由 0.939/0.60 降至 0.902/0.45，fine-tune 后回升至 0.920/0.55；fine-tune 结果不能替代锁模外部验证。各研究并非直接矛盾，因为任务、事件率、变量映射和验证口径不同。当前课题必须在本院保持模型与阈值冻结，并同时报告 calibration-in-the-large、slope、Brier、DCA 和区分度。

### 5. 治疗变量：既是信息，也可能污染标签

R040 与 R049 对液体量的观察性结果表面不同：前者未见 >=30 mL/kg 明显增加机械通气，后者见 U 型死亡关联。差异可由入组人群、3 h/6 h 暴露窗和 confounding by indication 解释；两篇都不足以给出因果治疗建议。R090 进一步展示了把“AKI 前任意治疗”放入预测变量的时间泄漏风险。对建模而言，液体、升压药、机械通气和测量频率只能在 `[T0,T12)` 内作为基线严重度/治疗代理；T12 后治疗升级属于结局过程，不得回流。

### 6. 文本与多域表型：NLP 是证据抽取器，不是金标准

R087 显示 ICD 对 HF 往往特异性高于敏感性，文本可改善队列构建和结局判定；但模型结果受语言、模板、语境、公平性和标签质量限制。当前 MIMIC 主窗口 7,828/7,828 份放射科报告已经完成文件级 QC，300 条 round 1 和 60 条独立 round 2 仍待人工确认。Codex/规则输出必须保留 provenance，并与临床裁决分层报告，不能把 AI 草案当最终 DHF 标签。

### 7. 利钠肽：支持证据而非单项确诊阈值

R089 在 23 名 severe sepsis/septic shock 患者中提示 BNP 升高可部分来自 NEP 24.11 活性下降，且 BNP >1000 pg/mL 仍不能排除液体反应。该小样本只支持机制边界，不能给出项目阈值；但它直接强化当前决定：NT-proBNP >=300 不能称 DHF 确诊阈值，early-sepsis 和肾功能背景下必须结合结构/功能异常、充血、管理证据及替代解释。

## 关键 tension 清单

| 文献对 | 表面张力 | 当前解释 | 状态 |
| --- | --- | --- | --- |
| R040 vs R049 | 30 mL/kg 未显示伤害 vs 10-15 mL/kg 风险最低 | 人群、时间窗和治疗选择混杂不同；不能作因果比较 | 未解决，需 RCT/因果设计 |
| R004 vs R055 | 外部性能明显下降 vs 双向外部稳定 | 结局、事件率、变量映射和评价流程不同 | 条件差异，不是直接矛盾 |
| R021 vs R020/R056 | PPV 约 0.05 vs 较高 AUPRC/事件召回 | 患病率、时间点/事件单位、阈值和结局定义不同 | 条件差异，需预先固定报警评价合同 |
| R003/R004 vs R038 | 治疗升级 WHF vs 严重度分层 mixed shock | 前者定义未来过程，后者描述当前状态 | 互补，不可混作同一标签 |
| R085 内部 vs 外部 | AUC 0.968 vs 0.718、recall 0.383 | case mix、肺炎构成、测量和阈值漂移 | 真实运输性警示，外部需锁模校准 |
| R086 KM vs 当前 estimand | alive discharge 作删失 vs 竞争事件 | 院内结局下出院阻止 ICU 事件发生 | 当前坚持 Fine-Gray，不复制普通删失 |
| R088/R090 标题 vs 实际设计 | “continuous/dynamic” vs 内部滑窗或交互网页 | 标题不能替代时间合同审查 | R088仅作动态 benchmark；R090作泄漏反例 |
| R089 vs 单阈值表型 | 高 BNP 被视为心衰/容量超负荷 vs sepsis 清除和炎症影响 | biomarker 非特异，需多域证据 | 与当前 operational phenotype 一致 |

## 当前可主张的研究 gap

1. 缺少针对 **operational DHF** 主队列、在 T12 重建在险集并把 early sepsis 作为预设亚组的 ICU HD 预测。
2. 现有研究常以死亡、ICD-AHF、CS 或整个 ICU stay 结局替代可干预的 T12 后治疗升级型恶化，时间边界不一致。
3. 治疗升级标签存在 indication bias，mixed shock 的病理生理分型不足。
4. 多数模型缺少与开发环境显著不同的中国医院外部验证和完整校准/净获益评估。
5. 高性能动态模型仍缺少前瞻实施研究证明报警能改善结局。

## 由文献推导的研究决策

- 在双库表型、T12 风险集和三态结局冻结前，不生成或引用最终样本、事件数和性能。
- 主 estimand 使用 Fine-Gray，alive index-ICU discharge 为竞争事件；1 h person-period 仅为补充。
- 所有缺失填补、标准化、特征选择和调参置于训练折内；动态分析以患者为拆分单位，每个时点重建在险集，病例与非病例使用对称锚点。
- 文本/AI 结果作为有 provenance 的证据层，300 条 round 1 与 60 条独立 round 2 完成人工确认后才可评估标签性能。
- 实验室变量必须使用预登记 `itemid × fluid × category × unit` allowlist，按结果可用时间门控，并审计比较符号与 raw/derived 双向覆盖；BUN 和乳酸列为首批回归案例。
- 本院锁模外部验证先使用原模型和原阈值；校准更新或阈值更新必须另列探索结果，不能回写为原始外部性能。
- 预设 TP/FP/FN/TN 轨迹审查，特别核对治疗行为标签、mixed physiology 和 early-sepsis 亚组。
- 开发前按 [[R084 - Moons 2025 - PROBAST+AI]] 预审，写作时按 [[R083 - Collins 2024 - TRIPOD+AI]] 逐项输出。

## 证据边界

- 核心 21 篇均已进入 Zotero 并有本地 PDF；本次新增/刷新的 7 篇已完成全文核对。
- R056 的 28 页 PDF 与 R071 的 7 页 PDF 已完成文本抽取和逐页视觉完整性检查；两条目没有既有 Zotero 笔记或高亮批注。
- 该 21 篇是滚动核心证据集，不是系统综述的完整纳入集，不能据此声称覆盖全部证据；近期系统检索将在下一阶段另行完成。
