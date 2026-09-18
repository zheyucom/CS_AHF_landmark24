# DHF 入组表型：文本抽取、人工验证与时间序列协议

日期：2026-09-03  
状态：执行协议 v1.4。300 条报告已完成第一位标注；60 条为同标注者重复；患者级多域审计第一版已完成。用户已确认院内严格主队列为 `echo-supported DHF ICU cohort`。

## 1. 直接结论

后续入组工作确实需要依赖影像报告、心超结果和可获得的临床记录来提高 DHF 表型可信度，但**当前主要工作不是训练一个大规模 NLP 模型**。

在 MIMIC-IV-Note 中，可靠可用的实时前 ICU 文本主要是 radiology report；它不能完整提供连续 physician note、症状、体征、肺超声或首次医生诊断时间。因此当前正确的重心是：

1. 精确的时间序列和可用性判定；
2. 可审计的规则型文本筛查；
3. 心超检查/结果的独立结构化审计；
4. 临床人工抽样验证；
5. patient-level 多域 DHF 表型构建；
6. 验证通过后才重建最终模型。

只有当规则筛查在人工验证中表现不足，才进入更复杂的 NLP，例如 section-aware contextual model 或医学语言模型微调。没有经过人工金标准标注，直接训练复杂模型不会比规则更科学，反而会使错误难以追踪。

## 2. `dhf_radiology_candidates.csv` 是什么

`project_control/bigquery/dhf_radiology_candidates.csv` 是**候选患者宇宙和时间锚点**，不是最终入组名单。

它包含全部 5,555 个 v3.3 landmark-eligible HF ICD anchors，以及每人对应的 `admittime`、`intime`、既有 acute-HF coding 和 pre-T0 loop/NT-proBNP 审计标记。它的用途是让 BigQuery 只读取这些人、严格截取同一次住院且 `admittime <= charttime < intime` 的 radiology report。

最终主队列只能在临床验证后从这个候选宇宙中产生；不应从 CSV 的任一字段直接推断 DHF。

当前操作性结论分为两层：院内外部验证主队列是截至 T12 已具有可追溯 DHF 操作性表型、且每例满足心超三级 QC 的成人 ICU 患者；全 ICU 候选宇宙作为选择性审计层保留。心超未做、结果缺失或只有操作记录时保留为 `unknown/not assessable`，不能进入严格队列，也不能判为阴性。这里不声称所有 ICU 患者必然完成心超，而是把“实际检查且结果支持异常”作为已冻结的院内严格研究对象定义。

## 3. 端到端数据流程

```text
C0  5,555 HF ICD anchors + local time boundaries
    -> BigQuery 106 raw radiology reports
R0  report-level text + charttime + storetime + screening flags
    -> clinical annotation / rule validation
R1  report-level congestion label: definite / possible / absent / indeterminate
    -> BigQuery 107 patient-level summary
P1  report coverage, availability, congestion-screen and adjudicated evidence
    -> local cohort audit
C1  DHF candidate / multidomain DHF / high-specificity DHF tiers
    -> event-count and EPV audit
M1  final low-dimensional Fine-Gray model and sensitivities
```

原始文本 `R0` 只用于表型验证，不进入 T0-T12 预测器，也不在结果文件中随意复制传播。

## 4. 时间序列规则

主研究是 `T12` landmark cohort。DHF 证据允许出现在 `[T0-24 h, T12)`，不要求患者在 `T0` 已经完成 DHF 诊断；所有用于资格判定的证据都必须在 `T12` 前有可追溯时间。院内严格主表型需同时具备 HF anchor、心超三级 QC、至少一个肺充血或临床失代偿域和至少一个治疗/管理强化域；只有 BNP、loop、最终 ICD 或心超操作记录支持时仍称 candidate/unknown。严格 `pre-T0` 证据仅作为敏感性分析。T12 后信息既不能回填入组，也不能进入预测器。

| 概念 | 字段 | 主分析用途 |
|---|---|---|
| 检查发生时间 | `radiology.charttime` | 主窗口保留 `intime-24 h <= charttime < intime+12 h`；pre-T0 敏感性另保留 `admittime <= charttime < intime` |
| 报告可见时间 | `radiology.storetime` | 单独审计 `storetime < T12`，用于更严格、可部署的可见性敏感性 |
| 入组治疗证据 | eMAR `charttime` | 只允许 `<T0` 的实际 IV 袢利尿剂给药 |
| 生物标志物 | `labevents.charttime` | 只允许 `<T0`；NT-proBNP 仅支持，不单独确诊 |
| 预测器 | ICU 结构化数据 | 只允许 `[T0,T12)` |
| 结局 | vasoactive/NEE/death 时间 | 只允许 `[T12,T60)`，且相对 pre-T12 基线升级 |

