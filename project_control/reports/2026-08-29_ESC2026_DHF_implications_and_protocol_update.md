# ESC 2026 DHF 术语更新对本课题的影响与方案修订

日期：2026-08-29  
状态：设计修订建议。DHF 最终表型须在 Note radiology 验证和导师确认后冻结。

## 1. 已核对的指南事实

2026 ESC 心衰指南已于 2026-08-28 发布：Kober L, Adamo M, et al. *2026 ESC Guidelines for the management of heart failure*. *Eur Heart J*. 2026. doi:10.1093/eurheartj/ehag100; PMID:42661420。

ESC 官方新闻稿明确说明：**decompensated HF (DHF) replaces acute HF**，原因是部分患者并非突然恶化，而是渐进性失代偿；部分较不急的 DHF 可在门诊处理。新闻稿同时指向 2026 Second Universal Definition of Heart Failure：Walsh MN, et al. *Eur Heart J*. 2026;47:4357-4374. doi:10.1093/eurheartj/ehag500。

用户提供的 DHF 文字定义为：急性或渐进起病的 HF 症状和/或体征，严重到需要紧急医疗关注并启动或强化治疗。该定义应作为本研究临床概念框架。自动化核验已确认指南 DOI、发布日期、PubMed 记录与 ESC 官方新闻稿；OUP 全文页面受到 Cloudflare 限制，因此正式写作前仍应由研究者从指南 PDF/口袋版逐字核对定义所在表格/页码，而不虚构页码或直接引号。

官方来源：

