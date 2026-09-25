# 任务报告：研究一医嘱代理与文本剂量/速率抽取

日期：2026-09-25  
状态：`ORDER_PROXY_LAYER_COMPLETED / TEXT_SUPPORT_EXTRACTED / CLINICAL_SAMPLE_REVIEW_PENDING`

## 1. 本轮决策

研究一不再等待 eMAR 完整到位。现有有效医嘱区间在预先登记的代理层中按“已执行/已暴露”的操作性假设使用，作为照护路径和短期治疗升级代理；论文明确称为 `order-based treatment exposure proxy`，不称 eMAR 确认执行。

## 2. 结构化医嘱结果

- 主 A+B+C 队列：773 个 episode；
- 血管活性药/正性肌力药原子代理记录：1,488 条；
- 其中有结构化剂量和剂量单位：1,303 条；
- 有目标结构化医嘱区间：357/773 个 episode；
- 目标药物白名单和连续泵/静脉途径规则沿用既有 G4 版本；
- 不从总剂量反推泵速、NEE 或实际逐次给药时间。

## 3. 文本剂量/速率抽取

从主队列真实存在的 `02_rdr_medrecord_list.csv` 抽取目标药物附近的剂量、浓度和速率文字，并保留：患者/就诊键、文档编号、文书名称、创建时间、原文片段、来源文件与行号、药物极性。

- 有目标药物提及：766/773 个 episode，其中排除 SOFA/APACHE/评分模板等参考文本后，临床文书提及为 733/773 个 episode；
- 有局部剂量文字：686/773 个 episode，其中 672 个处于单一目标药物局部窗口；
- 有局部速率文字：199/773 个 episode，其中 125 个处于单一目标药物局部窗口；
- 抽取器：`regex_nlp_v1`；
- 极性：`affirmed_or_unqualified`、`uncertain`、`negated`；
- 文本提及不单独创建治疗事件，不覆盖结构化医嘱。

目标药物采用最长别名匹配，已排除“去甲柔红霉素”被误识别为去甲肾上腺素，以及异丙/去甲肾上腺素中的子串误计为肾上腺素。剂量/速率只在局部标点窗口内提取，避免把远处其他药物剂量借给目标药物。

## 4. 研究一中的使用方式

1. 主结果：继续报告 T12–T60 的医嘱区间治疗升级代理、存活转出、行政终止和 unknown。
2. 文本剂量/速率：作为剂量/速率支持性描述和人工抽样复核对象，不计算 NEE，不作因果治疗效应分析。
3. 81 个既有代理事件保持不变；不把 unknown 并入阴性。
4. 代理治疗结果不进入院内死亡主关联模型，也不用于筛选 MIMIC 变量。
5. eMAR 若后续获得，在同一队列、时间窗和聚合规则下重跑敏感性分析。

## 5. 生成文件

- `project_control/designs/INTERNAL_DHF_STAGE1_ORDER_PROXY_AMENDMENT_V1_20260925.md`
- `project_control/extract_internal_vasoactive_text_dose_v1.py`
- `project_control/integrate_stage1_order_text_proxy_v1.py`
- `project_control/runs/20260925_internal_stage1_text_dose_extract/target_drug_text_dose_rate_mentions_v1.csv`
- `project_control/runs/20260925_internal_stage1_text_dose_extract/summary.json`
- `project_control/runs/20260925_internal_stage1_treatment_proxy/vasoactive_order_proxy_enriched_v1.csv`
- `project_control/runs/20260925_internal_stage1_treatment_proxy/stage1_treatment_proxy_features_v1.csv`
- `project_control/runs/20260925_internal_stage1_treatment_proxy/summary.json`

## 6. 仍需完成

- 对目标事件及有剂量/速率文字的病例进行分层人工抽样复核；
- 核对文本剂量是否确实属于目标药物，而不是同一段落中的其他药物；
- 将代理层结果写入最终表 5 和路径图；
- 完成表型临床校准、伦理信息和全文数字一致性审计。


## 7. 论文同步与一致性审计

- 论文滚动稿已新增表 5，包含 558 人 T12 风险集、81 个代理事件、150 个竞争转出、273 个未观察事件、54 个 unknown，以及文本剂量/速率支持层。
- 已明确区分 766/773 个所有目标药物提及 episode 与排除评分模板后的 733/773 个临床文书提及 episode。
- 数字—文本一致性审计：`project_control/runs/20260925_internal_stage1_treatment_proxy/manuscript_number_audit_v1.json`，结果 `pass=true`。
- 目标药物文本抽样复核包：`project_control/runs/20260925_internal_stage1_text_dose_extract/text_dose_rate_review_sample_v1.csv`，共 154 条、81 个分层；已按显式布尔解析重生成，并纳入 mention_context 与 dose_rate_ambiguity 分层。
