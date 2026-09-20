# DHF临床预测模型：任务总览

更新：2026-09-20 CST。当前优先级：**按科学问题→时间轴→DHF表型→T12风险集→结局→模型验证的逻辑链，完成双库临床复核和终点可观察性核对，并完成 MIMIC 实验室正式主线重构，再冻结队列、变量与模型。** 工作簿仅用于漏项检查和复现性审计，不替换本项目的研究定义。

## 一句话状态

MIMIC主窗口放射科报告已完整导出，raw 实验室合同及下游路径已通过 PostgreSQL 实际 QC；院内已完成全量时间门控和工作清单。但双库最终DHF表型、同口径三态结局和正式模型仍未冻结，当前仍处于队列/表型复核阶段。

## 研究主线

完整的六步递进关系见[研究逻辑链](RESEARCH_LOGIC_CHAIN_20260916.md)：前一步输出是后一步输入；最终结果不能反向改变已定义的时间窗、表型或终点。

成人index ICU的DHF操作性表型患者，在T12仍存活且留在index ICU；用`[T0,T12)`可得信息，预测T12后至`min(T60, alive index-ICU discharge)`的`treatment-escalation-based ICU hemodynamic deterioration`。Fine-Gray为主模型，alive ICU discharge为竞争事件，1 h person-period为补充，early sepsis为预设亚组。主终点不能称为纯cardiogenic shock，NT-proBNP >=300不能称为DHF确诊阈值；正式阈值及排除见[统计方案](STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md)。

MIMIC用于开发/内部验证，本院用于锁模外部验证。院内8,385是按床旁心超候选导出后筛出的成人index ICU分母，不是全院成人ICU分母，也不是最终DHF人数。MIMIC Echo strict draft仅6例，不能作为开发队列硬门槛；院内仍保留`performed + result available + abnormal support`的echo-supported严格层。

## 已验证事实

| 工作台 | 已完成成果 | 可靠数字与证据路径 |
|---|---|---|
| MIMIC主窗口放射科 | GCS完整导出后，Parquet/CSV通过行数、键唯一性和stay-level对账 | 7,828/7,828报告、3,886个有主窗口报告的stay；[主窗口审计](bigquery/landmark12_audit_20260904/DHF_MULTIDOMAIN_AUDIT_LANDMARK12_2026-09-04.md) |
| MIMIC新临床标注包 | 新`[T0-24 h,T12)`抽样包已生成：每个规则层100条，另有60条盲法round 2包 | 300条round 1、60条round 2；[标注包说明](bigquery/controlled_annotation_20260904_landmark12_complete_v2/README.md)。300条仍待临床人工最终确认，Codex草案不是金标准 |
| 院内时间门控 | 成人、键唯一性、T12偏移、出ICU顺序、可用时间窗均通过QC；原始DHF_SRR未修改 | 8,385人、284,049条去重证据、20,025条目标医嘱、3,720人同窗BNP；[QC](internal_validation/20260915_source_review/qc.json)、[验证QC](internal_validation/20260915_source_review/validation_qc.json) |
| 院内复核工作台 | 22例时间源、7例原定向语义复核及新增11例逐例原文复核已留痕；36份空模板剔除、1份矛盾文书隔离；8,385行互斥队列工作状态完成 | 修正后优先235例、T12观察链91例、HF锚点42例；新增11例（DHF支持6、DHF不足2、心源性归因未定3）；[工作清单QC](internal_validation/20260916_semantic_corrected/worklist_qc.json) |
| 当前病例来源缓存 | 修正后工作清单的文书和护理备注已重新按同一运行缓存 | 368例（15,105条文书、528条护理备注）；[缓存QC](internal_validation/20260916_case_review/source_cache_qc.json) |
| 院内乳酸/风险代理 | 两张全量检验表按报告时间重建前12小时乳酸，并与有效静脉血管活性医嘱交叉 | 26.7万乳酸报告、12,757条BNP；6,432/8,385例有同窗可解析乳酸；源文件单位字段缺失，但研究者已确认乳酸为mmol/L；[乳酸QC](internal_validation/20260916_semantic_corrected/lactate_qc.json) |
| Gate3 45例语义优先队列 | 已完成保守预审核并记录逐例证据，结果不外推为全量临床金标准 | 8例保留候选、37例保守排除、0例未决；[审计表](internal_validation/20260912/internal_gate3_semantic_evidence_20260914_adjudicated.csv) |
| 方法与论文合同 | 双库表型框架、14阶段流程、开题方法初稿和文献映射已落盘 | [表型合同](DHF_OPERATIONAL_PHENOTYPE_v20260914.md)、[论文流程](PAPER_WORKFLOW_20260915.md)、[方法初稿](PROPOSAL_METHODS_DRAFT_20260915.md) |

