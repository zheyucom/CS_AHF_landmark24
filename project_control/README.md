# CS_AHF 项目总控

更新时间：2026-09-04

> **日常主入口**：优先看
> [`project_control/RESEARCH_DASHBOARD.md`](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/RESEARCH_DASHBOARD.md)。
> 该文件实时维护研究方案总纲、当前进度、阻塞问题、预计投入和最新周报入口。

## 最终目标

使用 MIMIC-IV 开发并锁定一个可解释模型，预测具有 DHF 操作性表型的成人 ICU 患者在 ICU 入科
12 h landmark 后至 T60 或更早活着离开 index ICU 前的 ICU 内血流动力学恶化，
并在本院独立队列完成外部验证。early sepsis 为预设亚组，pre-T0 AHF 为严格
敏感性分析。所有论文数字必须能追溯到冻结协议、版本化 SQL、输入
校验和、配置、运行日志和输出文件。

## 当前结论

- 研究合同保留：每 patient index hospitalization 内首次 ICU stay；0-12 h predictors；T12 后至 T60 或 alive ICU discharge 前 outcome。
- 主结局称为 treatment-escalation-based hemodynamic deterioration，不称为
  纯 cardiogenic shock。
- 主模型升级为 Fine-Gray competing-risk model；1 h person-period landmark survival model 作补充。
- 旧结果方向稳定，但 `outputs/`、`outputs_v2/`、旧 `2,424/334` 和旧模型性能不是论文最终事实源。
- v3.2/v3.3 已完成 index-admission 队列、strict label、三态随访和 person-period QC。
- v3.3 45 个紧凑无泄露预测变量、白/黑名单审计及三表连接 QC 已完成；Fine-Gray 和 1 h person-period 的第一版 5 折 OOF 内部验证已完成。
- 旧 pre-T0 DHF 影像表型验证的 300 条第一位标注和 60 条同标注者重复已完成；当前完整 GCS 主窗口的新 300 条标注包仍待临床复核。患者级多域规则审计已完成第一版。用户已确认院内外部验证主队列为严格 `echo-supported DHF ICU cohort`；60 条同标注者重复不能作为独立 inter-rater reliability。
- 当前院内严格研究对象为：在 `[T0-24 h,T12)` 内具有可追溯 DHF operational phenotype、且到达 T12 的成人 ICU 患者；每例必须有实际完成、T12 前结果可用且支持心脏结构/功能异常的 TTE、TEE 或心脏 POCUS/床旁心超，同时具备肺充血或临床失代偿及治疗/管理强化证据。不要求 T0 入 ICU 时已经完成 DHF 诊断。全 ICU 候选宇宙仍保留，用于报告心超完成率、结果可用率和检查选择性；CXR 与胸部 CT 互补，`CXR OR CT` 为肺部宽口径审计，二者同时阳性仅作敏感性分析。
- 心超规则的三层状态必须分开：`echo_performed`、`echo_result_available`、`echo_abnormal_support`。仅有 procedure/order 或孤立 LVEF 数值不能直接证明 DHF；未检查、结果缺失和结果阴性也不能混为一类。MIMIC 的当前本地审计只有 462 例 TTE/TEE 操作记录、结构化 LVEF 0 例，故尚未形成 `echo-confirmed` 开发队列。
- 放射科标注已改为两步：先人工确认 `final_report_scope`/`final_modality`，再判读肺充血。胸片和胸部 CT/CTA 均可作为肺部证据；非胸部报告不进入肺充血 PPV 分母，不得标为 `no_congestion`；CT 未做不等于 CT 阴性，CXR+CT 同时阳性仅作敏感性分析。
- MIMIC-IV-Echo v1.0.1 已完成真实 BigQuery 行级审计：5,549 个有效候选中，`[T0-24 h,T12)` 有 61 例链接 TTE/TEE、9 例关联 note 在 T12 前、6 例同时满足当前 draft 异常支持。该覆盖不足以构成 MIMIC 开发端硬门槛，Echo 保留为高特异性验证/敏感性层；专用审计 SQL 为 `project_control/bigquery/113_query_mimic_echo_strict_candidate.sql`。
- 统计分析合同已补齐，见 [`STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md`](STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md)。