`charttime < T0` 证明检查发生在 ICU 前，不必然证明报告在 ICU 前已被临床团队看到。因此 106 v2 同时输出 `report_available_pre_t0_flag` 和 `storetime_missing_flag`。主表型和部署解释需报告两种时间口径的差异。

## 5. 心超与 CXR/CT 证据域

本轮审计的决策边界：心超是院内严格主队列必需的最高优先级客观心脏证据，但“有心超检查记录”不等于“心超异常”。严格队列必须同时满足：实际完成检查、结果在 T12 前可用、结果支持至少一项心脏结构或功能异常。心超未检查或结果不可用的 ICU 候选者不进入严格队列，但保留在选择性审计层。CXR 与胸部 CT 是互补的肺部充血证据，主规则使用 CXR OR CT；CXR AND CT 仅用于严格敏感性分析。要求两种检查同时存在会受 CT 临床选择性影响，造成不必要的选择偏倚和样本量损失。CT 阳性还应单独记录 PE、肺炎/ARDS 等替代或并存诊断，不把 CT 的缺失当作阴性。

心超是院内严格主队列的硬性证据域，但必须区分“做过检查”“结果可用”和“结果支持异常”。MIMIC 的现有审计只证明部分患者有心超操作记录，不能由此推断异常。至少输出：`echo_any_procedure_pre12_flag`、`echo_any_procedure_0_12h_flag`、`echo_result_available_pre12_flag`、`echo_result_available_0_12h_flag`、`echo_abnormal_support_pre12_flag`、`structured_lvef_pre12_available_flag`、首次/末次心超时间和结果可用性。

CXR 与胸部 CT 是互补的肺部充血证据，不要求两者同时存在。主分析使用 `CXR OR CT` 的时间合规证据；CT 检查未发生不能当作 CT 阴性。`CXR-only`、`CT-supported`、`CXR-or-CT`、`echo-confirmed` 和 `echo+lung-imaging` 分别作为预设表型层或敏感性分析。

心超异常、肺部影像充血、临床证据和实际治疗强化应分域保留。最终 `multidomain_DHF` 至少要求 HF retrospective anchor、一个客观/临床失代偿域和一个时间合规的管理/治疗域；NT-proBNP 只作支持证据，不能单独确诊 DHF。

## 6. 规则型 NLP v1

### 输入与输出

- 输入：每个 pre-T0 radiology report 的文本、`charttime`、`storetime`、ID/time anchor。
- 提取概念：pulmonary edema、interstitial/alveolar edema、vascular congestion、pleural effusion、cardiomegaly。
- 上下文：否定（例如 `no pulmonary edema`）和不确定（例如 `possible`、`cannot exclude`）。
- 输出：`positive_congestion_evidence_flag`、`uncertainty_hit`、报告可用性标记和规则版本；不输出临床“确诊 DHF”。

这是一个可解释的 weak-labeling 规则层。NegEx 的否定识别思路支持先处理否定语境；胸片文本的不确定性和专家比较是 CheXpert 等工作强调的核心问题。规则必须以本项目人工标签验证，而不能因借鉴文献就假定有效。

### 不能做的事情

- 不能用 discharge summary 为 T0 前医生诊断时间背书。
- 不能把 `pleural effusion` 或 `cardiomegaly` 单独等同于肺充血/DHF。
- 不能把 `possible congestion` 与 definite congestion 混为主表型。
- 不能把文本命中加入预测器，或让 T12 后报告回填入组。

## 7. 人工验证计划

### 报告级标注标签

每条报告由临床标注者在不知道结局和模型预测的情况下标为：

1. `definite_congestion`：明确肺水肿/肺血管充血；
2. `possible_congestion`：不确定或可能存在；
3. `no_congestion`：明确否定或无充血证据；
4. `indeterminate`：文字不足、术后/技术限制或无法判断。

同时单独标注是否有明显替代解释（PE、肺炎/ARDS、孤立胸腔积液等），但不把共病自动判为非 DHF。

### 抽样与质量门

