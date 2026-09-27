# 前30例表型审核诊断与住院期间新发AHF方向评估

日期：2026-09-27

## 1. 用户问题与本轮范围

1. 审查已完成的前30例人工标签，判断DHF比例低是否说明773例操作性队列失败。
2. 追溯290例的抽样来源，解释低BNP/NT-proBNP病例。
3. 核查一例T0错误并评估系统性风险。
4. 评估“入院时无AHF、住院后新发AHF”的独立研究方向。

## 2. 使用文件与版本

- `runs/20260924_internal_stage1_g3_phenotype/clinical_review_290_dropdown_20260927.xlsx`：研究者已填前30例。
- `runs/20260924_internal_stage1_g3_phenotype/clinical_review_sample_v1.csv`
- `runs/20260924_internal_stage1_g3_phenotype/review_sampling_manifest.json`
- `runs/20260924_internal_stage1_g3_phenotype/dhf_abc_evidence_ledger_v1.csv`
- `runs/20260924_internal_stage1_g3_phenotype/ntprobnp_rule_in_audit.csv`
- `build_internal_stage1_g3_phenotype.py`
- `INTERNAL_DHF_PHENOTYPE_CONTRACT_V1.md`

## 3. 已验证事实

### 3.1 290例不是全部来自773例

抽样分层为：

- 773例主算法支持层中：客观C层60例、治疗代理-only层60例；
- algorithmic unknown：50/132例；
- A+B但C不足：60/340例；
- 规则不支持随机：60/7140例。

因此只有120/290来自773例。抽样目的是同时估计误纳和漏诊，并非提供290个预期阳性病例。

### 3.2 前30例全部来自algorithmic unknown

生成脚本最终按`sample_stratum`排序，导致第1–50例均为algorithmic unknown。研究者前30例结果：

- DHF_yes：6；
- DHF_no：23；
- indeterminate：1；
- insufficient_data：0。

这30例不能估计773例的PPV。相反，若6个阳性经复核成立，提示A域召回可能不足；但标签尚未双人裁决，不能据此给出最终敏感度。

### 3.3 前30例存在两处确定的表内逻辑冲突

- `6614655_8`：总标签`DHF_no`，但A/B/C均为`yes`。
- `6506587_26`：总标签`DHF_yes`，但A为`no`；备注又称会诊考虑心衰肺水肿。

另需重点复核：复苏后EF35%是否为暂时性心肌顿抑、高BNP+既往心衰是否缺少当前B域、T0前一日事件是否在T0仍活动、急性右心衰是否属于目标综合征。

### 3.4 773例中的NT-proBNP结构

当前源数据只识别到NT-proBNP，没有独立BNP项目。773例中：

- 400例在T12前达到年龄相关NT-proBNP rule-in；
- 27例测过但未达到年龄rule-in，其中5例所有可用精确值均<300 pg/mL，22例位于300至年龄rule-in阈值之间；
- 346例T12前未观察到NT-proBNP结果；
- 594例属于客观C层，179例仅由静脉袢利尿医嘱代理支持。

因此不存在“大量已测NT-proBNP<300仍进入773”的现象；真正问题是未测者可被心超/治疗代理支持，以及当前“心超异常”可包含慢性结构异常。

### 3.5 BNP/NT-proBNP低值不能机械设为绝对排除

急性呼吸困难诊断Meta分析中，BNP<100和NT-proBNP<300的负似然比分别约0.11和0.09，属于强负证据，但并非绝对不可能；适用证据主要来自急诊呼吸困难人群，不能无条件外推至全部ICU。肥胖、极早期/快速肺水肿、HFpEF等可能出现相对低值。

推荐把BNP<100或NT-proBNP<300定义为`strong_negative_evidence`：触发人工复核/不一致层，而不是不看其他证据直接删除。

### 3.6 T0错误

`10832919_4`原T0为`2025-05-20 18:00:00`，来源`icu_discharge_note_admission_field`；研究者病历核对确认应为`2025-05-21 18:00:00`。该例属于algorithmic unknown，不在773例主算法队列，因此当前773计数不受此单例直接影响。

但该错误提示`icu_discharge_note_admission_field`来源可能存在日期解析/文书字段错配风险；正式冻结前需审计全部150例同来源T0，而不是只改一例。

## 4. 判断与影响