- [ESC 新闻稿](https://www.escardio.org/news/news-room/congress-news/2026-esc-guidelines-for-the-management-of-heart-failure/)
- [指南 DOI](https://doi.org/10.1093/eurheartj/ehag100)
- [PubMed PMID 42661420](https://pubmed.ncbi.nlm.nih.gov/42661420/)
- [Second Universal Definition DOI](https://doi.org/10.1093/eurheartj/ehag500)

## 2. 对课题的核心判断

### 2.1 研究不需要推倒重来，但必须改名和分层

原研究的时间结构仍合理：T0=ICU 入科，0-12 h 预测窗口，T12 后预测未来 48 h，alive ICU discharge 为竞争事件，Fine-Gray 为主模型。这与“及早识别可能继续失代偿的患者”的临床目标一致。

应停止把目标人群笼统称为 “acute HF”。推荐的论文对象名称为：

> **ICU patients with a pre-T0 decompensated heart failure (DHF) operational phenotype**

这里的 “operational phenotype” 必须保留，直到有症状/体征、影像、医生评估和治疗时间的多域验证。现有 `650/66` 只能称为 **DHF candidate phenotype**，不能直接称为已按 2026 指南临床确诊的 DHF。

### 2.2 DHF 入组与血流动力学恶化结局不是同一件事

| 层次 | 本研究中的含义 | 时间边界 | 是否可使用治疗信息 |
|---|---|---|---|
| 入组：DHF 表型 | 已有心衰，出现失代偿临床综合征并需要紧急评估/治疗 | 严格 `<T0` | 仅可使用 `T0` 前启动/强化的治疗，作为 DHF 证据域之一 |
| 预测器 | 临床团队在 T12 前可见的风险信息 | `[T0,T12)` | 可使用基线支持状态，但不能使用结局定义的 post-T12 升级 |
| 结局：ICU hemodynamic deterioration | 随后出现循环支持升级、持续 NEE 上升或 ICU 内死亡 | `[T12,T60)` 或更早 alive ICU discharge | 仅使用 T12 后、且相对 T12 前基线的升级 |

因此，只要严格遵守时间切分，**T0 前的利尿治疗用于证明“已在失代偿状态”，T12 后的血管活性/强心支持升级用于定义“后续循环恶化”并不构成直接信息泄露**。但两者都属于临床治疗行为，仍可能受医生偏好、科室流程及 sepsis/mixed shock 影响，必须在局限性中说明。

### 2.3 你的结局可以理解为“通向休克的恶化阶段”，但不能直接命名为心源性休克

临床上，未发生显性休克的 DHF 患者可能沿着充血、低灌注、升压/强心治疗升级到心源性或混合性休克的路径发展。研究排除了 T12 前的 overt shock proxy，预测的是其中后续发生的循环恶化，因此可以在研究动机中写为：

> identify patients with DHF who are at risk of progression towards shock or mixed circulatory failure.

但当前主结局仍不能写成 “incident cardiogenic shock” 或 “pre-cardiogenic-shock model”，因为升压药/NEE 升高和 ICU 死亡还可能由脓毒性、出血、呼吸衰竭或 mixed physiology 驱动。准确的终点名称应保持：

> **treatment-escalation-based ICU hemodynamic deterioration**

并预设一个更严格的次要终点：`incident overt shock/CS-like proxy`，只用于机制一致性分析。SCAI SHOCK 分期可帮助解释休克严重度，但 MIMIC 只能构造代理指标，不能声称临床 SCAI 分期。参考：Naidu SS, et al. *J Am Coll Cardiol*. 2022;79:933-946. doi:10.1016/j.jacc.2022.01.018。

## 3. DHF 表型应如何重建

### 3.1 不再把 “acute HF ICD” 当作唯一中心条件

DHF 可发生在既往 HF 恶化，也可作为 de novo HF 首发表现。因此最终诊断编码应退回为**回顾性 HF 锚点**，而不是要求必须出现 acute/acute-on-chronic code。当前 5,555 例风险集中都有 HF ICD 锚点，其中 4,485 例为 acute/acute-on-chronic 编码。更新后应审计：采用任何 HF ICD 锚点是否能覆盖更多符合 DHF 多域证据的患者。

### 3.2 推荐的三层证据结构

| 证据层 | 推荐字段及时间 | 作用 | 当前可得性 |
|---|---|---|---|
| 回顾性 HF anchor | 本次住院最终 HF ICD，诊断序位，用于审计 | 确认 HF 背景；绝不进入预测器 | 已有 |
| 临床/客观 decompensation | pre-T0 放射科报告中的肺水肿/血管充血；有时间的医生诊断、症状/体征；心超结构/功能异常 | 证明充血或心衰临床综合征 | radiology 可经 Note 获得；其他字段在 MIMIC-IV 中不完整 |
| 紧急治疗/管理证据 | pre-T0 实际 IV 袢利尿剂、血管扩张剂/无创通气或明确的 HF 治疗强化 | 证明需要启动/强化治疗 | loop eMAR 已有；其他治疗需字段审计 |
| 生物标志物 | pre-T0 NT-proBNP，保留 assay/单位/时间 | 支持，不独立确诊 | 已有 |

主表型的推荐门槛是：`HF retrospective anchor + 至少一项 pre-T0 临床/客观 decompensation 证据 + 至少一项 pre-T0 紧急治疗/管理证据`。如果缺少临床/客观域，只能归为 `DHF candidate`，不能成为最终主表型。

NT-proBNP 不可单独充当任一必需域。`NT-proBNP >=300` 是排除/支持逻辑中的低阈值，不是 DHF rule-in；肾功能、年龄、房颤、肺栓塞、肺高压和脓毒症等可影响数值。

### 3.3 MIMIC-IV 的现实边界

MIMIC-IV-Note v2.2 的可用核心是 `radiology` 与 `discharge`。其中：

- pre-T0 `radiology.charttime` 可用于回顾性抽取肺水肿、血管充血和胸腔积液；需要否定词/不确定词处理和人工盲法抽样复核；
- discharge summary 常含最终诊断，但其记录时间可能在 ICU 后，不能作为 T0 前医生诊断时间，不能进入预测器；
- MIMIC-IV-Note 不能可靠补齐连续的急诊/住院 physician notes、症状、体征、肺超声或首次医生诊断时间；
- 当前本机没有可用心超报告表。不能假定能从 MIMIC-IV-Note 补出 LVEF 或床旁超声。

所以最科学的做法不是假装完整复刻指南金标准，而是进行**可追溯的多域操作性表型验证**，并公开报告缺失域和抽样验证性能。

## 4. 对当前 650/66 和模型的直接处理

1. 不删除现有 650/66 审计或 105A 低维输入，它们保留为 `legacy AHF/DHF-candidate` 版本。
2. 不立刻运行其最终 Fine-Gray 模型，因为其 504 例为 NT-proBNP-only，尚不能满足新的多域 DHF 主表型。
3. 先在 5,555 个 HF ICD 锚点中完成 pre-T0 radiology 覆盖率和人工抽样验证；这一步可能让候选人数扩大或缩小，不能预先假定结果。
4. 根据验证后的人数和事件数决定：
   - 若多域 DHF 事件数足够，作为主队列，重新冻结低维模型；
   - 若事件数不足，使用较宽 `DHF candidate` 作为主开发队列，并把多域 DHF 作为高特异性敏感性/表型验证，明确研究是操作性而非临床金标准；
   - 双证据/高特异性样本若事件极少，只做描述和方向性验证，不建高维模型。
5. 原 5,555/454 模型绝不改写为 DHF 最终性能；它仅是 broad HF-anchored 历史/比较结果。

## 5. 文献依据与可用于答辩的表述

| 依据 | 对课题的直接作用 |
|---|---|
| Kober et al., 2026 ESC HF guideline, doi:10.1093/eurheartj/ehag100 | 用 DHF 更新人群的临床概念和论文术语 |
| Walsh et al., 2026 Second Universal Definition, doi:10.1093/eurheartj/ehag500 | 支持从单一 LVEF/单一检测向临床综合征、病因和轨迹的统一定义转变 |
| McDonagh et al., 2021 ESC HF guideline, doi:10.1093/eurheartj/ehab368 | 历史上已强调临床表现、影像和生物标志物的整合；用于解释过渡期方法 |
| DeVore et al., 2016 ADHERE WHF model, doi:10.1016/j.ahj.2016.04.021 | 支持治疗强化型 WHF 的院内预后意义，但不等同于你的 mixed-physiology HD 终点 |
| Beer et al., 2024, doi:10.1002/ehf2.14792 | 支持 WHF 至 CS 的连续临床谱系，适合论证研究动机 |
| Naidu et al., 2022 SCAI update, doi:10.1016/j.jacc.2022.01.018 | 支持将休克视为有层级的临床状态，但不能把 MIMIC 代理指标当作临床分期 |

答辩时可用：

> 新指南促使我们把研究对象从“急性心衰编码患者”升级为“DHF 操作性表型患者”。DHF 的判定与后续循环恶化必须分开：入组只使用 ICU 前的多域证据和治疗启动/强化；模型在 T12 后预测相对基线的新循环支持升级。这样研究关注的是失代偿后可能走向休克或混合循环衰竭的过程，而不把治疗升级同时当成同一时点的入组条件与结局。

## 6. 下一步执行顺序

1. 使用新的 106 导出和 BigQuery 查询，扫描全部 5,555 个 HF ICD 锚点的 pre-T0 radiology 文本。
2. 记录每个 stay 的报告覆盖率、时间窗合规率、阳性/否定/不确定报告数；从阳性和阴性各随机抽样进行盲法人工核对。
3. 先根据 radiology 验证结果定义 `DHF_candidate` 与 `multidomain_DHF`，再审计样本量、事件数和组间差异。
4. 导师确认是以多域 DHF 还是宽 DHF candidate 为主；随后重新冻结低维模型，而不是继续使用 105A 作为最终版本。
5. 完成 component-specific outcome、strict shock/CS-like 次要结局和非支持类变量敏感性，以避免将治疗行为误解为纯病理生理进展。
