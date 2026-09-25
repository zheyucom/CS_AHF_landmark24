# 研究一补充表目录与结果解释规范 V1

状态：工作稿；所有表格在临床表型审核和实验室元数据确认后重新冻结。

## 补充表 S1：来源抽样框与年度完整性

数据源：project_control/runs/20260923_internal_stage1_l0/calendar_year_counts.csv

内容：2021–2025 年候选 episode 数、2024 数据断层标记、排除 2024 年的敏感性层。

解释限制：不能把床旁心超选择后的抽样框当作全 ICU 患病率分母；2024 年不用于年度趋势推断。

## 补充表 S2：A/B/C 表型筛选流程

数据源：project_control/runs/20260924_internal_stage1_g3_phenotype/phenotype_flow_counts.csv

内容：候选 8,385；A、B、C 各域支持；主 A+B+C 773；严格客观层 594；严格 T12 风险集 558。

解释限制：这些是算法筛选计数，不是临床金标准计数；临床审核完成前应标注 algorithmic operational phenotype。

## 补充表 S3：心超可观察性与 EF 分型

数据源：project_control/runs/20260924_internal_stage1_g3b_echo_phenotype/echo_phenotype_v1_1_distribution.csv 和 project_control/runs/20260924_internal_stage1_g3c_echo_mapping/echo_mapping_audit.csv

内容：同次就诊心超、急诊—住院桥接、窗口外报告、HFrEF-supported、HFpEF-supported、EF 无法分类、报告内冲突和跨报告变化。

解释限制：有检查不等于窗口内可用；EF 未知不编码为正常；HFrEF/HFpEF 为规则支持表型，不替代临床确诊。

## 补充表 S4：合并症记录性负担

数据源：project_control/runs/20260924_internal_stage1_enrichment_audit/recorded_comorbidity_burden_distribution_v1.csv 和 project_control/runs/20260924_internal_stage1_g7b_documented_comorbidity/association_documented_comorbidity_sensitivity_v1.csv

内容：8 个合并症域的阳性、否定、冲突、unknown 状态；记录性域计数分布；扩展敏感性模型 OR。

解释限制：0 表示当前资料未检出阳性记录，不表示临床无病；OR 只作假设生成关联。

## 补充表 S5：早期实验室可用性和元数据缺口

数据源：project_control/runs/20260924_internal_stage1_enrichment_audit/lab_window_coverage_v1.csv、lab_source_dictionary_v1.csv、lab_first_value_distribution_audit_v1.csv

内容：T0 前 24 h 与 T0–T6 的覆盖率、报告可见时间、非血来源、异常值、单位和标本字段可用性。

解释限制：当前没有采样时间、独立标本字段和单位字段；单位确认前只作数据质量描述，不作临床数值解释或多变量模型。

## 补充表 S6：T0 评估和床旁生命体征导出质量

数据源：project_control/runs/20260924_internal_stage1_t0_vitals_and_timing_audit/admission_assessment_t0_coverage_v1.csv、bedside_timestamp_audit_v1.csv、bedside_item_window_coverage_v1.csv

内容：入院评估表 T0 可用性、重复冲突、范围审计、床旁测量时间戳覆盖和待补字段。

解释限制：入院评估表可代表 T0；纵向床旁记录必须有逐条测量时间，不能用 T0 语义替代。

## 补充表 S7：T0–T12 证据首次可见时间

数据源：project_control/runs/20260924_internal_stage1_t0_vitals_and_timing_audit/phenotype_evidence_timing_v1.csv 和 project_control/runs/20260924_internal_stage1_g2_chronology/chronology_summary.csv

内容：A、B、C 各域首次可见时间及三域齐备时间（T0、T0–T6、T6–T12）。

解释限制：用于展示回顾性确认的时间结构，不用于事后删选病例或重建死亡模型。

## 补充表 S8：T12–T60 短期代理结局和文本支持

数据源：project_control/runs/20260925_internal_stage1_treatment_proxy/stage1_treatment_proxy_features_v1.csv、project_control/runs/20260925_internal_stage1_text_dose_extract/text_dose_rate_review_strata_summary_v1.csv

内容：81 个医嘱/管路代理事件、150 个竞争事件、273 个未观察事件、54 个 unknown；目标药物提及、剂量/速率文本和分层复核抽样比例。

解释限制：医嘱区间为 order-based treatment exposure proxy；文本 NLP 为支持性证据；不称 eMAR 执行，不把 unknown 或未观察到事件当阴性。

## 表格生成顺序

1. 先生成不依赖临床金标准的 S1、S5、S6、S7；
2. 完成临床表型审核后冻结 S2、S3；
3. eMAR 或人工文本复核完成后更新 S8；
4. 最后更新主表 1–5、图 1 和摘要数字，运行全文数字审计。
