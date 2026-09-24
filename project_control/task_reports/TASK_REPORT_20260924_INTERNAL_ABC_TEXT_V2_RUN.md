# 任务报告：本院 DHF 文本分析 V2 与结构化诊断召回层

日期：2026-09-24  
状态：V2 已运行；临床校准与最终队列冻结仍未完成  
任务：把“目前考虑心衰，予相应治疗”纳入文本分析，同时保留可审计逻辑和 V1 历史快照。

## 一、执行结论

已完成一套不看结局的 V2 规则和全量运行。V1 的 773 例没有被覆盖，V2 仅作为新增召回/敏感性层：

| 层级 | V1 | V2 | 变化 |
|---|---:|---:|---:|
| 8,385 例来源候选 | 8,385 | 8,385 | 0 |
| A 域支持 | 2,035 | 2,056 | +21 |
| 主 A+B+C 算法队列 | 773 | 784 | +11 |
| 严格客观层 | 594 | 599 | +5 |
| 主队列严格 T12 风险集 | 558 | 564 | +6 |
| 主队列宽松 T12 敏感性层 | 601 | 608 | +7 |
| 严格客观 T12 风险集 | 417 | 420 | +3 |

新增 11 例主队列中，10 例来自文本“当前/考虑心衰 + 明确针对性治疗”，1 例来自 T12 前结构化“补充诊断：急性心力衰竭”。V2 仍是算法标签，不是临床确诊。

## 二、实际处理流程

1. 读取 V1 G3 账本、原始时间门控证据和隔离文书清单；
2. 保持 V1 同一时间门控文书来源，不扩大到未审计的全量文书宇宙；
3. 在当前 episode 的 T0−24 h 至 T12 窗口重新分析心衰文本；
4. 识别 HF 判断、治疗词、句间距离、当前/既往/否定/假设/低概率/鉴别语义；
5. 对同句或相邻句的“当前/考虑 HF + 明确 HF 治疗”标记 affirmed_with_treatment_support；
6. 对同段较远文本标记 probable_current_hf，只进复核队列；
7. 读取同次就诊结构化诊断，按诊断类型和时间窗单独审计；
8. 仅重算 A 域，再重算 A+B+C 主层和严格客观层；
9. 输出 V1→V2 转换矩阵、病例级来源、文本证据、结构化诊断证据和 QC。

## 三、边界规则与修正记录

初次运行发现“心源性休克可能性小”和“必要时利尿”可能被错误升级。已加入并测试：

- 低概率表达：可能性小/低、可能不大、不太可能、可能性不高 → 不自动升级；
- 条件性处置：必要时、如出现、若……则 → 不自动升级；
- 问号不确定：心功能不全？ → 不自动升级；
- 抗感染单独出现 → 不支持 HF A 域；
- 鉴别诊断、既往史、风险告知 → 不支持自动升级；
- 同句/相邻句是唯一自动升级距离；远句只进复核。

## 四、测试与验证

新增语义测试 11 项全部通过，覆盖：

- 同句、相邻句自动升级；
- 无明确治疗不升级；
- 鉴别诊断、风险告知、既往史、抗感染不升级；
- 远距离文本仅复核；
- 低概率、条件性治疗、问号表达不升级。

针对性回归测试通过：

- V2 文本测试；
- 原 G3 表型测试；
- G1 范围、G2 时间轴测试。

全量 project_control/tests 共 93 项：88 项通过，5 项失败/错误均来自本轮之前的既有测试/未登记 SQL 状态，未涉及 V2 代码：

- test_audit_internal_stage1_enrichment.py 的既有接口/实验室语义断言；
- test_start_run_quality_gate.py 因工作区新增 SQL 未登记而按 fail-closed 阻断。

因此不能把全量测试写成“全部通过”；V2 自身及相关回归已通过。

## 五、交付文件

- V2 规则与实现：project_control/build_internal_stage1_g3_text_v2.py
- V2 测试：project_control/tests/test_internal_dhf_text_v2.py
- V2 规范：project_control/INTERNAL_DHF_TEXT_SEMANTIC_V2_SPEC_20260924.md
- V2 QC：project_control/runs/20260924_internal_stage1_g3_text_v2/qc.json
- V2 账本：project_control/runs/20260924_internal_stage1_g3_text_v2/dhf_abc_evidence_ledger_v2.csv
- 新增病例：project_control/runs/20260924_internal_stage1_g3_text_v2/newly_supported_cases_v2.csv
- 文本证据：project_control/runs/20260924_internal_stage1_g3_text_v2/text_semantic_evidence_v2.csv
- 结构化诊断证据：project_control/runs/20260924_internal_stage1_g3_text_v2/structured_diagnosis_evidence_v2.csv
- 远句复核队列：project_control/runs/20260924_internal_stage1_g3_text_v2/probable_text_review_queue_v2.csv
- V1→V2 转换矩阵：project_control/runs/20260924_internal_stage1_g3_text_v2/phenotype_label_change_matrix_v2.csv

## 六、重要限制

1. V2 复用了 V1 的时间门控文书来源，没有声称已经包含所有护理、SOAP、出院、放射报告或完整临床文书；
2. “予治疗”在当前院内数据中仍是文书/医嘱代理，不是 eMAR 实际执行；
3. V2 仍未经过临床金标准审核，不能计算敏感度、特异度、PPV 或 NPV；
4. V2 不能把 784 例写成“真实 DHF 人群”，建议正文称“V2 算法操作性候选/敏感性层”；
5. 结构化诊断时间窗外的 762 条诊断只作回顾性审计，不支持 T12 早期识别；
6. 下一步应先对新增 11 例和远句复核队列做不看结局的临床抽样校准，再决定是否把 V2 作为主分析敏感性层。

## 七、研究顺序建议

当前仍按：

V1 主分析快照 → V2 召回审计/校准 → eMAR 到位后执行级治疗重建 → 第一阶段冻结 → MIMIC 正式建模

V2 结果不用于修改 MIMIC 变量集，不用于根据院内结局挑选预测因子，也不解除临床表型校准和 eMAR 结局冻结门。