| 抽样层 | 初始样本 | 目的 |
|---|---:|---|
| definite positive rule screen | 100 reports | 估计阳性预测值和常见误触发 |
| negated/uncertain screen | 100 reports | 核验否定/不确定处理 |
| no-hit reports | 100 reports | 发现漏检概念和估计假阴性风险 |

- 至少 20% 报告由第二位临床标注者独立复核；报告 raw agreement 和 Cohen's kappa；分歧由预先指定的临床专家裁决。
- 主规则的最低实践门槛建议为：definite positive 的 PPV 达到可接受水平且 95% CI 足够窄；具体阈值在看到标注前与导师确定，不能事后按结果移动门槛。
- 若 PPV 不足，先修正规则词典、否定/不确定窗口和报告段落处理，再在独立保留样本上复验；不要在同一 300 份报告上无限调参后报告性能。

## 8. Patient-level DHF 规则和决策门

### 表型层级

| 表型 | 最低证据 | 用途 |
|---|---|---|
| `DHF_candidate` | HF anchor + `[T0-24 h,T12)` 内 loop 或 NT-proBNP 等支持证据 | 宽队列/敏感性 |
| `radiology_supported_DHF` | HF anchor + 时间合规的 CXR 或 CT definite congestion 报告 | 客观表型验证层 |
| `echo_supported_DHF` | HF anchor + T12 前心超三级 QC 通过且支持结构/功能异常 + 肺充血/临床失代偿 + 治疗/管理强化 | 院内严格外部验证主队列 |
| `multidomain_DHF` | HF anchor + 一个客观/临床失代偿域 + 时间合规实际治疗/管理证据，可不含可用心超结果 | 宽口径桥接/敏感性层 |

### 当前第一版审计结果

患者级审计已输出 5,549 行且 stay_id 唯一，结局守恒为 452 event + 2,934 compete + 2,163 censor。严格 ICU 前可见的 definite CXR 为 425 例、definite chest CT 为 55 例、CXR OR CT 为 449 例、CXR AND CT 为 31 例；心超检查记录为 462 例，但结构化 LVEF 可用为 0。以上是规则支持和严格时间口径的审计，不是全量人工确诊，也不能替代主窗口 [T0-24 h,T12) 的最终表型冻结。

### 冻结顺序

1. 先运行 106 并保存原始结果为 `dhf_radiology_raw_v2`。
2. 再运行 107，得到每个候选患者的报告覆盖与筛查汇总。
3. 完成人工标注和规则锁定，建立 `DHF adjudicated evidence` 表。
4. 计算每层的 stay 数、事件数、竞争事件、缺失率和 EPV。
5. 先核查 MIMIC 与院内是否都有可时间审计的心超实际结果；严格队列达到可分析事件数后，在不查看外部验证结局的前提下冻结主表型。
6. 按最终严格队列事件数重新冻结预测器，之后才开始最终建模和外部锁模验证。

## 9. 文献依据

- Kober L, Adamo M, et al. 2026 ESC HF Guideline. doi:10.1093/eurheartj/ehag100：DHF 术语和临床综合征框架。
- Walsh MN, et al. Second Universal Definition of HF. 2026. doi:10.1093/eurheartj/ehag500：统一 HF 定义与轨迹框架。
- Metra M, et al. Worsening of Chronic HF: HFA clinical consensus. 2023. doi:10.1002/ejhf.2874：WHF 与治疗强化的概念边界。
- DeVore AD, et al. ADHERE in-hospital WHF model. 2016. doi:10.1016/j.ahj.2016.04.021：治疗强化型院内 WHF 的预测先例。
- Chapman WW, et al. NegEx. 2001. doi:10.1006/jbin.2001.1029：临床文本否定识别的可解释规则基础。
- Irvin J, et al. CheXpert. 2019. doi:10.1609/aaai.v33i01.3301590：胸片报告概念、不确定性和专家标注的重要性。

## 10. 工作量与优先级

| 阶段 | 主动工时 | 外部等待 | 交付物 |
|---|---:|---:|---|
| BigQuery 106/107 | 已完成 | 用户运行查询 | raw reports + patient summary |
| 报告清洗与抽样包 | 2-4 h | 无 | blinded annotation CSV |
| 临床人工标注 | 4-8 h | 临床标注者 | adjudicated labels |
| 规则锁定与表型审计 | 4-8 h | 无 | final phenotype report |
| 最终模型重建 | 8-16 h | 计算 | locked Fine-Gray analysis |
