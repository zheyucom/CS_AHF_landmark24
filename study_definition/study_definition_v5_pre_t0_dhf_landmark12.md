# Study Definition v5.7: Echo-supported DHF Identified by T12 and 12 h Landmark Prediction

更新日期：2026-09-03  
状态：基于 ESC 2026 的方案修订稿 v5.8；MIMIC 主开发队列采用多域 DHF 操作性表型；`echo-supported DHF ICU cohort identified by T12` 仅为高特异性验证/院内严格验证层；最终主模型待主表型冻结后重建

## 1. 研究问题

在成人首次 ICU stay 中，针对在 `T12` 前已具有可时间追溯的**失代偿性心衰（DHF）操作性表型**、且 ICU 最初 12 h 尚未出现 overt shock proxy 的患者，能否利用 ICU `0-12 h` 可获得的信息预测随后 `12-60 h` 内的治疗升级相关 ICU 血流动力学恶化？

本研究预测的是 DHF 后续向循环支持升级、低灌注或 mixed circulatory failure 演进的风险；不直接诊断 DHF，也不把主终点写成临床确诊心源性休克。

## 2. 临床概念和时间分离

ESC 2026 以 DHF 替代 acute HF。DHF 可急性或渐进起病，临床概念包括 HF 症状/体征、紧急医疗关注及启动/强化治疗。MIMIC-IV 不具备完整的实时症状、体征和医师诊断流，因此只能建立操作性表型。

| 层级 | 可用时间 | 本研究用途 |
|---|---|---|
| DHF 入组证据 | `[T0-24 h,T12)` | 证明截至 T12 已可时间追溯识别 HF 失代偿；不要求 T0 时已经确认 |
| 预测变量 | `[T0,T12)` | 预测风险，不含资格/结局变量 |
| 结局证据 | `[T12,T60)` 或更早 alive ICU discharge | 定义后续 hemodynamic deterioration |

T0 前的利尿/治疗强化可用作 DHF 管理证据；T12 后相对 pre-T12 基线的 vasoactive/inotrope 升级才可用于结局。两者不可跨越时间边界。

### 2.1 开发队列与院内验证队列

`echo-supported DHF ICU cohort identified by T12` 是本研究的高特异性确证层：患者必须是 index ICU stay，且在 `T12` 前完成 TTE、TEE 或心脏 POCUS/床旁心超，有可解析结果支持心脏结构或功能异常，并结合肺充血/临床失代偿和治疗强化证据。心超是该严格层的必要客观心脏证据，不是可选协变量；但它不是 MIMIC 主开发队列的硬门槛。

这里的“做了心超”必须是三级证据链：`performed`（实际完成，不是医嘱）+ `result available`（结果在 `T12` 前可获得）+ `abnormal support`（结果内容支持结构或功能异常）。HFpEF 不能用“LVEF >=50%”简单判为心超阴性；应检查舒张功能/充盈压、左房扩大、左室肥厚、肺动脉压、右心功能、瓣膜病等结果。反之，只有检查记录而没有结果，或报告明确正常但没有其他心脏异常支持，均不能进入严格 `echo-supported` 层；这表示“该严格表型不可评估/未满足”，不等于临床上排除了 DHF。

临床指南通常要求对疑似急性/失代偿性心衰尽早进行超声评估，但指南建议不等于 MIMIC 中每个 ICU 患者都一定留下可用的 TTE/TEE/POCUS 结果。床旁心超也可能未执行、未结构化记录或结果无法回溯。因此提数阶段必须保留完整 ICU 候选宇宙，并报告心超完成率、结果可用率、异常支持率及由此产生的选择性；不能把未找到心超记录编码为阴性。

