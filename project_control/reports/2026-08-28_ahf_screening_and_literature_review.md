# AHF 人群筛选审计与文献依据

日期：2026-08-28  
对应审计：`sql_v3_2/audits/099_create_ahf_phenotype_audit.sql`  
数据库表：`study_ahf_v3_2.audit_099_ahf_phenotype_v1`

## 结论先行

当前 v3.3 的 `5,555` 例应称为：

> 回顾性 HF ICD 锚定、并在 T12 前具有某种时间可追溯 HF 相关证据的 ICU 操作性队列。

不宜直接称为“5,555 例均已确诊急性心衰”。原因是当前队列门槛允许：

- NT-proBNP 只要被检测过，不要求 `>=300`；
- IV 袢利尿剂医嘱可以作为时间证据，未严格要求实际 eMAR 给药；
- 不强制最终 ICD 必须是 acute / acute-on-chronic HF；
- 主队列是“by T12”的广义口径，不保证 ICU 入科前已有客观 AHF 证据。

## 099 审计结果

| 证据层级 | stay 数 | 事件数 | 事件率 |
|---|---:|---:|---:|
| acute-HF ICD，但无合规 ICU 前客观证据 | 3,835 | 331 | 8.63% |
| 非急性或其他 HF 锚点 | 1,070 | 57 | 5.33% |
| 实际 IV 袢利尿剂 eMAR + NT-proBNP >=300 | 43 | 1 | 2.33% |
| 实际 IV 袢利尿剂 eMAR alone | 103 | 8 | 7.77% |
| NT-proBNP >=300 alone | 504 | 57 | 11.31% |

推荐的严格 pre-T0 AHF 操作队列为 `650/5,555 (11.7%)`，其中 `66` 个主事件，事件率 `10.15%`。最近 24 h 严格敏感性队列为 `378` 例、`34` 个事件，事件率 `8.99%`。

注意：共病计数不是互斥分类。严格候选队列中，审计标记包括 ACS/AMI `159`、AKI/CKD/透析 `448`、肺栓塞 `15`、肺炎/ARDS `162`、COPD/哮喘 `180`、肝病/肝硬化 `58`。

## 筛选是否需要排除其他疾病

### 不建议全部排除

ACS、CKD/AKI、房颤、COPD、肺炎等可以是 AHF 的诱因、并存病或鉴别诊断。若全部排除，会把真实临床 AHF 人群中最重要、风险最高的一部分删掉，并降低外部可推广性。

### 建议排除或单独处理

1. **肺栓塞**：作为预设敏感性排除，因 NT-proBNP 可因右心负荷升高，利尿剂也可能不是 AHF 特异治疗。
2. **明确非心衰主导的替代诊断**：若能取得急诊/入院主诊断、影像或医生诊断时间，建议排除“PE 主导”“肺炎/ARDS 主导”“孤立 ACS/AMI 主导”而无充血证据者。
3. **BNP-only 亚组**：不从主队列机械删除，但必须单独报告，并做排除 BNP-only 的敏感性分析。
4. **ACS、CKD、房颤、COPD/哮喘**：主分析保留，作为共病/效应异质性分层；不能仅凭存在该 ICD 就认为不是 AHF。

## 推荐的最终队列结构

### 方案 A：如果论文必须声称研究 AHF

- 主队列：`acute/acute-on-chronic HF ICD` + `HF ICD seq <=5` + ICU 入科前实际 IV 袢利尿剂 eMAR 或 NT-proBNP `>=300`。
- 目前审计规模：`650/66`。
- 主模型特征数应同步降至约 `6` 个有效参数以内，或明确采用强收缩/探索性建模；不能把原 45 特征模型直接搬过来。
- 敏感性：
  - 最近 24 h 证据：`378/34`；
  - 排除 BNP-only：`146/9`；
  - 排除 PE；
  - 高特异性“双证据”队列：`43` 例，仅作描述性分析，不适合建模。

### 方案 B：如果必须保留 5,555 例

论文对象应改写为：

> ICU patients with a retrospective HF diagnosis anchor and early HF-related operational evidence.

