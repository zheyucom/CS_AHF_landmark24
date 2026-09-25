# 研究一人工审核执行指南 V1

## 先回答你的问题

是的，需要逐例回到原病历系统核对；但不是核对全部 773 例。

- 主表型审核：290 例；
- 文本剂量/速率支持审核：154 条文本记录；
- 近边界补充包：100 例，可在主审核完成后再做，不作为第一轮必须任务。

CSV 中的摘要、行号和算法字段只用于生成审核包，不能代替原病历，也不能直接当作临床金标准。

## 一、主表型审核

推荐文件：

project_control/runs/20260924_internal_stage1_g3_phenotype/clinical_review_blinded_v1.csv

原始保留文件：

project_control/runs/20260924_internal_stage1_g3_phenotype/clinical_review_sample_v1.csv

### 每一例的操作顺序

1. 用 visit_id 或患者病历号在原病历系统打开本次 ICU 就诊。
2. 以 t0_time 为时间锚点，核对入 ICU 前 24 小时至 T12 的病历、检验、心超、影像和治疗记录。
3. 先独立判断总问题：本次 ICU episode 是否存在急性/失代偿性心力衰竭临床综合征？
4. 再分别判断 A、B、C 三个域。不要先看算法结果再倒推总标签。
5. 记录最关键的支持证据、主要替代解释、时间是否晚于 T0，以及关键缺失项。
6. 保存后再审核下一例。不要删除原始列或覆盖原始审核包。

### 允许填写的总标签

- DHF_yes：支持本次急性/失代偿性心衰；
- DHF_no：有足够证据支持其他解释，且本次不满足 DHF；
- indeterminate：证据冲突，无法明确判断；
- insufficient_data：关键资料缺失，不能判断。

### A/B/C 分域标签

每个域填写：

- yes：有明确支持；
- no：有足够资料明确不支持；
- unknown：未检查、缺失或时间语义不明；
- conflict：同一域证据互相冲突。

注意：

- 既往心衰史不能单独证明本次失代偿；
- 单个 NT-proBNP、单次 EF 或单条利尿医嘱不能脱离临床语境单独确诊；
- 没有记录不等于没有症状；
- T0 后出现的证据可以用于本次回顾性临床判断，但要在 comments 中注明“post-T0”。

## 二、文本剂量/速率审核

推荐文件：

project_control/runs/20260925_internal_stage1_text_dose_extract/text_dose_rate_review_blinded_v1.csv

一行代表一个文本药物提及，不一定代表一个患者，也不代表已经给药。

### 每一行的操作顺序

1. 打开 document_id 对应的原始病历文本。
2. 阅读完整上下文，不只看 CSV 片段。
3. 判断药物名称是否确实指向患者本人的目标药物。
4. 判断剂量是否属于该药物；如果同一段有多个药物且无法归属，填写 uncertain。
5. 判断速率是否为该药物的速率；ml/h 不能自动转换为剂量或 NEE。
6. 如果只是评分模板、参考范例、既往史、计划用药或否定语句，标记 false_positive 或 uncertain，并说明原因。

### 允许填写的字段

- review_status：confirmed / false_positive / uncertain / not_reviewable；
- confirmed_drug：yes / no / uncertain；
- confirmed_dose：yes / no / uncertain / not_present；
- confirmed_rate：yes / no / uncertain / not_present；
- review_notes：填写歧义、替代药物、否定、模板或时间问题。

## 三、盲法和双人审核

- 审核时不要查看算法标签、抽样层、死亡结局、短期代理事件或模型结果。
- 290 例主表型审核至少抽取约 20% 由第二名审核者独立复核；分歧交第三位资深医生裁决。
- 154 条文本复核至少抽取约 20% 双人复核；所有分歧记录并裁决。
- 如果当前只有一名审核者，可以先完成第一轮，但不能把单人结果写成正式一致性或金标准结果。

## 四、审核完成后交回的文件

请保留以下字段和原始行顺序，另存为带日期的新文件：

- clinical_review_completed_YYYYMMDD.csv；
- text_dose_rate_review_completed_YYYYMMDD.csv。

不要把患者姓名、身份证号或完整病历正文复制到 CSV；只保留项目已有的患者/就诊键和审核结论。
