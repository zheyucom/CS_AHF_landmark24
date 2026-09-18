# MIMIC 文本与影像信息用于 AHF 表型确认的可行性方案

日期：2026-08-28

## 结论

可以补充文本和胸片报告，但当前本机数据库尚未安装 `mimiciv_note`，也没有院内心超报告表。因此，现阶段不能直接从本机数据库提取症状、查体、胸片报告或医生首次诊断时间。

补装 MIMIC-IV-Note 后也不能完整解决实时确诊问题：该数据集主要包含 discharge summaries 和 radiology reports，并不是完整的急诊/住院医师实时病程记录流。出院记录可用于回顾性验证，但可能包含 ICU 后信息，不能未经时间截断用于 T0/T12 前预测或定义实时诊断时间。

当前 `650/66` 也不是“只靠 BNP 入组”，而是：

```text
acute/acute-on-chronic HF ICD
AND HF ICD sequence <= 5
AND [pre-T0 actual IV loop eMAR OR pre-T0 NT-proBNP >=300]
```

不过其中 `504/650` 属于 NT-proBNP-only，必须单独报告并做排除 BNP-only 敏感性分析；NT-proBNP 不能单独等同于 AHF。

## 可获得性矩阵

| 目标证据 | 现有结构化 MIMIC | 补装 Note/CXR 后 | 用途 |
|---|---|---|---|
| NT-proBNP | `mimiciv_hosp.labevents`，有数值和 `charttime` | 不需要 Note | 支持证据，不能单独确诊 |
| IV 袢利尿剂实际给药 | `mimiciv_hosp.emar`/`emar_detail` | 不需要 Note | 治疗过程证据，需严格识别 route 和给药状态 |
| ICD 诊断 | `diagnoses_icd`，通常没有临床下诊断时间 | 不变 | 回顾性诊断锚点 |
| 胸片报告 | 当前未安装 | `mimiciv_note.radiology` 或 MIMIC-CXR 报告/标签 | T0 前影像支持，按报告时间截断 |
| 症状、查体 | 当前未安装 | 不保证有完整 ED/住院 physician note | MIMIC 中通常不能完整恢复 |
| 医生首次 AHF 诊断时间 | 当前无 | discharge note 多为回顾性 | 不能作为可靠实时确认时间 |
| 肺超声 | 当前无稳定标准字段 | 通常不由 MIMIC-IV-Note 提供 | 不宜假定可获得 |
| 心超 LVEF/RV 功能 | 仅有检查/字段可用性审计 | 需要独立 echo 数据源/报告 | 不能用 Note 缺省替代 |

## 文本抽取的正确定位

补装后可对 `mimiciv_note.radiology` 做可审计规则抽取，识别肺水肿、肺血管充血、间质性水肿、胸腔积液、心影增大，以及“无肺水肿/无充血”等否定表达。每条命中应保留 `note_id`、`hadm_id`、`charttime`、报告章节、命中短语、否定状态和规则版本，并做人工抽样复核。

推荐先把 radiology 证据用于回顾性表型验证和敏感性分析，而不是直接替换主队列。出院总结中的 “acute decompensated heart failure” 可以验证最终表型，却不能证明 T0 前已诊断，也不能进入 0–12 h 预测器。

需要 dyspnea、orthopnea、PND、下肢水肿、JVP、湿啰音、医生 assessment 和首次诊断时间时，MIMIC-IV-Note 不是完整解决方案。若这些字段是研究合同的硬性金标准，应在本院具备实时病历的数据中提取；MIMIC 研究应使用 operational phenotype 表述。

## 推荐队列层级

### 主分析候选

继续使用已审计的 `650 stays / 66 events` strict pre-T0 操作性队列。论文中应明确它是 retrospective operational phenotype，而不是临床金标准。

### 文本/影像增强验证队列

补装 radiology 后增加：

```text
strict ICD anchor
AND pre-T0 radiology evidence of congestion/pulmonary edema
```

该队列用于报告结构化定义的影像支持比例，并比较 BNP-only、loop-only 与双证据组的一致性。胸片充血不特异，不能单独取代临床综合判断。

### 高特异性描述性队列

```text
strict ICD anchor
AND at least two of:
  pre-T0 actual IV loop eMAR
  pre-T0 NT-proBNP >=300
  pre-T0 radiology congestion/pulmonary edema
```

目前 loop+NT-proBNP 只有 `43 stays / 1 event`，加入影像后仍要先看事件数；事件不足时只做表型验证，不建高维模型。

## 其他疾病处理

BNP/NT-proBNP 会受肾功能、年龄、房颤、肥胖、肺栓塞、肺高压和脓毒症影响，但不能因此把 ACS、AKI/CKD、房颤、COPD 或肺炎全部排除。它们可以是 AHF 诱因、共病或并存综合征。

- PE：预设排除敏感性；
- 明确以 PE、ARDS 或肺炎为主且无充血证据者：在获得影像/文本后做替代诊断排除敏感性；
- ACS/AMI、AKI/CKD、房颤、COPD/哮喘：主分析保留，做共病/异质性分层；
- BNP-only：主候选中单独标记，并报告排除 BNP-only 敏感性。

## 实施顺序

| 步骤 | 工作 | 主动工时 |
|---|---|---:|
| A | 核对 Note/CXR 文件、版本和授权 | 0.5–1 h |
| B | 安装 `mimiciv_note` 并做行数/字段/键 QC | 1–2 h |
| C | 生成 radiology 章节、否定词、时间截断和证据片段 | 3–6 h |
| D | 盲法抽样人工复核 | 2–4 h |
| E | 接入 strict 队列，报告覆盖率和敏感性 | 2–4 h |

当前没有数据库认证信息，且 `mimiciv_note` 尚未安装，因此本轮没有伪造 Note 行数或覆盖率。安装完成后运行 `sql_v3_2/audits/100_audit_note_source_availability.sql`，再进入文本抽取。

## 参考来源

- MIMIC-IV-Note 本地建表定义：`/Users/zheyu/Desktop/Task/26.4 CS_403/mimic-code/mimic-iv-note/buildmimic/postgres/create.sql`
- MIMIC-CXR 文本处理：`/Users/zheyu/Desktop/Task/26.4 CS_403/mimic-code/mimic-iv-cxr/txt/README.md`
- 项目 AHF 表型审计：`project_control/reports/2026-08-28_ahf_screening_and_literature_review.md`
- ESC 2021 AHF 指南：doi `10.1093/eurheartj/ehab368`