## 初步或历史结果（不得作为论文最终结果）

- 修正后规则预审核为865 `probable_dhf`、1个旧技术名`confirmed_dhf`、7,387不支持、132未知；这866例是规则支持候选，**不是临床确认DHF人数**。新增11例原文复核状态仍为AI预审，不是临床金标准。
- MIMIC 300条既有AI/草案回连到7,828条主窗口报告后，肺充血筛查层为675人；`5,549 / 452 / 2,934 / 2,163`及任何分层事件数只是候选证据层，**不是最终DHF队列或最终结局结果**。见[回连QC](bigquery/review_linkage_20260915/qc.json)和[分层表](bigquery/review_linkage_20260915/evidence_layer_counts.csv)。
- 全部匹配心超报告可用2,827人、异常规则支持1,083人；名称明确床旁/床边且同窗结果可用2,599人（修正后运行）。它们受报告时间代理、范围及异常规则影响，不是DHF人数，不能与旧`2,519/2,517/2,475`直接纵向比较。
- 旧`2,424/334`、旧`outputs/`、`outputs_v2/`和旧宽口径Fine-Gray/person-period性能仅保留为可行性/历史诊断材料。**需清理旧文档**：继续核查PPT、旧报告或README中是否仍把上述数字写成最终论文结果。

## 当前工作台与阻塞问题

## 复现性控制（新增）

工作簿字段已转为项目级控制表：

- [项目级复现合同](DHF_PROJECT_REPRODUCIBILITY_CONTRACT_V1.md)：规定科学问题、两库角色、时间轴、表型、结局、缺失和冻结门控。
- [实验字段映射](DHF_EXPERIMENT_FIELD_MAPPING_V1.csv)：逐项检查工作簿字段在DHF方案中是否有对应物；映射不是把项目改成工作簿格式。
- [验收标准封存表](acceptance_criteria_frozen.csv)：只保存看结果前的达标条件；`measured_value`目前留空，不能当作结果表。
- [运行登记](run_registry.csv)：每次实际数据处理追加一行，记录输入快照、脚本、seed、折索引、输出哈希和偏差说明。
- [医嘱代理分类规范](ORDER_PROXY_CLASSIFICATION_SPEC_V1.md)：明确持续泵入、区间重叠、单次点用、跨T0不确定和文书支持的区别。

因此，“完整实验方案”在本项目中表现为研究合同、步骤协议、验收标准和运行登记四类材料；工作簿的Prompt只是检查这些材料是否遗漏的参照，不是需要逐字复制的模板。

| 问题 | 下一动作 | 主动工时 | 计算/等待 | 风险 |
|---|---|---:|---:|---|
| 新主窗口300条临床标注未确认 | 临床标注round 1；若需要正式可靠性，第二位标注者独立完成60条round 2 | 5-10 h临床复核；60条约1-2 h | 人工排期 | 高 |
| 院内DHF与T12风险集未冻结 | 优先复核235例，并补91例T12观察链、42例HF锚点及规则阴性抽样 | 12-20 h | 低 | 高 |
| 治疗升级终点的执行/可用时间不完整 | 用医嘱、护理、文书重建组成与观察完整性；eMAR可得时做主定义/代理敏感性对照 | 6-12 h | 数据补提数天至数周 | 高 |
| MIMIC多域DHF未冻结 | 汇总HF anchor、失代偿、管理及替代解释；不因Echo strict draft仅6例放宽或强加心超门槛 | 6-12 h | 低 | 高 |
| 变量/语义合同未锁定 | 使用新增变量字典和语义规则词典完成字段、单位、缺失和A/B/C规则审计；版本锁定后重跑全量 | 4-8 h | 低 | 高 |
| MIMIC实验室正式流水线 | 阶段 C PostgreSQL 全库执行与硬门通过：classified 37,778,198、eligible 37,732,919，错误体液/反向时间/单位共隔离45,279；5,555行模型 base 对齐、episode 多匹配0 | 分解 BUN/肌酐/乳酸 raw-vs-derived 差异原因，补齐完整 v3.3 上游依赖后再逐文件评估晋级；当前仍 `allow_final_run=false` | 4-8 h | 高 |
| 最终模型尚未重跑 | 事件数决定低维参数后，运行嵌套MICE m=20、Fine-Gray、person-period和预设敏感性 | 8-16 h | 数小时至过夜 | 中 |