MIMIC-IV-Echo v1.0.1（[官方页面](https://physionet.org/content/mimic-iv-echo/1.0.1/)）现已完成 schema 与行级时间窗审计：`echo_study_list` 提供 `study_datetime` 和关联 note 的 `note_charttime`。在 5,549 个有效候选中，`[T0-24 h,T12)` 内仅 61 例有链接 TTE/TEE、9 例关联 note 在 T12 前、6 例同时具结构化异常支持。`note_charttime` 仍仅为结果可用的代理，不是独立签署时间。故 MIMIC 不适合将 Echo 结果作为主开发队列的纳入硬门槛；否则会导致极端检查选择和没有足够样本/事件的预测模型。

最终主模型的硬门槛改为：**MIMIC 开发队列必须有预先冻结、时间可追溯、经抽样人工复核的多域 DHF 操作性表型；不得把 BNP/利尿剂、单张胸片或 Echo procedure 单独视作确诊。** Echo 用于病例级表型验证和高特异性敏感性；院内可按同样的多域桥接层及更严格 `echo-supported` 层分别报告。在此门槛满足前，现有 v3.3 性能仍为历史/诊断结果，不是最终主模型结果。

## 3. DHF 表型层级

### 3.1 回顾性 HF anchor

本次住院最终 HF ICD 和诊断序位只用于回顾性确认 HF 背景与审计，绝不进入预测器，且不代表实时诊断时间。DHF 可以是既往 HF 失代偿或 de novo HF，故不要求最终编码必须为 acute/acute-on-chronic HF。

### 3.2 心超、胸片与胸部 CT 的证据优先级

心超是本研究最优先的客观心脏证据，且必须在最终表型中实际使用“结果内容”，而不是仅使用 TTE/TEE 操作记录。它回答的是心脏结构、收缩/舒张功能、右心负荷和瓣膜病等问题；胸部影像不能替代这一层证据。严格验证主队列要求每例患者在 T12 前有实际可解析的心超结果并支持异常；未检查、结果缺失或仅有操作记录者不进入严格队列，但保留在全 ICU 候选宇宙用于选择性审计。未检查或结果缺失不能被编码为心超阴性。

胸片与胸部 CT 是互补而非相互替代的肺部充血证据，二者均不能单独确定 DHF 的心源性病因。主影像规则采用 CXR OR CT，意思是“只要已完成的一种检查明确提示肺水肿/肺血管充血，即可构成肺部证据域”；不是说胸片单独即可诊断 DHF。CXR AND CT 仅作为严格敏感性分析，因为 CT 并非疑似 DHF 的常规必做检查，通常因 PE、肺炎、ARDS 或诊断不确定性而选择性完成；强制双检查会造成严重检查选择偏倚。胸部 CT 还用于识别替代或并存诊断，但 CT 缺失不能当作阴性。当前患者级审计中的 425/55/449/31 是严格 ICU 前可见 definite CXR/CT、CXR OR CT、CXR AND CT 数字，不能直接当作主窗口最终入组数。

心超是最重要的客观心脏证据域。最终院内严格队列为 `echo-supported DHF`：要求 T12 前存在可用心超结果，且结果支持心脏结构或功能异常；同时仍需肺充血/临床失代偿和管理强化证据。不能把“完成心超”当成异常，也不能把未检查或结果缺失判为阴性。由于这是一个检查选择性人群，必须从全 ICU 候选宇宙起步，报告心超完成率、结果可用率、异常支持率和严格队列与未入组者的差异。MIMIC 主开发队列则使用预先冻结的多域表型，并将可获得的 Echo 结果用于验证该表型的特异性和选择性；论文不得把 MIMIC 多域模型冒充为严格 Echo 队列模型。

证据按以下层级记录：

1. **心超优先证据**：TTE/TEE 的检查完成时间和可用的结构化结果；LVEF、左右室功能、瓣膜病、心房扩大、IVC/肺动脉压或舒张功能等仅在结果确实存在且时间早于 `T12` 时使用。做过心超只能证明“有检查”，不能代替“心超异常”。
2. **肺部充血证据**：胸片（肺血管充血、间质/肺泡水肿）和胸部 CT（间质/肺泡水肿、肺血管充血相关改变、双侧胸腔积液）是互补来源。主规则使用 `CXR OR CT`，不要求两者同时存在；CT 未检查不能当作 CT 阴性。
3. **临床/管理证据**：可时间定位的呼吸困难、体征、医生评估，以及实际 IV 袢利尿剂、血管扩张或无创通气等治疗/管理强化。治疗证据不能单独证明心源性病因。
4. **NT-proBNP**：只作支持证据，不能单独确诊；肾功能异常、房颤、肺栓塞、肺高压和脓毒症等均可升高 NT-proBNP。

因此，胸片单独不足以确诊 DHF；胸部 CT 可以作为互补肺部证据，但“胸片+CT 必须同时阳性”也不是主纳入规则。最终表型至少须把肺部证据与 HF 背景和治疗强化相结合；心超结果可用时还须优先用于心源性佐证。`echo-supported` 与 `echo + lung imaging` 是预设的高特异性确证层，而不是把 CXR-only 结果误写为 DHF 金标准。

### 3.3 DHF candidate

当前第一版患者级审计已完成：5,549 个有效 stays，结局为 452 event、2,934 compete、2,163 censor；462 例有 TTE/TEE 检查记录，但可用结构化 LVEF 为 0。因此现阶段不能声称建立了完整 echo-confirmed DHF 层，心超检查记录只能作为数据可用性字段。

`HF retrospective anchor` 加至少一项 pre-T0 时间戳支持证据：实际 IV 袢利尿剂 eMAR、NT-proBNP 或其他已审计证据。NT-proBNP 单独只能构成 candidate，不构成 DHF 确诊。

### 3.4 Multidomain DHF（拟定主表型）

拟定主表型同时满足：

1. `HF retrospective anchor`；
2. 一个时间合规的失代偿佐证组合：优先为心超异常结果加肺充血/临床失代偿；在心超结果尚不可获得的数据层，至少为经否定词处理、人工抽样复核的 CXR 或胸部 CT 肺水肿/肺血管充血，加可时间定位的临床失代偿证据。单独 CXR、单独 CT、单独 NT-proBNP 或单独利尿剂均不满足此项；
3. 至少一项同一时间窗内的紧急管理/治疗证据：优先实际 IV 袢利尿剂 eMAR，其他治疗必须预先审计后才可加入。

高特异性确证层的准确命名为 `echo-supported DHF ICU cohort identified by T12`。其最低结构是：

```text
adult index ICU stay
AND reached T12
AND HF retrospective anchor
AND echo performed before T12
AND echo result available before T12
AND echo result supports cardiac structural/functional abnormality
AND lung congestion or clinical decompensation evidence before T12
AND urgent treatment/management escalation before T12
AND no pre-T12 overt shock proxy
```

未检查、结果缺失、结果不可解析或只有操作记录者不得进入高特异性确证层；应保留在 `DHF candidate`、`multidomain DHF` 或 `rule-supported operational phenotype` 审计层。若只有最终编码和 NT-proBNP/利尿剂支持，命名为 `DHF candidate`，不得作为已确诊 DHF；若只有影像规则支持但未取得完整临床/心超佐证，不能称作 Echo-confirmed DHF，但在经过时间审计和抽样临床复核后可构成 MIMIC 多域主表型。

预设分析报告 `DHF candidate`、`multidomain DHF`、最近24 h 证据、排除 BNP-only、PE 排除和影像阳性分层。若 multidomain DHF 的事件数不足，不能强行做高维模型，应将其作为高特异性表型验证。

### 3.5 左/右心受累与射血分数表型

HFrEF/HFmrEF/HFpEF-compatible 以及左、右、双心受累是预设的描述性/异质性表型，不能因临床重要性而在当前数据中直接拆成多个主模型。仅在 T12 前有可解析心超结果时，才按 LVEF、舒张/充盈压、左右室功能、瓣膜病、TR/肺动脉压等预先冻结字段分类；未做或不可评估者单列，不插补为正常。主模型仍预测统一的治疗升级相关 ICU 血流动力学恶化；只有各亚型的事件数、表型可靠性和低维参数上限均满足预设要求时，才进行交互或分层表现分析。详细计划见 `project_control/DHF_SUBTYPE_ANALYSIS_PLAN_V1.md`。

## 4. 其余研究合同

- 分析单位：每患者 index hospitalization 内第一次 ICU stay。
- 主研究入组：患者到达 `T12`，并在 `[T0-24 h,T12)` 内具有可时间追溯的 DHF 证据；不要求 `T0` 或 ICU 入科前已完成 DHF 确认。
- `pre-T0 DHF`（证据全部发生于 `T0` 前）仅作严格敏感性分析。
- T12 前死亡/不能到达 landmark 者排除。
- T12 前 overt shock proxy 仅作风险集排除，不作为临床确诊 CS。
- ACS、CKD/AKI/ESRD、PE、肺炎/ARDS 和 COPD 不作机械性全排；它们可为 DHF 诱因或并存病。主表型必须有 HF anchor 加独立失代偿证据；“孤立替代诊断且无心脏证据”作为高特异性排除敏感性。
- BNP/NT-proBNP、IV loop 或最终 HF ICD 均不能单独确诊 DHF；BNP-only 不进入拟定 multidomain 主表型。
- 主事件：T12 后循环支持升级或 NEE 相对 pre-T12 基线持续升高，或 ICU 内死亡。
- 竞争事件：alive index-ICU discharge。
- 主模型：Fine-Gray；1 h person-period 是补充。
- 主结局名称：`treatment-escalation-based ICU hemodynamic deterioration`。
- strict shock/CS-like proxy 作为次要结局/敏感性；不把 mixed-physiology 主结局称为纯 CS。
- 所有 preprocessing、插补、变量选择和权重拟合必须训练折内完成。

## 5. 当前执行门槛

本轮已完成 108 结构化心超审计、患者级多域审计以及 MIMIC-IV-Echo 行级审计；后者生成 `echo_result_audit_v1`，实测 61 个窗口内 Echo-linked studies、6 个 high-specificity draft。院内严格表型仍为 `echo-supported DHF ICU cohort`；院内全量心超数据尚未取得。最终模型不得建立在“仅 final ICD + BNP/利尿剂”或“仅胸片规则阳性”的队列上，也不能把 MIMIC 多域模型直接宣称为院内严格 Echo 队列的外部验证。

1. 已完成 106/107 和 300 条报告第一位标注；60 条重复为同标注者复制，不能作为独立 kappa。
2. 对 MIMIC 的 61 个 Echo-linked studies 分层抽样人工复核，验证结构化 abnormal-support 草案；院内仍必须提取 TTE/TEE/POCUS 结果、检查时间和报告可用时间，且不得把“做过心超”当作异常。
3. 审计 CXR-only、CT-supported、CXR-or-CT、echo-confirmed、echo+lung-imaging 各 DHF 层级的 stay 数、事件数、竞争事件和缺失性。
4. 在 MIMIC 多域主表型事件数确定后冻结模型特征数和运行最终模型；院内严格 Echo 队列作为外部验证的高特异性层，并同时报告与之可桥接的多域层。

## 6. 关键来源

- Kober L, Adamo M, et al. *2026 ESC Guidelines for the management of heart failure*. *Eur Heart J*. 2026. doi:10.1093/eurheartj/ehag100.
- Walsh MN, et al. *Second Universal Definition of Heart Failure*. *Eur Heart J*. 2026;47:4357-4374. doi:10.1093/eurheartj/ehag500.
- 完整影响评估：`project_control/reports/2026-08-29_ESC2026_DHF_implications_and_protocol_update.md`。