此时不能把队列称作临床确诊 AHF；应把 `650` 例严格 pre-T0 AHF 作为主要表型敏感性分析，并在摘要和局限性中说明表型误分类风险。

**当前建议：先按方案 A 完成表型敏感性重建和低维模型可行性评估，再决定是否保留方案 B 作为主分析。** 现有 5,555 例模型性能不能自动转移为严格 AHF 人群的最终性能。

## 文献中通常如何筛选 AHF

既往指南、注册研究和急性心衰试验通常不是单凭 BNP/NT-proBNP 入组，而是组合使用：

1. 急性呼吸困难或心衰症状；
2. 体征或影像学充血/肺水肿；
3. 医师对 acute decompensated HF 的临床判断或住院诊断；
4. BNP/NT-proBNP 作为支持性证据；
5. 利尿剂、血管扩张剂或其他急性心衰治疗作为治疗过程证据；
6. 同时记录 ACS、肾功能、肺部疾病等诱因和共病，而不是一概排除。

BNP/NT-proBNP 更适合作为“排除/支持”工具，而不是独立确诊标准。肾功能不全、高龄、房颤可使数值升高；肥胖可使数值偏低；肺栓塞、肺高压、脓毒症和右心负荷也会影响结果。因此，本数据库缺少症状、体征、胸片/肺超声和医生诊断时间时，必须使用“operational phenotype”措辞。

## 建议写入 Methods 的操作定义

> We defined a retrospective acute heart failure anchor using an acute or acute-on-chronic heart-failure discharge diagnosis coded within the first five diagnosis positions. To improve temporal clinical plausibility, the prespecified pre-ICU phenotype required at least one objective, time-stamped indicator before ICU admission: an actually administered intravenous loop diuretic documented in the eMAR or an NT-proBNP concentration of at least 300 pg/mL. Because symptoms, physical findings, imaging reports, and real-time physician diagnostic timestamps were not consistently available in MIMIC-IV, this definition was treated as an operational phenotype rather than a clinical gold standard. Acute coronary syndrome, kidney disease, atrial fibrillation, and pulmonary disease were retained as concurrent conditions and examined in sensitivity or subgroup analyses; pulmonary embolism and biomarker-only classification were assessed in prespecified exclusion sensitivities.

## 可核查参考文献

1. McDonagh TA, et al. 2021 ESC Guidelines for the diagnosis and treatment of acute and chronic heart failure. *European Heart Journal*. 2021;42:3599-3726. doi:10.1093/eurheartj/ehab368.
2. Fonarow GC, et al. Quality of care and outcomes in acute decompensated heart failure: The ADHERE registry. *Current Heart Failure Reports*. 2004. doi:10.1007/s11897-004-0021-8.
3. Januzzi JL Jr, et al. NT-proBNP testing for diagnosis and short-term prognosis in acute destabilized heart failure: an international pooled analysis of 1256 patients. *European Heart Journal*. 2006;27:330-337. doi:10.1093/eurheartj/ehi631.
4. Maisel AS, et al. Rapid measurement of B-type natriuretic peptide in the emergency diagnosis of heart failure. *New England Journal of Medicine*. 2002;347:161-167. doi:10.1056/NEJMoa020233.
5. Mueller C, et al. The use of B-type natriuretic peptide in the evaluation and management of acute dyspnea. *New England Journal of Medicine*. 2004;350:647-654. doi:10.1056/NEJMoa031681.

这些文献支持“临床表现/充血证据 + 医师判断 + 生物标志物 + 治疗证据”的组合思路，但不能替代对本数据库字段可用性的审计。

## 下一步

1. 不覆盖 v3.3 主结果，保留 5,555 例作为 broad operational cohort 历史/比较版本。
2. 以 650 例严格 pre-T0 AHF 队列建立独立候选建模输入，特征数按 66 个事件重新控制。
3. 输出排除 BNP-only、排除 PE、最近 24 h 和“双证据”敏感性结果。
4. 在得到导师意见前，不把 5,555 例的模型性能写成“确诊 AHF 患者模型性能”。