## 下一步7天计划

1. 完成新主窗口300条临床确认；明确是否启动第二位标注者对60条进行独立盲法复核并计算kappa。
2. 完成院内235例优先队列、91例T12观察链和42例HF锚点队列的病例级裁决，随后做规则阴性抽样，形成可审计`cohort_freeze.csv`。
3. 冻结MIMIC多域DHF操作性表型：HF anchor、独立失代偿/充血、T12前管理证据和替代解释分别记录，不把单项影像、BNP或检查流程当确诊。
4. 重建T12后事件、alive ICU discharge竞争事件和观察完整性；执行级eMAR/泵速缺失时，明确医嘱区间仅为预设代理敏感性。
5. 以最终事件数重新限定低维候选参数，运行嵌套MICE m=20、Fine-Gray主模型、1 h person-period补充模型及预设表型/缺失/结局敏感性。

## 已确认的三项主分析决定

1. **两库主队列口径（已确认）**：MIMIC采用多域DHF operational phenotype作为开发/内部验证主队列，不把心超设为硬门槛；本院以现有8,385名“床旁心超选择后的成人候选”作为外部验证抽样分母，同窗床旁心超结果可用层（当前2,599例）作为严格敏感性层。
2. **比较符号检验值（已确认）**：原始字符串、上下界和删失标志全部保留；`>xx/<xx`不改写为精确值，只有整个区间位于阈值一侧才进行阈值判定；BNP等右偏指标主分析用预先登记的保守边界代理，并报告右/左删失敏感性。
3. **治疗执行代理（已确认）**：eMAR暂不可得时，以未作废医嘱的开停时间和给药途径作为治疗暴露代理；不从总剂量推导泵速或NEE。取得eMAR后按同一冻结队列进行预设敏感性重跑，代理结果不能冒充执行级测量。

## 数据合同补全状态（不再重复向研究者索取已确认内容）

- BNP=`pg/mL`、乳酸=`mmol/L` 已登记为 `confirmed_user`；其他单位必须由字典或人工核对确认，不能仅凭数值范围静默推断。
- 变量字典和语义规则词典是正式队列/特征冻结的阻塞项；医嘱代理验证是正式结局冻结的阻塞项。
- AI 判读 provenance 不阻塞当前预审核，但必须在论文中披露并保存；已有11例结构化输出和来源行号，模型/prompt 未记录项已标明 `not_recorded`。
- MIMIC实验室V2已替代旧V1；v3.1 正式聚合与不可变审计快照重跑均已通过，BUN 非血液 itemid 已隔离；结果见 2026-09-18 执行报告和 cohort snapshot 报告。
- 2026-09-19 完成实验室流水线质量门阶段 A：167/167 SQL 已登记，`ACTIVE=0`，旧主线在 raw 合同层重构前禁止正式运行；103 条历史/审计风险已入账，不能解释为旧 SQL 已修复。
- 2026-09-19 完成实验室流水线阶段 C 数据库执行：14 个合同概念和 12 个硬门通过；BUN 错误体液 eligible=0，45变量表与5,555行 base 对齐，episode 多匹配=0。raw-vs-derived 检出 BUN 142 个 derived-only episode 及644条 T12 后才可用的 pre-T12 采样事件；原因待分层，正式入口仍未晋级。
- 近期方法复核确认：实验室名称正则只可发现候选，正式特征必须使用精确语义 allowlist；异常值、单位不符和 derived 漏失进入隔离审计，不静默删除或补零。
- 若论文报告 inter-rater reliability，需第二位临床标注者独立盲法复核；同一标注者重复复核不能产生独立 kappa。

## 文件入口