## 三阶段

| 阶段 | 交付物 | 当前状态 | 通过条件 |
|---|---|---|---|
| 1. 文献驱动设计 | 15 篇全文卡、知识地图、设计决策 | 完成 | Zotero/Obsidian 同步；taxonomy 校验通过；设计决策有原文证据 |
| 2. MIMIC 开发与论文工件 | v3.3 队列、数据字典、模型、表图、方法与结果证据矩阵 | 进行中 | 全链重跑通过；关键计数一致；无时间泄漏 |
| 3. 本院外部验证 | 原始长表、映射报告、锁模验证、必要时再校准 | 等待数据 | 样例审计通过；变量/单位/时间窗对齐；锁模后再接触结局 |

## 阶段 1 决策

保留：固定 12 h landmark、48 h horizon、校准、AUPRC/competing-risk AUC、
决策曲线、top-risk enrichment 和独立外部验证。旧 elastic-net 二分类主分析降级为历史探索；
当前主线为 Fine-Gray competing-risk model，1 h person-period landmark survival model 作补充。

必须补强：

1. 报告结局的治疗行为依赖性，保留 no-NEE、NEE 0.10、12-48 h、排除
   pre12 shock proxy 等敏感性分析。
2. 报告报警负担、PPV/风险富集和校准，不以 AUROC 单独证明临床价值。
3. 锁模外部验证与再校准、模型更新严格分开。
4. 论文按 TRIPOD+AI 报告，并按 PROBAST+AI 做开发前和终稿偏倚审计。
5. 暂不升级复杂模型；先解决标签质量、动态生理特征和可迁移性。

证据入口：Obsidian `[[CS_AHF 文献知识地图]]`、`[[Literature Index]]`。

## 阶段 2 执行门

1. 恢复并审阅全部上游 SQL。
2. 使用版本化独立 schema，当前为 `study_ahf_v3_2`，禁止覆盖 `study_ahf` 历史表。
3. 初始化独立 run 目录并冻结脚本/config 哈希。
4. 从 MIMIC 原始/官方 derived schema 运行 SQL，导出 v3 CSV。
5. 校验 cohort flow、标签时间、唯一 stay、缺失、异常值和泄漏。
6. 仅在 QC 通过后建模；所有 preprocessing、特征选择、插补、IPCW 权重模型必须在训练折内拟合。
7. 生成 Table 1、模型性能、校准、DCA、敏感性、错误分析和流程图数据。
8. 论文只引用同一个 v3 run 的数字。

## 当前阶段 2 状态

已完成：

- v3.2 index-admission AHF-by-T12 候选队列：5,564 stays，旧定义事件 511。
- v3.3 landmark eligible cohort：5,555 stays；主事件 454；alive ICU discharge competing event 2,935；T60 administrative censoring 2,166。
- 1 h person-period v2：176,525 行，5,555 stays，每 stay 一个终止行，时间 QC 通过。
- early sepsis 亚组：1,498 stays / 151 events；non-sepsis：4,057 stays / 303 events。
- 090 compact 主模型输入：45 个预设预测器；5,555 stays 唯一，标签/person-period 连接完整，黑名单扫描无混入。
- Fine-Gray 主模型 48 h OOF AUC/Brier：`0.7622 / 0.0652`；person-period 补充模型：`0.7681 / 0.0655`。
- 嵌套 predictor-only MICE 可行性：5 折、每折 `m=5` 无 logged event；MICE-only 48 h OOF AUC/Brier `0.7533 / 0.06533`，MICE+缺失指示器 `0.7566 / 0.06490`。最终表型冻结后须以 `m=20` 重跑锁模版。
- Fine-Gray 主模型折间方向初审：37/45 个特征五折同向，top 10% 风险组事件率 24.1%、捕获 29.5% 事件。
- 患者级多域审计：5,549 行且 stay_id 唯一；结局为 `452 event + 2,934 compete + 2,163 censor`。ICU 前可见 definite CXR/CT 为 425/55，`CXR OR CT` 为 449，`CXR AND CT` 为 31；心超检查记录 462 例，但可用结构化 LVEF 为 0。

