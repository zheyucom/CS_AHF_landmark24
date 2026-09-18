# 任务报告：45例语义复核与300条影像预审核

日期：2026-09-14

## 已完成

1. 读取 `internal_gate3_semantic_evidence_20260914.csv` 的45例及对应 ICU 文书、诊断、BNP/NT-proBNP、袢利尿剂区间。
2. 建立保守预审核脚本 `project_control/adjudicate_gate3_semantic_queue.py`，过滤通用病危告知、APACHE/SOFA、呼吸治疗模板和“可能出现心衰”风险语句。
3. 生成：
   - `internal_gate3_semantic_evidence_20260914_adjudicated.csv`
   - `internal_gate3_semantic_user_check_20260914.csv`
4. 45例预审核结果：8例保留候选，29例保守排除，8例人工裁决。
5. 读取并预审核300条 MIMIC 胸部影像抽样，生成脚本 `project_control/bigquery/pre_review_dhf_radiology_300.py` 和输出：
   - `dhf_radiology_annotation_round1_codex_prereviewed_20260914.csv`
   - `dhf_radiology_annotation_round1_codex_prereview_user_check_20260914.csv`
6. 影像结果：胸部223、非胸部63、混合/不清14；明确充血97、可能充血8、无充血25、不确定170；31条列入边界复核。
7. 形成操作型表型文件：`project_control/DHF_OPERATIONAL_PHENOTYPE_v20260914.md`，明确 MIMIC 与院内的共同 A/B/C 证据域、时间窗、替代解释、冻结门槛及文献依据。

## 人工裁决队列（8例）

请只裁决“是否存在本次 episode 的患者特异性 HF 锚点 + 失代偿/充血”，不需要重新确认已锁定的 T0 语义。病例证据已在 `internal_gate3_semantic_user_check_20260914.csv` 中展开：

| 病例 | 当前冲突 | 需要裁决 |
|---|---|---|
| G3-014 | 腹腔感染/脓肿主导，但 NT-proBNP 5960→4800、湿啰音 | BNP 是否有慢性肾病/感染解释？是否有本次心衰诊断或心源性利尿/充血记录？ |
| G3-009 | 创伤性脑出血和股骨骨折，使用呋塞米，合并瓣膜/冠心病诊断 | 呋塞米是否因急性充血/心衰，而非常规液体管理？ |
| G3-010 | 脑梗死主导，BNP 检验“无殊” | 是否存在本次 HF/肺充血的患者特异性记录？ |
| G3-024 | 脑出血主导，NT-proBNP 98，模板提及心衰风险 | 是否有独立于模板的 HF/充血证据？ |
| G3-026 | 术后腹部疾病主导，存在通用危重风险语句 | 是否有实际心衰/肺充血诊断或治疗？ |
| G3-030 | 创伤性脾破裂、失血性休克主导 | 是否有明确心衰或心源性充血证据？ |
| G3-040 | 脑出血，双下肢凹陷性水肿、低氧和湿啰音 | 水肿/肺部表现是否被临床记录为心源性，还是脑出血/误吸/液体管理？ |
| G3-047 | 肾盂肿瘤术后，NT-proBNP 678→1138，既往心梗；无水肿 | 是否有本次 HF/肺充血诊断或心衰治疗，而非围术期风险评估？ |

## 冻结前仍需完成

- 人工裁决上述8例和影像31条边界行。
- 将裁决结果回写主表并重算最终 confirmed/probable/not-supported/unknown 数量。
- 补齐 ICU 内 hemodynamic deterioration、ICU death、存活出科的执行级时间和竞争事件编码，随后才能重算 Fine–Gray 与 person-period 模型。