- [本周周报](reports/weekly/2026-09-15_weekly_report.md) / [当天自动化任务报告](task_reports/TASK_REPORT_2026-09-15.md)
- [院内8,385人处理状态](internal_validation/20260916_semantic_corrected/cohort_disposition_working.csv) / [修正后优先队列](internal_validation/20260916_semantic_corrected/priority_DHF_review.csv)
- [院内时间审计](internal_validation/20260915_source_review/encounter_icu_time_audit.csv) / [原文证据链](internal_validation/20260915_source_review/time_gated_evidence.csv) / [1,024份证据摘要](internal_validation/20260915_source_review/case_evidence_digest.csv)
- [MIMIC新300条临床复核包](bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_draft.csv) / [独立60条盲法包](bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round2_blinded.csv)
- [MIMIC完整主窗口审计](bigquery/landmark12_audit_20260904/DHF_MULTIDOMAIN_AUDIT_LANDMARK12_2026-09-04.md) / [MIMIC回连QC](bigquery/review_linkage_20260915/qc.json)
- [最新实质任务报告](task_reports/TASK_REPORT_20260920_PROPOSAL_REPORT_REFRESH.md) / [MIMIC BigQuery 阶段 C](task_reports/TASK_REPORT_20260920_MIMIC_BIGQUERY_PHASE_C.md) / [MIMIC来源登记](MIMIC_DHF_SOURCE_COVERAGE_LEDGER_20260916.md) / [旧总览归档](reports/RESEARCH_DASHBOARD_ARCHIVE_20260915_BEFORE_SIMPLIFICATION.md)
- [2026-09-20 新版开题报告及可编辑图示](../deliverables/opening_proposal_20260920/)
- [院内变量字典](INTERNAL_DHF_VARIABLE_DICTIONARY_V1.csv) / [语义规则词典](DHF_SEMANTIC_RULE_DICTIONARY_V1.md) / [MIMIC实验室语义审计V2](MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.md) / [候选发现SQL](MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql) / [AI provenance](internal_validation/20260916_case_review/AI_REVIEW_PROVENANCE.json)



## 质量保证与 MIMIC 访问复核（2026-09-19）

本轮确认：本机 `mimiciv31` PostgreSQL 核心 hosp/icu/derived 可只读调用；当前未发现 `mimiciv_note` 或 `mimiciv_ed`。BigQuery 最近记录为 API 可到达但 `physionet-data:mimiciv_hosp.d_labitems` 读取权限不足，不能按正式患者级取数处理。

质量判断：项目的复现合同、变量/语义字典、时间轴、竞争风险方案和 fail-closed 质量门较强；实验室阶段 C 数据库 QC 已完成，但最终 DHF 表型、T12 风险集、三态结局、临床标注、完整 v3.3 依赖链和最终模型尚未冻结。Prompt 是必要的审计入口，不是正确性的替代品。详细方案见 [项目质量保证与 MIMIC 访问复核](task_reports/TASK_REPORT_20260919_PROJECT_ASSURANCE_AND_MIMIC_ACCESS_REVIEW.md)。

## 更新日志

- 2026-09-15 16:13 CST：生成本周组会周报；总览改为已验证、初步/历史和待决事项分层；将新主窗口300条标注明确标为待临床确认。
- 2026-09-15：院内来源复核和互斥队列工作清单完成；MIMIC既有300条AI/草案回连审计完成，均不构成最终临床标签。
- 2026-09-16：补齐双库队列、比较符号检验值、单位缺失、异常值、缺失值和医嘱执行代理合同；新增MIMIC来源覆盖登记和数据清洗任务报告。
- 2026-09-16：登记院内 BNP/乳酸确认单位；新增变量字典、DHF语义规则词典、AI审核 provenance 和 MIMIC `labevents` 截断审计模板；明确五项工作的冻结门控级别。
- 2026-09-16：将工作簿定位为漏项检查框架；新增项目级复现合同、字段映射、封存验收标准、运行登记和医嘱代理分类规范。验收表暂不填实测结果。
- 2026-09-18：MIMIC-IV v3.1 实验室 V2 正式聚合完成；BUN 非血液 itemid 已隔离，结果和 BigQuery 作业证据已登记。
- 2026-09-19：完成 MIMIC 实验室流水线阶段 A 质量门；正式运行入口接入 fail-closed 预检，生成 167 行权威清单及 103 条历史/审计风险账本，未运行患者级数据库。
- 2026-09-19：完成 MIMIC 实验室流水线阶段 B；新增 raw 合同层、NT-proBNP 三态阈值、乳酸结局与紧凑预测变量复制修订，生成 173 行权威清单及 100 条历史/审计风险账本；PostgreSQL 数据验证未运行，正式主线未解锁。
- 2026-09-19：完成 MIMIC 实验室流水线阶段 C；PostgreSQL 全库合同层、12项硬门、NT-proBNP/乳酸下游、45变量及 raw-vs-derived 聚合审计均实际执行。修复063A历史字段重名；正式主线仍因完整依赖与研究定义未冻结而保持 fail-closed。
- 2026-09-20：按当前研究逻辑链重写学校开题报告，更新 T0/T12/T60 时间轴与双库技术路线；候选分母、AI 预审核、实验室 QC 和历史模型均按边界表述，未改变正式研究定义或冻结状态。