当前卡点：

- MIMIC 开发端的 Echo 行级时间审计已完成，但窗口内严格 Echo-supported draft 仅 6 例；当前全量数字只能称为 rule-supported operational phenotype，不能称为 echo-confirmed DHF。
- MIMIC 主开发队列的多域 DHF 证据层级尚未最终冻结：HF ICD anchor 不能单独等同 DHF，而严格影像/治疗组合仅 189 例、28 个事件，无法支撑当前 45 个预测器。
- 如论文需要正式一致性，补充一位独立临床标注者对 60 条报告进行盲法复核；现有 60 条为同标注者重复。
- 按最终 DHF 队列的事件数重新冻结低维预测器，并在冻结数据上以 `m=20` 运行折内 MICE、MICE+缺失指示器、中位数和 complete-case 诊断，再完成 early sepsis、IPCW、complete60、phenylephrine、60 min 和 pre-T0 敏感性分析。
- 审阅敏感性结果后冻结论文数字、Table 1、性能表和图形数据。
- 完成 IPCW、complete60、phenylephrine 排除、60 min 持续时间和 pre-T0 AHF 敏感性分析。

## 阶段 3 数据入口

先返回每个数据源 20-50 行脱敏样例和字段字典，不要预先手工计算模型变量。
现有提数清单与映射模板位于
`CS_AHF_hemodynamic_deterioration_ml_project/docs/`。样例通过连接键、时间窗、
单位和记录语义审计后再导出全量。

禁止上传姓名、证件号、手机号、住址等直接标识。开发模型在查看本院结局前
锁定；外部验证先原样应用，再决定是否仅再校准。

## 下一动作

1. 按用户已确认的口径执行院内 `echo-supported DHF ICU cohort`；向导师说明全 ICU 候选宇宙与严格队列的双层报告方式，并保留 radiology-supported/multidomain 作为桥接敏感性层。
2. 如需 inter-rater reliability，补一位临床标注者独立复核 60 条；不报告现有同标注者重复的 kappa。
3. 按最终队列重算事件数、缺失率和有效参数上限，冻结低维 compact manifest；随后在冻结输入上重跑 `m=20` MICE、MICE+缺失指示器、中位数和 complete-case 诊断。
4. 运行主 Fine-Gray、1 h person-period、预设表型/缺失/删失敏感性；仅在条件满足时加入竞争风险机器学习基准。
5. 在用户已登录的 BigQuery 控制台运行 109/110，补齐主窗口 `[T0-24 h,T12)` radiology 覆盖与可见性审计；本执行环境于 2026-09-04 的 `SELECT 1` 仍在 30 秒内连接超时，因此无法代为提交，但这不涉及账号权限或 SQL 语法。随后用输出核查本院心超结果源，先返回 20-50 行脱敏样例和字段字典，执行连接键、单位与时间窗审计。

## 任务报告与持续维护

本目录是本项目正式研究控制面。当前状态统一写入 `RESEARCH_DASHBOARD.md`，历史过程统一写入 `task_reports/`。新增实质任务时不得另建平行的 `inbox/RESEARCH_DASHBOARD.md` 或根目录 `task_reports/`。

每份任务报告至少记录：用户问题与范围、使用文件和版本、已验证事实、判断与影响、新增决策、阻塞项、下一步、本轮修改文件和可重复性信息。报告采用追加式历史记录，不覆盖旧报告。

本轮新增报告和模板见 `task_reports/`。