1. “前30例DHF少”主要由审核包按分层成组排序造成，不是773例PPV的证据。
2. 审核表顺序不理想，容易产生连续阴性造成的判断漂移；剩余病例应在保持盲法的情况下随机打散。
3. 773仍只能称工作版算法队列，不能冻结为临床DHF队列。V1必须保留作为审计基准；不能看到前30例后直接覆盖规则。
4. 当前最应收紧的是A域语境、B域替代解释、心超C域的急性相关性及治疗代理，不是把NT-proBNP设置为强制入组条件。
5. 住院后新发AHF是独立且有临床价值的研究方向，但与当前ICU prevalent-DHF研究的人群、T0、结局和部署场景不同，不应直接混入现主线。

## 5. 新增/确认的研究决策

### 5.1 当前表型校准

- 保留G3 V1，不重跑、不覆盖。
- 继续完成290例，但使用V2随机续审表。
- 新增T0状态和DHF相对T0发生时间字段。
- 对5例NT-proBNP<300但算法支持者做全量定向复核。
- 对治疗代理-only层在eMAR到位前只作为宽松层；严格客观层仍需临床校准。
- 完成审核后，按抽样概率加权估计总体性能；同时分别报告主支持层PPV、unknown层漏诊和各误分类机制。

### 5.2 候选V2规则方向（尚未实施）

- A域排除风险告知、鉴别诊断、既往史、模板和结局后回顾性语句。
- B域将孤立呼吸困难/湿啰音/水肿降为弱证据；肺炎、ARDS、PE、肾衰等替代解释进入归因裁决。
- C域区分急性血流动力学/充盈压证据与慢性结构异常；轻度瓣膜病、单纯心腔扩大不能独立救活弱A/B病例。
- NT-proBNP<300（或未来BNP<100）标记强负证据；存在明确例外时可保留，否则进入不一致审核层。
- IV袢利尿医嘱不能等同实际执行，也不能单独作为高特异性主层。

### 5.3 住院期间新发AHF

- 保存为独立扩展研究构想；先做全院小规模表型/事件时间可行性审计，再决定是否建动态预测模型。
- 正式分母必须为入院时无AHF的全部合格住院episode，不能只收集出院诊断含AHF的病例。
- 出院诊断/病程文本只用于候选发现；事件时间必须人工/规则重建。
- 首选普通病房动态landmark，预测未来24/48小时，不把事件后检查和治疗泄漏为预测变量。

## 6. 未决问题与阻塞项

- 前30例两个逻辑冲突及临床疑难项需研究者复核。
- 余260例和双人复核尚未完成。
- 150例`icu_discharge_note_admission_field`来源T0尚未系统审计。
- BNP项目当前未进入既有G3源数据；待新实验室提取后区分BNP与NT-proBNP。
- eMAR未到位，治疗代理不能升级为执行证据。
- hospital-onset AHF全院事件数、事件时间可定位率及预测窗前数据覆盖尚未知。

## 7. 下一步

1. 研究者先在V2表的“需复核”页处理前30例问题，再继续审核。
2. 完成50例algorithmic unknown后，进行一次阶段性一致性/误分类审计，但不改规则。
3. 同时审计150例低质量T0来源；校正后重切时间窗。
4. 完成全部290例并双人复核后，冻结临床参考标签，再评估是否形成G3 V2。
5. 对hospital-onset AHF先做3–6个月全院可行性审计，不立即建模。

## 8. 本轮修改文件

- `runs/20260924_internal_stage1_g3_phenotype/clinical_review_290_dropdown_v2_20260927.xlsx`
- `runs/20260924_internal_stage1_g3_phenotype/low_ntprobnp_under300_targeted_review_v1.csv`（5例定向复核，不属于原290例）
- `internal_validation/20260927_manual_review/t0_manual_corrections_v1.csv`
- `designs/HOSPITAL_ONSET_AHF_RESEARCH_CONCEPT_V1_20260927.md`
- `task_reports/TASK_REPORT_20260927_FIRST30_PHENOTYPE_REVIEW_AND_HOSPITAL_ONSET_AHF.md`
- `../literature_review/zotero_hospital_onset_ahf_manifest_20260927.csv`

Zotero已核验6篇核心文献：4篇新导入“短期恶化动态预警/方法学”，2篇为既有条目；item key见manifest。Obsidian已新增主题综述和6张证据卡，位置为`notes/literature/hospital_onset_ahf/`。

## 9. 可重复性信息

- 原抽样seed：`internal_dhf_g3_review_v1_20260924`
- V2剩余病例顺序seed：`stage1_review_continuation_v2_20260927`
- V2不使用结局、算法层、临床证据或人工标签决定剩余病例顺序。
- 原始CSV及用户已填V1工作簿均未覆盖。