更新规则：总览只保留主线、可核验证据、当前阻塞和下一交付。最终论文人数、事件数和性能必须来自同一冻结run。

## 任务报告与文件整理（新增）

本项目正式研究资料统一以 `project_control/` 为根目录：

- 当前状态唯一入口：[RESEARCH_DASHBOARD.md](RESEARCH_DASHBOARD.md)
- 历史过程报告：[task_reports/](task_reports/)
- 报告规范：[task_reports/README.md](task_reports/README.md)
- 空白模板：[task_reports/TASK_REPORT_TEMPLATE.md](task_reports/TASK_REPORT_TEMPLATE.md)

涉及研究结论、队列、变量、结局、统计方法、数据处理、质量控制、模型运行或文件修改的实质任务，必须新增一份 `TASK_REPORT_YYYY-MM-DD_<TOPIC>.md`，并同步更新本总览的报告索引和更新日志。历史报告不得覆盖；结论变化必须写明“旧结论 → 新结论 → 修正原因”。

本轮新增报告：

- [开题报告按当前研究主线重写与图示更新（2026-09-20）](task_reports/TASK_REPORT_20260920_PROPOSAL_REPORT_REFRESH.md)

- [变量筛选与 Prompt 审计（2026-09-17）](task_reports/TASK_REPORT_20260917_VARIABLE_SELECTION_PROMPT_AUDIT.md)
- [任务报告机制与文件整理（2026-09-17）](task_reports/TASK_REPORT_20260917_REPORTING_WORKFLOW.md)
- [沙盒与本机 Workspace 桥接确认（2026-09-17）](task_reports/TASK_REPORT_20260917_LOCAL_WORKSPACE_BRIDGE.md)
- [本机正式目录同步与重复文件清理（2026-09-17）](task_reports/TASK_REPORT_20260917_LOCAL_SYNC_AND_DEDUP.md)
- [本机 Git 初始化与安全边界配置（2026-09-18）](task_reports/TASK_REPORT_20260918_GIT_SETUP.md)
- [本地 Git 优先决策说明（2026-09-18）](task_reports/TASK_REPORT_20260918_GIT_LOCAL_ONLY_DECISION.md)
- [近期文献与 MIMIC 清洗方法复核（2026-09-17）](task_reports/TASK_REPORT_20260917_RECENT_LITERATURE_AND_MIMIC_CLEANING.md)
- [MIMIC-IV 实验室审计 V2（2026-09-17）](task_reports/TASK_REPORT_20260917_MIMIC_LAB_AUDIT_V2.md)
- 2026-09-18：已配置 GitHub SSH origin，仓库为 zheyucom/CS_AHF_landmark24。
- 2026-09-18：main 已推送并校验远程 SHA=46e382a7922d4ebf61bbe79ff215564dcde00c9a；本地与 origin/main 一致。

- [MIMIC-IV 实验室审计 V2 正式执行报告（2026-09-18）](task_reports/TASK_REPORT_20260918_MIMIC_LAB_AUDIT_V2_EXECUTION.md)
- [MIMIC-IV 实验室审计 V2 不可变 cohort 快照重跑（2026-09-18）](task_reports/TASK_REPORT_20260918_MIMIC_LAB_AUDIT_V2_COHORT_SNAPSHOT.md)
- [MIMIC 实验室流水线质量门阶段 A（2026-09-19）](task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_QUALITY_GATE_PHASE_A.md)
- [MIMIC 实验室流水线阶段 B：raw 合同层与主线复制修订（2026-09-19）](task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_PHASE_B.md)
- [MIMIC 实验室流水线阶段 C：PostgreSQL 执行与差异审计（2026-09-19）](task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_PHASE_C.md)
