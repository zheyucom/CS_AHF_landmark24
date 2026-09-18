# CS_AHF 实时研究总览

更新时间：2026-09-15 Asia/Shanghai

## 论文级工作流（当前执行版）

本项目的每一步都必须留下可复现文件，且能直接对应论文或补充材料。当前主线是：在成人 index ICU 患者中，以 T0 后 12 h 的可用信息，预测随后至 T60 的 ICU 内血流动力学恶化/死亡，并用 Fine–Gray 竞争风险模型、MIMIC 内部验证和本院锁模外部验证评价稳定性。

| 阶段 | 目标与主要动作 | 关键输出 | 通过条件 | 论文位置 | 状态 |
|---|---|---|---|---|---|
| 1 研究问题冻结 | 明确 DHF ICU 场景、T0/T12/T60、主事件和竞争事件 | 研究合同、版本记录 | 研究问题可一句话复述 | Introduction/Methods | 已完成 |
| 2 定义与文献 | 用 Universal Definition/ESC 界定 DHF；预设 A+B+C 多域表型、否定词和替代诊断规则 | `DHF_OPERATIONAL_PHENOTYPE_v20260914.md` | 每个域有来源、时间和排除边界 | Methods/Supplement | 已完成 |
| 3 队列构建 | 男女合并；排除 <18 岁；每患者首次成人 index ICU stay；重建多次 ICU episode | `encounter_icu.csv` | 主键唯一、分母守恒、9204020 排除 | Methods/Fig.1 | 进行中 |
| 4 时间轴与数据清洗 | 依据护理入 ICU 事件、入 ICU 文书、结构化时间代理重建 T0；报告/医嘱时间仅标代理；严格执行 T0/T12 门控 | `encounter_icu.csv`、QC JSON、清洗日志 | 无 T12 后泄露；时间冲突可追溯 | Methods/Supplement | 进行中 |
| 5 DHF 表型冻结 | NLP/规则提取 HF anchor、充血/失代偿、治疗强化、替代诊断；将 45 例语义审计作为校准，不外推人工标签 | `icu_note_evidence.csv`、`diagnostic_evidence.csv`、`treatment_order_proxy.csv`、`dhf_phenotype_screen.csv` | confirmed/probable/not_supported/unknown 规则版本冻结；抽样异常有人工解释 | Methods/Table 1/Supplement | 进行中 |
| 6 预测变量冻结 | 只保留 T0-T12 可用变量；折内插补、标准化和变量选择；资格变量和结局派生变量列入黑名单 | feature manifest、缺失矩阵 | 唯一变量清单、无泄露审计通过 | Methods/Supplement | 已完成第一版 |
| 7 结局与竞争风险 | 从 T12 后实际支持升级/NEE 持续时间、死亡、活着出 ICU、T60 行政删失重建三态结局 | outcome manifest、事件时间表 | 事件/竞争/删失互斥且时间顺序正确 | Methods/Results | MIMIC 已完成；院内待整合 |
| 8 建模 | 预设 Fine–Gray 主模型；1 h person-period 为补充模型 | 锁模脚本、模型对象 | 不按结果临时改变量或阈值 | Methods | 第一版已完成 |
| 9 内部验证 | MIMIC 五折 OOF，报告 AUC、Brier、校准、CIF、bootstrap/折间稳定性 | OOF predictions、Table 2、Fig.2 | 全部预处理在训练折内 | Results/Supplement | 已完成第一版 |
| 10 外部验证 | 锁模后原样运行本院 echo-supported DHF 队列；报告全 ICU 到严格队列的选择性 | external validation dataset、Table 3 | 不改入组/变量/阈值；缺失模式单独报告 | Results | 待表型冻结 |
| 11 敏感性分析 | 影像来源、BNP-only、最近24h、complete-60h、IPCW、60 min 持续时间、phenylephrine 排除 | sensitivity matrix | 方向和解释边界预先规定 | Supplement/Discussion | 待开始 |
| 12 论文工件 | 生成 CONSORT-like flow、队列表、校准图、CIF、亚组图及 Methods/Results 数字 | figures、tables、manuscript draft | 所有数字来自同一冻结 run | 全文 | 待开始 |
| 13 审稿人预审 | TRIPOD+AI、PROBAST+AI、竞争风险和选择偏倚逐项审计 | reviewer audit、risk register | 每个高风险项有处理或限制说明 | Supplement/Response | 待开始 |
| 14 投稿包 | 整理代码、数据字典、数据可用性、AI/NLP 披露、补充材料 | submission package | 可复现、版本一致、引用可核验 | 投稿材料 | 待开始 |

### 这一步的意义与文献依据

当前生成的五张工作表不是新的临床结论，而是论文所需的“证据链中间层”：把原始男女文件统一到 episode 主键，并保留每条文书、检查、检验和医嘱的来源及时间代理。这样才能按 DHF 是综合征而非单一指标的原则组合 A（HF anchor）、B（充血/失代偿）和 C（支持/强化），同时识别否定、替代诊断和多次 ICU 进出，避免把单独 BNP、单张影像、单个医嘱或关键词命中当作金标准。

方法依据包括：Bozkurt et al., *Eur J Heart Fail* 2021（HF 通用定义）；McDonagh et al., *Eur Heart J* 2021（ESC HF 诊断与管理）；Chapman et al., *J Biomed Inform* 2001（NegEx 否定识别）；Irvin et al., *Radiology: AI* 2019（CheXpert 不确定/否定影像标签）；Fine & Gray, *JASA* 1999（竞争风险）；Collins et al., *BMJ* 2024（TRIPOD+AI）；Wolff et al., *Ann Intern Med* 2019（PROBAST）；Riley et al.（预测模型样本量）；Vickers & Elkin, *Med Decis Making* 2006（决策曲线）；Steyerberg（临床预测模型验证）。

### 当前闸门

- 已冻结：成人 index ICU 分母、男女合并、9204020 排除、报告时间/医嘱时间代理的标记方式、MIMIC Fine–Gray 主模型合同。
- 正在完成：院内每个 episode 的 T0/T12/T60 时间轴、多次 ICU 进出识别，以及 A+B+C 全量 DHF 分层。
- 暂不宣称：2,475 例文本异常支持、8,385 例成人分母或 5,549 例 MIMIC 规则支持层均不是最终 DHF 人数。
- 技术人员后续提供正式检查/采样时间后，只做时间敏感性更新，不推翻当前主流程；eMAR 暂缺时以医嘱区间作为明确标注的执行代理。

> 2026-09-04 追加：主窗口原始报告已通过 GCS 导出并下载完整 `7,828/7,828` 行（Parquet 与 CSV 均已做行数、键唯一性和 stay-level 对账）。此前网页本地下载的 `7,558` 行已明确标记为历史不完整尝试，不再用于当前模态/阳性层审计。300 条人工标注来自旧 pre-T0 抽样框，与主窗口按 `(stay_id,note_id)` 仅重合 `145/300`，不能直接估计主窗口 PPV。已从完整主窗口重新生成三层各 100 条的人工标注包，另有 60 条待第二位标注者独立复核。

## 这个文件怎么用

这是本项目的日常主入口。你以后最主要看这个文件：

`project_control/RESEARCH_DASHBOARD.md`

它负责同时回答四个问题：

1. 研究方案全局是什么；
2. 目前已经完成了什么；
3. 当前卡在哪一步；
4. 下一个 7 天需要花多少时间和精力解决什么。

更新规则：

- 每次完成实质研究任务后，更新本文件的状态、关键数字、阻塞问题和下一步计划。
- 每周二 16:00 的自动周报会读取本文件，并反向更新这里的最新周报入口与进展摘要。
- 这里的“实时”指任务完成后和周报时同步更新，不是每条 SQL 或每个模型进程运行中逐秒刷新。
- 旧 `outputs/`、`outputs_v2/` 和旧模型结果只能作为历史/诊断材料，不能作为论文最终结果。

## 一句话状态

研究已经从旧的 “AHF + early sepsis 二分类 logistic” 转向更稳妥的主线：**DHF 操作性表型 ICU 患者 T12 landmark 后至 min(T60, 活着离开 index ICU) 的 ICU 内血流动力学恶化竞争风险预测；Fine-Gray 为主模型，early sepsis 是预设亚组。**

当前处在：**阶段 3：DHF 主表型冻结准备；本院成人 index ICU 分母和 45 例 Gate 3 语义预审核已完成，MIMIC 影像边界行已完成 Codex 草审。** ESC 2026 已将 acute HF 改为 DHF。GCS 完整主窗口 300 条影像仍保留为临床复核/独立标注材料，不能把 Codex 草标当人工金标准。BigQuery 网页控制台已实际运行主窗口 radiology 109/110：5,549 个有效候选有 7,828 份 `[T0-24 h,T12)` 报告，3,886 个 stay 有报告、3,542 个 stay 有 T12 前可见报告，且 `storetime` 无缺失。MIMIC-IV-Echo 已完成真实数据核验：在 `[T0-24 h,T12)` 内只有 61 例有链接 TTE、9 例关联 Echo note 在 T12 前、6 例同时有异常结构化支持。心超缺失主要是检查选择性/数据覆盖问题，不能用“未检查=正常”或数值插补解决。MIMIC 主开发队列须采用多域、时间可追溯的 DHF 操作性表型；心超作为高特异性表型验证/敏感性层。院内外部验证可保留 `echo-supported DHF` 严格队列。乳酸来源审计已完成：`derived.bg` 漏掉 550 个有效的 ICU 0-12 h 原始乳酸记录，主特征已改用 `labevents itemid=50813`，缺失率从旧版 57.44% 降至 47.54%；这不支持把主预测窗改为 24 h。BNP/利尿剂、单独胸片或单独“做过心超”仍不能确诊 DHF。本轮已将院内高级检索拆为“全 ICU 成年分母、心超候选子集、同住院补充证据”三批，平台端只做高召回粗筛，T0/T12 和 DHF 语义判定留在本地。

## 研究方案总纲

当前决策边界：MIMIC 主开发队列使用**多域、时间可追溯的 DHF 操作性表型**：HF anchor + 肺充血/临床失代偿证据 + 治疗/管理强化证据，且不以 BNP、利尿剂、单张胸片或 Echo procedure 单独确诊。心超是最有价值的结构/功能证据，但实际 MIMIC-IV-Echo 覆盖在预设时间窗内过低，不能作为开发端的硬纳入条件；它用于病例级验证和高特异性敏感性层。院内外部验证的严格层仍要求 T12 前 TTE、TEE 或心脏 POCUS 结果可用且支持异常。未做心超或结果缺失不能当作心超阴性，应单独报告检查选择性。胸片与胸部 CT/CTA 是互补的**肺部证据域**：CT 可支持肺水肿、肺间质改变、肺血管充血和胸腔积液判断，也可识别 PE、肺炎、ARDS 等替代或并存解释；但 CT 不能单独确诊 DHF，未做 CT 也不能视为 CT 阴性。主审计使用 `CXR OR CT`，并分别报告 `CXR-only`、`CT-only`、`CXR AND CT`，其中后两者是分层/敏感性分析，不是新的硬性入组条件。

## 胸部 CT 纳入规则（2026-09-05 已明确）

胸部 CT/CTA 应纳入 DHF 相关的肺部证据域，人工复核范围包括：普通胸部 CT、增强胸部 CT、肺动脉 CTA，以及报告中明确描述肺水肿/肺充血/间质性水肿、胸腔积液或相关肺部改变的检查。CTA 还应单独记录 PE；肺炎、ARDS、肺不张等不能简单归为“无 DHF”，而应作为替代或并存解释记录。

这项调整不等于“所有患者必须有 CT”。当前研究采用以下层级：

| 层级 | 作用 | 解释边界 |
|---|---|---|
| `CXR OR CT` | 主肺部证据审计层 | 任一胸部影像有明确肺充血支持；仍需与 HF anchor、临床失代偿和治疗/管理证据结合 |
| `CXR-only` / `CT-only` | 检查来源分层 | 用于评估 modality 选择性和结果稳定性 |
| `CXR AND CT` | 严格影像敏感性层 | 可能严重选择病情更重或检查更多者，不能作为默认主队列 |
| `no CXR/CT` | 未观察到肺部影像证据 | 不能编码为“无肺水肿”或“无 DHF” |

影像人工标注只对胸部报告判读肺充血和替代诊断；下肢静脉超声、头颅/腹部检查、导管操作和其他非胸部报告应标记为非胸部或不确定，不进入肺充血 PPV 分母。最终标签必须使用人工确认后的 `final_report_scope`、`final_modality` 和 `final_congestion_label`，不能直接使用自动关键词命中。

| 模块 | 当前冻结/候选定义 |
|---|---|
| 研究对象 | MIMIC：成人 index ICU stay 中，在 `[T0-24 h,T12)` 具备多域 DHF 操作性表型；院内严格验证：另要求 `echo-supported DHF`；均不要求 T0 时已确诊 |
| 分析单位 | 每位患者 index hospitalization 内首次 ICU stay，每患者一行 |
| Index time | ICU 入科时间 `intime` |
| Landmark | ICU 入科后 12 h，即 T12 |
| 预测变量窗口 | ICU 入科 0-12 h 可获得信息 |
| 预测窗口 | T12 至 T60，或更早的 alive index-ICU discharge |
| 主估计目标 | ICU-level hemodynamic deterioration cumulative incidence |
| 竞争事件 | 活着离开 index ICU |
| 主事件 | 支持水平升级或 NEE 升高持续 >=30 min，或 ICU 内死亡 |
| 主方法 | Fine-Gray competing-risk model |
| 补充路线 | 1 h person-period landmark survival model |
| 敏感性 | BNP-only、PE、最近24 h、双证据/影像表型、IPCW fixed-window、complete-60h、phenylephrine 排除、60 min 持续时间 |
| 外部验证 | 本院 `echo-supported DHF ICU cohort`，锁模后原样验证；另报告全 ICU 候选宇宙到严格队列的选择性，必要时仅再校准 |

## 当前研究合同

必须遵守：

- 不把最终 ICD、资格变量、post-landmark 信息放入预测器。
- 所有 preprocessing、变量选择、插补、权重模型都必须在训练折内完成。
- early sepsis 不再是主队列限制，而是预设亚组。
- 现有 HF ICD、NT-proBNP 和实际 IV loop 仅构成 DHF candidate；本院严格外部验证必须满足 `echo_performed=1 + echo_result_available=1 + echo_abnormal_support=1`，不能把“做过心超”当成异常，也不能因 MIMIC 缺失心超结果而把未检查者判为阴性。完整 5,549 stay 的 radiology-supported/multidomain 仍是“规则支持筛查层”，不能写成全量人工确诊。
- MIMIC-IV-Echo v1.0.1 已真实核验：`echo_study_list` 提供 `study_datetime`、`note_id`、`note_charttime`，可与结构化测量关联。`note_charttime` 仅是报告可用性的代理，而不是独立签署时间；它只能按 `subject_id` 和时间窗关联。实测 `[T0-24 h,T12)` 覆盖为 61/5,549 TTE/TEE study、9 例 note 在 T12 前、6 例异常支持，故不得将其作为 MIMIC 开发端硬门槛或假定未检=阴性。
- 2026-09-03 已在 Codex 侧再次复测：`gcloud` 登录账号与 billing project 正确，但到 `bigquery.googleapis.com:443` 的网络连接超时。该 CLI 阻塞不影响已在浏览器 BigQuery 控制台完成的 Echo 查询和结果表；无需再申请 Echo 数据权限。复测记录见 `project_control/task_reports/TASK_REPORT_2026-09-03_BIGQUERY_CLI_RETEST.md`。
- ICU alive discharge 不能简单当作“48 h 无事件”，主分析按竞争事件处理。
- 论文数字只引用同一冻结 run 中可追溯的结果。

已冻结的建模合同：

- 主文：Fine-Gray competing-risk 作为唯一主模型。
- 补充：1 h person-period landmark survival。
- 事件：ICU 内血流动力学恶化 + ICU 内死亡。
- 竞争：alive index-ICU discharge。
- 资格变量：不进预测器。
- broad v3.3 主模型曾冻结 45 个预设候选特征；旧 650 例 AHF candidate 的 6 参数表仅作历史可行性审计，不能与最终 DHF 模型混写。

## 阶段路线图

| 阶段 | 状态 | 已有/目标交付物 | 通过条件 |
|---|---|---|---|
| 1. 文献驱动设计 | 基本完成 | 研究问题、landmark、结局和报告原则 | 设计有文献和导师反馈支撑 |
| 2. 队列与结局重建 | 基本完成 | v3.2/v3.3 队列、strict label、三态随访、person-period | 关键计数一致，时间 QC 通过 |
| 3. 无泄露预测变量重建 | **进行中** | 最终 DHF 表型、缺失模式审计、变量 manifest、折内插补流程和低维输入 | 先冻结主表型和有效参数数 |
| 4. 主模型与内部验证 | 已完成第一版 | Fine-Gray 与 1 h person-period OOF、AUC/Brier/校准、CIF | 折内预处理，无泄露，指标可复现 |
| 5. 敏感性分析 | 待开始 | IPCW、complete60、phenylephrine、60min、pre-T0 | 方向稳定，解释边界清楚 |
| 6. 论文工件 | 未开始 | Methods/Results/Table 1/图/补充材料 | 所有数字来自冻结 run |
| 7. 本院外部验证 | **字段映射/样例 QC** | 全 ICU 候选宇宙提取、心超三级 QC、样例审计、锁模验证 | 先确认 ICU 时间、心超结果语义、eMAR 和结局字段；不先看本院结局 |

## 已完成成果

- 完成分析单位切换：每位患者 index hospitalization 内首次 ICU stay。
- 完成 v3.2 AHF-by-T12 候选队列重建。
- 完成主结局标签审计，确认短暂用药不是主要瓶颈。
- 完成随访/竞争 ICU 出科审计，确认二分类固定窗口存在重要偏倚风险。
- 完成 v3.3 strict 主标签重写，使用连续 >=30 min 的升级状态。
- 完成 landmark eligibility reconciliation，显式排除 T12 前/时死亡 9 例。
- 完成 1 h person-period v2 构建和 QC。
- 完成 090A-090C：基于 5,555 例 v3.3 eligible stays 建立 45 个预设的 0-12 h 紧凑预测器与 Fine-Gray 输入表；2026-09-04 乳酸改源后已重建。
- 完成 090D：唯一性、白/黑名单、manifest、缺失矩阵和特征×标签×person-period 三表连接 QC 全部通过；乳酸缺失为 `2,641/5,555 (47.54%)`，pH/base excess 为约 46.35%。
- 完成 114A-C 实验室时间窗/来源审计：原始 0-12 h 覆盖为乳酸 52.40%、pH 55.32%、base excess 53.61%，24 h 仅额外增加约 5 个百分点；主时间窗保持 12 h。
- 完成 115 测量机制审计：主事件组乳酸有效测量 67.84%，alive ICU discharge 组为 45.66%；高缺失实验室变量的 MICE + 缺失指示器敏感性升级为必做。
- 完成 094 严格嵌套 MICE 可行性运行：五折外层、每折 `m=5` 的 predictor-only PMM 在训练折拟合，验证折只使用训练供体；无插补 logged event。48 h OOF：MICE-only AUC/Brier `0.7533/0.06533`，MICE+缺失指示器 `0.7566/0.06490`。这是当前 rule-supported v3.3 输入的可行性敏感性，不是最终锁模结果。
- 完成 sepsis 与 non-sepsis 分层计数。
- R 4.6.1、`cmprsk`、`riskRegression` 已可用于竞争风险分析。
- 完成 Fine-Gray 5 折 OOF 内部验证：主模型 48 h competing-risk AUC `0.7622`，Brier `0.0652`；十分位校准平均绝对误差约 `0.0057`。
- 完成 1 h person-period 补充模型及 5 折 OOF 评估：48 h competing-risk AUC `0.7681`，Brier `0.0655`；概率递推误差小于 `1e-14`。
- 缺失指示器敏感性与主 Fine-Gray 结果接近：AUC `0.7605`，Brier `0.0649`。
- 完成第一版稳定性审阅：Fine-Gray 主模型 45 个预测器中 `37/45` 个在 5 折保持同一系数方向，`32/45` 个五折完全同向；主模型 top 10% 风险组事件率 `24.1%`、捕获 `29.5%` 事件。
- 完成 099 AHF 表型审计：当前 5,555 例中严格 pre-T0 AHF 为 `650/66`，最近 24 h 严格敏感性为 `378/34`；发现当前 broad v3.3 队列含 `3,835` 例 acute-HF ICD 但无合规 pre-T0 客观证据，以及 `1,070` 例非急性/其他 HF 锚点。
- 完成 MIMIC 文本可行性核查：当前本机没有 `mimiciv_note`、放射科报告或心超报告表；补装后可用于回顾性影像/文本表型验证，但不能把 discharge summary 当作 T0 前实时诊断时间。
- 完成本机 Note/CXR 源审计：`mimiciv_note` 四张表和可能的 `mimiciv_cxr.cxr` 均为 `not_installed`；未伪造文本覆盖率。
- 完成 Note 数据准备层：安装脚本加入文件可读性、无交互认证和磁盘空间预检；新增 pre-T0 radiology 证据抽取 SQL，但尚未执行真实抽取。
- 完成早期 BigQuery 定向验证输入导出：旧 `650` 个 strict AHF candidate 的文件仅保留作历史复核；当前表型验证统一使用覆盖全部 `5,555` 个 HF anchors 的 106 输入表。
- 完成 104 年龄分层 NT-proBNP rule-in 审计：当前候选中年龄分层 rule-in `484` 例；loop+年龄分层 rule-in `36/1`；loop 或年龄分层 rule-in `594/61`。该审计不修改现有队列或模型。
- 完成 105A legacy AHF candidate 低维输入表：`650` stays、`66` events、`317` alive ICU discharge competing events、`267` administrative censoring；唯一性通过。该 6 参数表只记录历史可行性，DHF 多域表型确定前不可冻结为主模型。
- 核验 ESC 2026：DHF 取代 acute HF；新增 DHF 方案、术语边界和终点分层。主结局仍是 treatment-escalation-based ICU hemodynamic deterioration，而不是临床确诊 CS。
- 完成 106 BigQuery DHF radiology 候选导出：`5,555` HF ICD anchors，`5,556` 行含表头，8 列字段数 QC `bad_rows=0`；106 v2 同时审计 `charttime` 和 `storetime`，新增 107 patient-level 汇总查询和盲法人工标注指南。
- 完成 106/107 云端表与本地 QC：`dhf_radiology_raw_v2`、`dhf_radiology_patient_summary_v1` 已创建并下载；有效候选边界 `5,549/5,555`，原始报告 `4,303`，其中 ICU 前可见 `3,593`。
- 完成旧 pre-T0 300 条报告第一位标注并通过 ID/标签 QC；按用户要求生成 60 条同标注者重复结果，构造性一致率 100%/kappa=1，不能作为独立 inter-rater reliability。规则筛查只能作为经抽样单标注验证的 weak label，不能直接当最终 DHF 诊断。
- 完成 GCS 完整主窗口三层各 100 条的新标注包和保守 AI 草标；当前 300/300 仍为 `pending_human_review`，尚未形成最终临床标签。
- 完成 108 结构化心超审计：5,549 个有效候选中 462 例有 TTE/TEE 检查记录，但结构化 LVEF 可用为 0；因此“做过心超”只能作为检查可用性字段，不能作为心超确证。
- 完成患者级 DHF 多域第一版审计：5,549 行且 stay_id 唯一，结局守恒为 `452 event + 2,934 compete + 2,163 censor`；ICU 前可见 definite CXR 为 425 例、definite chest CT 为 55 例、`CXR OR CT` 为 449 例、`CXR AND CT` 为 31 例。该表是 rule-supported operational phenotype audit，不是人工金标准。
- 完成 MIMIC-IV-Echo BigQuery 真正行级审计并创建 `project-9386bb9f-de39-47eb-886.ahf_work.echo_result_audit_v1`：三表 schema 可读；有效候选 5,549 例中，窗口内链接 TTE/TEE study 61 例、非空结构化结果 61 例、关联 Echo note `charttime<T12` 9 例、draft abnormal-support 41 例、三条件的 strict echo-supported draft 仅 6 例。该结果使“Echo 硬门槛仅用于 MIMIC 高特异性验证层、不能用于主开发队列”的可行性决策有了实证依据。
- 补齐主窗口 radiology 查询 109/110：覆盖 `[T0-24 h,T12)`，将检查发生时间和报告在 `T12` 前可见时间分开；106/107 的 pre-T0 结果仍只用于严格敏感性分析。
- 完成 GCS 完整导出与本地复核：Parquet 共 `7,828` 行、27列，`(stay_id,note_id)` 唯一，3,886 个 stay；完整 CSV SHA256 为 `bf742833fd2ba708fad9e20a0884636a2b02e6b80fbaef61679fcc41f40048e6`。
- 完成 300 条标注与主窗口链接审计：按 `(stay_id,note_id)` 精确链接 `145/300`，未链接 `155/300`；旧标注可保留作规则语义验证，但不能当作 `[T0-24 h,T12)` 主窗口的无偏性能估计。
- 完成本院数据库样例结构审计：确认 7 类导出模型可用于字段映射；进一步确认 ICU 入/出科文书、床旁 ICU 记录以及普通 TTE、TEE、床旁心超、心超专科化评估报告均存在。样例为脑梗死+出院小结+65岁，不能代表目标 ICU-DHF 队列；院内规格升级为 v1.5，继续核实结构化 ICU 时间、心超/检验时间语义、实际 eMAR 和 ICU 结局字段。
- 完成 Gate 1 院内 ICU 主表：男女合并后 8,654 个唯一候选就诊号、8,386 名候选患者；过滤 1 条 17 岁记录后保留 8,653 个成人候选就诊号、8,385 名成人患者，并按每位患者首次成人候选 ICU stay 设定 index。原始候选重复 9 行，所有候选均能连接完整就诊表。
- 完成本院候选专用检查表的心超三态审计：8,385/8,385 成人 index stay 有床旁心超报告行，8,383/8,385 有非空所见或结论；基于预设文本关键词的异常支持仅作 8,266 例 draft flag，不能作为 DHF 金标准。数据库“是否异常”字段未用于替代临床判定。
- 完成心超时间门控重跑与男女混合 50 例样例 QC：`[T0-24 h,T12)` 内床旁心超报告 2,519/8,385，结果可用 2,517/8,385，关键词异常支持 draft 2,475/8,385；女性 886/2,842、男性 1,633/5,543 有窗口内床旁心超。50 例样例均为“心脏超声检查报告单”的床旁/床边项目且结果非空；数据库“是否异常”50/50 为 0，不能作为异常真值。用户已确认检查按报告时间代理处理，时间语义不再作为 Gate 3 阻塞项。
- 完成 Gate 3 字段语义盘点：访问表提供入区/出院时间、离院方式和就诊状态候选；bedside 表存在尿量、纯尿量和吸氧浓度；插管表提供置管/拔管日期；检验表提供报告日期和值。已根据临床确认更新语义：护理明确转入 ICU 事件时间和“入ICU记录”正文时间优先，结构化“入区时间”为代理；`出ICU记录`中的“入院时间”不能直接当作 ICU 入科时间；尿量按约 3–4 小时区间累计处理，吸氧浓度需结合给氧方式解释，气插/气切/吸痰分层。orders 可按开嘱-停嘱、途径、剂量和单位作为用药暴露/eMAR 区间记录，但不含逐次执行时刻和泵速变化，治疗升级主结局仍优先使用实际执行证据。已生成 [`TASK_REPORT_2026-09-12_GATE3_FIELD_SEMANTICS.md`](task_reports/TASK_REPORT_2026-09-12_GATE3_FIELD_SEMANTICS.md) 作为数据管理员语义确认清单。

## 当前可靠关键数字

| 口径 | 数字 |
|---|---:|
| v3.2 AHF-by-T12 候选队列 | 5,564 stays |
| v3.2 旧定义事件 | 511 |
| T12 前/时死亡排除 | 9 |
| v3.3 eligible stays | 5,555 |
| v3.3 主事件 | 454 |
| v3.3 竞争事件 alive ICU discharge | 2,935 |
| v3.3 行政删失 T60 still ICU no event | 2,166 |
| DHF 多域审计有效 stays | 5,549 |
| DHF 多域审计事件/竞争/删失 | 452 / 2,934 / 2,163 |
| person-period 行数 | 176,525 |
| early sepsis eligible stays/events | 1,498 / 151 |
| non-sepsis eligible stays/events | 4,057 / 303 |
| 紧凑主模型候选预测器 | 45 |
| Fine-Gray 48 h OOF AUC / Brier | 0.7622 / 0.0652 |
| Person-period 48 h OOF AUC / Brier | 0.7681 / 0.0655 |
| Fine-Gray 主模型 5 折同向/完全同向特征 | 37/45 / 32/45 |
| Fine-Gray top 10% 风险组事件率/事件捕获 | 24.1% / 29.5% |
| 严格 pre-T0 AHF 审计队列 | 650 / 66 |
| 严格 pre-T0 最近24h敏感性 | 378 / 34 |
| 严格 pre-T0 排除 BNP-only | 146 / 9 |
| 严格 pre-T0 中 NT-proBNP-only | 504 / 57 |
| 严格 pre-T0 中 IV loop-only | 103 / 8 |
| 严格 pre-T0 中 IV loop + NT-proBNP | 43 / 1 |
| 104 年龄分层 NT-proBNP rule-in | 484 / - |
| 104 loop + 年龄分层 rule-in | 36 / 1 |
| 104 loop 或年龄分层 rule-in | 594 / 61 |
| 106 DHF radiology 候选导出 | 5,555 stays / 5,556 CSV rows incl. header |
| 106 有效候选时间边界 | 5,549 stays |
| 院内全 ICU 候选宇宙（男女合并） | 8,386 patients / 8,654 visits |
| 院内成人 index ICU 主表（已排除 9204020，年龄17岁） | 8,385 patients / 8,653 visits |
| 院内床旁心超报告覆盖（成人 index） | 8,385/8,385 stays |
| 院内床旁心超结果可用（非空所见或结论） | 8,383/8,385 stays |
| 院内床旁心超异常支持 draft（待人工复核） | 8,266/8,385 stays |
| 院内窗口 `[T0-24 h,T12)` 床旁心超报告 / 结果可用 / 异常 draft | 2,519 / 2,517 / 2,475 stays |
| 院内窗口床旁心超（女性 / 男性） | 886/2,842 / 1,633/5,543 stays |
| Gate 3 当前可用/待确认 | ICU 时间语义、bedside/插管字段和用药区间语义已按用户确认；45 例语义优先队列已完成保守预审核（8 retain / 37 exclude / 0 unresolved）；执行级 eMAR（如需）及结局编码仍待补提 |
| 106 pre-T0 radiology 原始报告 | 4,303 rows |
| 106 ICU 前可见原始报告 | 3,593 rows |
| 107 patient-level 汇总 | 5,549 rows |
| 109 主窗口 radiology 原始报告（GCS 完整导出） | 7,828 rows；Parquet/CSV 已通过完整性核验 |
| 110 主窗口有任意报告 / T12 前可见报告 | 3,886 / 3,542 stays |
| 110 主窗口规则阳性 / 明确阳性 / T12 前可见阳性 | 2,707 / 2,321 / 2,350 stays |
| 110 主窗口报告 `storetime` 缺失 | 0 / 7,828 |
| 300 条盲法标注包 | 300 reports |
| 300 条标注与 landmark-12 精确链接 | 145/300；155 条不属于新主窗口 |
| 60 条同标注者重复包 | 60 reports；非独立复核 |
| 规则阳性 / 明确阳性 / ICU 前可见明确阳性 | 997 / 877 / 769 patients |
| 规则阳性层人工明确充血 | 78/100 (78.0%, Wilson 95% CI 68.9%-85.0%) |
| 同标注者重复一致率 | 60/60 (100%, 构造性；非独立 kappa) |
| ICU 前可见 definite CXR / chest CT / CXR OR CT / CXR AND CT | 425 / 55 / 449 / 31 stays |
| CXR OR CT + pre-T0 IV loop 或 NT-proBNP 支持 | 189 stays / 28 events |
| ICU 前心超检查记录 / 可用结构化 LVEF | 462 / 0 stays |
| MIMIC-IV-Echo `[T0-24 h,T12)` 链接 TTE/TEE study / 非空结构化结果 | 61 / 61 stays |
| MIMIC-IV-Echo 关联 Echo note 在 T12 前 / draft 异常支持 / strict draft | 9 / 41 / 6 stays |
| Gate 3 50例用户裁决 | 50/50 T0 文书时间明确；G3-043 首段 index 且无 DHF；G3-001 有效危重心超；核实清单 0 |
| ICU 0-12 h 原始乳酸 / pH / base excess 覆盖 | 52.40% / 55.32% / 53.61% |
| ICU 0-24 h 原始乳酸 / pH / base excess 覆盖 | 57.53% / 60.18% / 58.52% |
| 090B 重建后乳酸特征缺失 | 2,641 / 5,555 (47.54%) |
| 主事件 / alive ICU discharge 组的乳酸有效测量 | 67.84% / 45.66% |
| 嵌套 MICE 可行性 OOF AUC / Brier（only） | 0.7533 / 0.06533 |
| 嵌套 MICE 可行性 OOF AUC / Brier（+缺失指示） | 0.7566 / 0.06490 |

## 当前工作台

### 2026-09-14 Gate 3/影像预审核进度更新

- Gate 3 45 例已完成第二轮保守预审核：8 例 `echo_supported_draft` 候选、37 例 `not_supported`、0 例 unresolved。G3-014（感染/肾功能不全主导、心超未支持）和 G3-040（脑出血/肺炎主导、缺乏患者特异性 HF 锚点）已依据完整文书保守排除；模板中的“可能心衰/心功能不全”不计为 HF 锚点。
- 影像 31 条边界行已逐条完成范围/模态/充血/替代解释草案：胸部 20、非胸部 6、混合/不清 5；明确充血 7、可能充血 8、无充血 4、不确定 12。仅 7 条技术范围或混合报告保留为可选人工确认，当前无新增必答病例。
- 新结果与脚本见 `project_control/task_reports/TASK_REPORT_2026-09-14_GATE3_RADIOLOGY_ADJUDICATION_UPDATE.md`、`project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_adjudicated_20260914.csv` 和 `project_control/bigquery/adjudicate_radiology_boundary_20260914.py`。所有标签仍为 draft，未写入最终金标准或模型输入。

已完成：**5,549 stay 患者级规则支持表型、结局和 EPV 第一版审计，以及 MIMIC-IV-Echo 行级链接审计。** 结果为 `452 event + 2,934 compete + 2,163 censor`；ICU 前可见 definite CXR/CT 为 `425/55`，`CXR OR CT` 为 `449`。本次已正式确认：胸部 CT/CTA 与胸片共同构成肺部证据域，CT 既用于肺水肿/充血支持，也用于 PE、肺炎和 ARDS 等替代或并存诊断审计；不要求每例同时有胸片和 CT，也不把单独 CT 阳性当作 DHF 确诊。主窗口 109/110 已通过网页控制台完成，GCS 已补齐全文导出：`7,828` 份报告覆盖 `3,886` 个 stay，`3,542` 个 stay 的报告在 T12 前可见；Parquet/CSV 均已完成完整性核验。300 条旧 pre-T0 标注仅 `145/300` 与主窗口报告精确重合，因此不能直接作为主窗口性能估计。MIMIC Echo 在预设窗口内仅 `61` 例检查、`6` 例高特异 strict draft，因此 MIMIC 主分析不能要求 Echo 硬门槛。院内严格验证仍采用 `echo-supported DHF ICU cohort`，但必须先提取完成、结果可用、异常支持三层字段，不能提前报告人数。

现在真正要做的是：**冻结 MIMIC 主队列证据层级，并按该表型的事件数重新限制预测器；随后重跑锁模版主模型和敏感性分析。本院同步补提执行级 eMAR/治疗升级与 ICU 结局时间字段。** 院内抽取口径已证实成人 index stay 几乎全部带有候选床旁心超报告，但这只验证了抽取选择条件，不能替代 T12 前时间门控、结果临床解释和 DHF 组合判定。当前所有全量影像数字仍称为 `rule-supported operational phenotype`，不能写成全量人工确诊。折内 MICE 已完成 `m=5` 可行性核验；最终冻结后重跑 `m=20`。心超缺失处理方案见 [`MISSING_DATA_AND_ECHO_HANDLING_PLAN_V1.md`](MISSING_DATA_AND_ECHO_HANDLING_PLAN_V1.md)。

统计分析总合同见 [`project_control/STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md`](STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md)。该合同明确：Fine-Gray 是与竞争风险 CIF estimand 对齐的主模型；person-period 是时间结构补充；单因素 P 值、Fisher 检验不做预测变量筛选；elastic net 是预设惩罚回归比较，竞争风险机器学习仅在预设条件满足时作为补充。模型数量不以“越多越好”为目标，所有调参和预处理必须在训练折内完成。

当前用户动作：Gate 3 的 45 例无需重复核对；如需正式影像标注，仅复核 7 条技术范围/混合报告即可。当前唯一实质阻塞是按 [`INTERNAL_DHF_MINIMUM_DATA_REQUEST_v20260914.md`](INTERNAL_DHF_MINIMUM_DATA_REQUEST_v20260914.md) 补提多次 ICU episode、执行级 eMAR/治疗升级和 ICU 结局时间字段，之后才能冻结全量 confirmed/probable/not-supported/unknown 及事件/竞争事件/删失。

院内原始 `DHF_SRR` 已完成只读源审计：25 个 CSV，全部文书 775,853 行（非空正文 775,837 行），并已生成就诊号级高召回文书筛查层（8,653 个成人就诊号，排除 9204020）。该筛查层只用于 NLP/人工排序；由于尚未按 ICU episode 与 T0/T12 门控，不能解释为 DHF 纳入人数。

当前已经连接：

- stay-level v3.3 三态标签；
- 1 h person-period v2；
- ICU 入科 0-12 h 无泄露临床预测变量（45 个，见 manifest）；
- sepsis 亚组标记；
- 106/107 radiology validation candidates、patient-level summary、300/60 盲法标注包；
- 后续敏感性分析所需 censoring/complete60/phenylephrine 标记。

旧 2,424/334 建模 CSV、旧模型 AUROC/AUPRC 和旧报告只能保留作历史基线，相关入口文档仍需清理旧文档标记。

## 2026-09-04 最新执行结果

- GCS 导出的完整主窗口全文已再次通过本地脚本复核：解析后 `7,828` 条报告、`27` 列、`3,886` 个 stay；`(stay_id,note_id)` 唯一，报告正文和 `storetime` 均无缺失，CSV SHA256 为 `bf742833fd2ba708fad9e20a0884636a2b02e6b80fbaef61679fcc41f40048e6`。
- 主窗口 `[T0-24 h,T12)` 中 `6,415/7,828` 条报告在 T12 前可见，`3,352` 条在 ICU 入科前已可见；完整报告的自动模态规则计数为 CXR `1,534`、胸部 CT `315`、其他/未分类 `5,979`。2026-09-04 已将人工标注改为“先确认 `final_report_scope`/`final_modality`，再判肺充血”：胸片和胸部 CT/CTA 都进入可判读胸部影像，非胸部报告从肺充血 PPV 分母排除。这些仍是规则审计，不是人工确诊。
- 患者级完整审计已重跑：有效 HF anchor `5,549`；definite CXR/CT 且 T12 前可见 `625` stays、`78` events；再加 pre-T0 IV loop 或 NT-proBNP 支持 `83` stays、`15` events。严格影像层 EPV 仅 `1.73`，不能运行当前 45 预测器模型。
- 已从完整主窗口重新生成三层各 100 条的盲法标注包，并生成保守 AI 草标副本 `300/300`；当前全部为 `pending_human_review`，草标不进入最终标签。主窗口标注包路径见关键证据入口。
- 已将 `make_dhf_annotation_draft.py` 和 `merge_dhf_annotation_review.py` 的默认目录切换到 `controlled_annotation_20260904_landmark12_complete_v2`，避免新旧时间窗误合并。

## 阻塞问题矩阵

| 问题 | 为什么阻塞 | 下一动作 | 预计主动工时 | 计算/等待 | 风险 |
|---|---|---|---:|---:|---|
| MIMIC 开发表型与院内严格验证口径不完全对称 | MIMIC-IV-Echo 的窗口内严格证据只有 6 例，不能与院内 Echo 硬门槛直接等同 | 冻结 MIMIC 多域主表型，并将 Echo 作为病例级验证/高特异性敏感性；院内报告严格层与桥接层 | 2-4 h | 需临床审阅 Echo 规则 | 高 |
| 独立双标注缺失 | 60 条是同一标注者复制，构造性 kappa=1 | 如需正式可靠性，补一位临床标注者盲法复核并裁决 | 1-3 h | 依赖临床人员 | 中 |
| 院内心超结果语义和全量证据尚未锁定 | 样例已证明 TTE/TEE/床旁心超报告存在，但严格队列仍需区分完成、结果可用和异常支持；procedure flag 不够 | 按 v1.5 规格确认时间/状态字段，做三级 QC 和全量导出 | 2-4 h | 依赖院内数据管理员 | 高 |
| 院内 ICU 时间/结局和 eMAR 语义尚未锁定 | 文本可发现入出 ICU 和用药提及，但不能自动替代结构化 stay、死亡状态或真实执行记录；医嘱时间只是计划时间 | 取得 20-50 例覆盖样例；由院内人员按候选值逐例核对并回填实际时间/状态 | 2-4 h | 依赖院内数据管理员/临床复核 | 高 |
| 旧入口文档仍可能误导 | 2,424/334 和旧 outputs 还在历史边界附近 | 在入口文档和周报中继续标记“历史/诊断材料”，必要时单独清理 | 1-2 h | 低 | 低 |
| 最终模型重建尚未开始 | 不能在 phenotype 冻结前把最终变量表锁死 | 冻结后重建无泄露特征表并跑最终 Fine-Gray / person-period | 4-8 h | 数小时到过夜 | 中 |
| 常规变量缺失处理尚未进入最终锁模管线 | 乳酸/血气等高缺失变量可能有信息性缺失，不能统一填 0；现有 `m=5` 结果尚非最终表型 | 已通过折内 MICE 工程可行性；表型冻结后以 `m=20` 重跑，补齐中位数/complete-case 诊断 | 2-4 h | 数小时 | 中 |

## 下一步 7 天计划

1. 将 300 条旧 pre-T0 标注固定为历史规则验证集，保留 `145/300` 主窗口精确链接审计；明确 60 条同标注者重复不能提供独立 kappa。
2. 新主窗口 300 条报告已完成范围/模态/充血/替代解释预审核；仅 7 条技术范围或混合报告保留为可选临床盲法确认，未确认前继续标记为 draft。
3. 对 61 个 Echo-linked study 分层抽取有 note、异常支持、正常/不确定样例作人工临床复核，不能直接将 regex draft 当作金标准；该项不阻塞当前分母锁定。
4. 冻结 MIMIC 多域 DHF 主表型，并明确 Echo 仅为表型验证/高特异性敏感性；不再等待 Echo 硬门槛来启动主队列。
5. 在严格 Echo 队列可用后，先报告 HFrEF/HFmrEF/HFpEF-compatible 及左/右/双心受累的可评估性和事件数；只在样本支持时做预设交互/分层，不拆分当前主模型，见 `DHF_SUBTYPE_ANALYSIS_PLAN_V1.md`。
6. 按 [`INTERNAL_DHF_MINIMUM_DATA_REQUEST_v20260914.md`](INTERNAL_DHF_MINIMUM_DATA_REQUEST_v20260914.md) 提交院内最小数据补提申请：严格主验证采用 `echo-supported DHF ICU cohort`；同时保留全 ICU 候选宇宙、radiology-supported 和无心超结果审计层，用于评估选择性和可迁移性。
7. 按最终主表型事件数重新冻结低维预测器和 manifest；不得把 broad v3.3 的 45 个预测器直接搬到低事件表型层。
8. 完成主 Fine-Gray、1 h person-period 及预设的 component-specific、strict shock/CS-like、BNP-only、PE、最近24 h、IPCW/complete60 敏感性。
9. 按 [`MISSING_DATA_AND_ECHO_HANDLING_PLAN_V1.md`](MISSING_DATA_AND_ECHO_HANDLING_PLAN_V1.md) 在最终冻结表型上重跑 `m=20` MICE、MICE+缺失指示、中位数和 complete-case 诊断分支；心超不做数值插补。
10. 按 [`2026-09-04_mimic_dhf_phenotype_freeze_recommendation.md`](reports/2026-09-04_mimic_dhf_phenotype_freeze_recommendation.md) 完成 109/110 和临床文本域后冻结 MIMIC 主表型；若严格多域层仍事件过少，则由导师在“低维 DHF 模型”与“HF-anchor ICU cohort 预测”两条预设路线中作出命题选择。

## 需要导师决定

- 本院外部验证按“先全 ICU 候选宇宙与心超字段/样例审计，再锁模原样验证，最后才讨论再校准”的三阶段流程推进。
- 院内主验证队列已按用户确认采用 `echo-supported DHF ICU cohort`：必须有 T12 前实际心超结果支持异常；radiology-supported、multidomain 但无可用异常心超和 `CXR AND CT` 作为桥接/敏感性层。MIMIC 开发队列能否完全采用同一硬门槛，取决于是否取得独立心超结果源。
- 是否允许把旧 `2,424/334` 和旧 `outputs/outputs_v2` 相关入口再单独清理一轮，避免后续写作误用。

## 历史结果边界

以下内容不要写成最终论文结果：

- `2,424/334` 主队列/事件；
- `outputs/`、`outputs_v2/`；
- 旧 logistic/elastic-net 模型性能；
- early sepsis 作为唯一主队列的旧表述；
- 未经过 v3.3 eligible + 无泄露特征表重建的模型结果。

它们可以作为：

- 早期探索；
- pipeline 恢复对照；
- 方法学修正前的诊断材料。

## 关键证据入口

| 内容 | 路径 |
|---|---|
| 当前研究定义草案 | `study_definition/study_definition_v5_pre_t0_dhf_landmark12.md` |
| 历史 AHF 定义草案 | `study_definition/study_definition_v4_pre_t0_ahf_landmark12.md` |
| 特征冻结合同 | `project_control/FEATURE_FREEZE_V33.md` |
| 090 compact 特征/QC run | `project_control/runs/20260828_v3_3_compact_features/` |
| Fine-Gray baseline 脚本 | `analysis_r/090_finegray_baseline_v33.R` |
| 外部验证最小字段 | `project_control/EXTERNAL_VALIDATION_MINIMUM_FIELDS.md` |
| v3.2 index-admission 队列 | `project_control/runs/20260827_v3_2_index_adm/` |
| 主结局审计 | `project_control/runs/20260827_v3_2_outcome_label_audit/` |
| v3.3 person-period reconciled | `project_control/runs/20260827_v3_3_person_period_reconciled/` |
| 最新任务报告 | `project_control/task_reports/TASK_REPORT_2026-09-04_MIMIC_TIME_WINDOW_AND_LAB_FEASIBILITY.md` |
| 时间窗可行性与敏感性方案 | `project_control/TIME_WINDOW_FEASIBILITY_AND_SENSITIVITY_PLAN_V1.md` |
| 缺失数据与心超处理方案 | `project_control/MISSING_DATA_AND_ECHO_HANDLING_PLAN_V1.md` |
| 测量机制审计结果 | `project_control/runs/20260904_lab_measurement_outcome_audit/reports/115_measurement_availability_by_final_state.csv` |
| 周报目录 | `project_control/reports/weekly/` |
| MIMIC 文本/影像可行性方案 | `project_control/reports/2026-08-28_mimic_text_ahf_extraction_plan.md` |
| Note/CXR 数据源审计 SQL | `sql_v3_2/audits/100_audit_note_source_availability.sql` |
| Note 下载与安装说明 | `project_control/MIMIC_NOTE_DOWNLOAD_AND_INSTALL.md` |
| pre-T0 放射科证据抽取 SQL | `sql_v3_2/audits/101_create_pre_t0_radiology_ahf_evidence.sql` |
| BigQuery 下载/查询路径 | `project_control/bigquery/README.md` |
| BigQuery pre-T0 radiology 查询 | `project_control/bigquery/103_query_pre_t0_radiology.sql` |
| BigQuery DHF radiology 查询 | `project_control/bigquery/106_query_pre_t0_dhf_radiology.sql` |
| BigQuery DHF patient-level 汇总 | `project_control/bigquery/107_query_dhf_radiology_patient_summary.sql` |
| BigQuery DHF 主窗口 radiology | `project_control/bigquery/109_query_landmark12_dhf_radiology.sql`、`110_query_landmark12_dhf_radiology_patient_summary.sql` |
| BigQuery 心超结果审计模板 | `project_control/bigquery/112_echo_result_audit_template.sql` |
| BigQuery MIMIC-IV-Echo 结构化结果审计 | `project_control/bigquery/113_query_mimic_echo_strict_candidate.sql` |
| DHF NLP/时序验证协议 | `project_control/reports/2026-08-29_dhf_phenotyping_nlp_and_time_series_protocol.md` |
| DHF 两阶段 NLP 优化方案 | `project_control/reports/2026-09-05_DHF_NLP_TWO_STAGE_REFINEMENT.md` |
| DHF radiology 人工标注指南 | `project_control/templates/DHF_RADIOLOGY_ANNOTATION_GUIDE.md` |
| 300 条标注与 landmark-12 链接审计 | `project_control/bigquery/landmark12_audit_20260904/DHF_ANNOTATION_LANDMARK12_LINKAGE_2026-09-04.md` |
| DHF 影像中文快速指南 | `project_control/templates/DHF_RADIOLOGY_ANNOTATION_QUICKSTART_ZH.md` |
| DHF 主窗口 round1 抽样包 | `project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1.csv` |
| DHF 标注回写与 QC 脚本 | `project_control/bigquery/merge_dhf_annotation_review.py` |
| 已完成标注处理与验证报告 | `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260902/` |
| 患者级多域表型/结局/EPV审计脚本 | `project_control/bigquery/build_dhf_multidomain_audit.py` |
| 患者级多域审计报告 | `project_control/bigquery/controlled_annotation_20260830_v2/processed_20260903/DHF_MULTIDOMAIN_AUDIT_2026-09-03.md` |
| 影像范围/心超/备注说明任务报告 | `project_control/task_reports/TASK_REPORT_2026-09-02_ANNOTATION_SCOPE.md` |
| 本院数据提取完整规格 | `project_control/INTERNAL_HOSPITAL_EXTRACTION_SPEC_DHF_EXTERNAL_VALIDATION_V1.md` |
| 本院高级检索执行方案 | `project_control/INTERNAL_HOSPITAL_ADVANCED_SEARCH_STRATEGY_DHF_V1.md` |
| 本院平台字段勾选清单 | `project_control/INTERNAL_HOSPITAL_PLATFORM_FIELD_EXPORT_CHECKLIST_DHF_V1.md` |
| 本院样例证据与字段 QC 报告 | `project_control/task_reports/TASK_REPORT_2026-09-04_INTERNAL_SAMPLE_EVIDENCE_AND_QC.md` |
| 本院数据提取简版申请 | `project_control/INTERNAL_HOSPITAL_DATA_REQUEST_BRIEF_DHF_V1.md` |
| 本院 DHF 最小数据补提请求（当前执行入口） | `project_control/INTERNAL_DHF_MINIMUM_DATA_REQUEST_v20260914.md` |
| 本院原始源数据库存审计 | `project_control/internal_dhf_source_inventory_20260914.json` |
| 本院文书高召回筛查层 | `project_control/internal_dhf_document_recall_screen_20260914.csv` |
| 本院字段映射模板 | `project_control/INTERNAL_HOSPITAL_FIELD_MAPPING_TEMPLATE.csv` |
| BigQuery 结果导入与盲法抽样脚本 | `project_control/bigquery/prepare_dhf_radiology_annotation.py` |
| ESC 2026 DHF 影响评估 | `project_control/reports/2026-08-29_ESC2026_DHF_implications_and_protocol_update.md` |
| AHF 设计与文献依据 | `project_control/reports/2026-08-29_ahf_design_decisions_and_literature_basis.md` |
| legacy strict AHF 低维候选清单 | `project_control/FEATURE_FREEZE_AHF_STRICT_CANDIDATE_V1.md` |
| strict AHF 低维候选 SQL | `sql_v3_2/modeling/105A_create_strict_ahf_lowdim_candidate_v1.sql` |

## 最新周报

- `project_control/reports/weekly/2026-09-01_weekly_report.md`（2026-09-03 补充更新）

## 更新日志

- 2026-09-05：正式将胸部 CT/CTA 纳入 DHF 肺部证据域；主规则为 `CXR OR CT`，并分层报告 `CXR-only`、`CT-only`、`CXR AND CT`。明确 CT 可支持肺水肿/充血和替代或并存诊断审计，但不能单独确诊 DHF，未做 CT 不能视为阴性；同步补入 300 条主窗口人工复核清单。
- 2026-09-08：完成本院高级检索方案 v1.0。将平台检索拆分为全体成年 ICU 候选宇宙、心超候选子集和同住院补充证据三批；明确“入 ICU/出 ICU”使用 OR、`B超检查报告单` 不能整体视为心超、初筛保留全 ICU 分母，并将 T0/T12、报告语义、心超异常和 DHF 组合判定留给本地二次筛选。
- 2026-09-08：完成本院检索平台字段勾选清单。明确核心导出为连接键/ICU 时间、心超与胸部影像全文、临床文书、目标检验、医嘱与实际 eMAR、体征/出入量/呼吸支持和 ICU 结局；费用、国籍民族、饮食与护理行政字段不进入首轮导出。
- 2026-09-05：形成两阶段 NLP 优化方案：结构化数据广筛，时间门控的症状/体征/医生评估/替代解释上下文抽取精筛；先建立规则和人工金标准，再比较 ClinicalBERT/BioClinicalBERT 或受约束 LLM，不直接把自由文本二分类结果作为 DHF 金标准或主模型预测器。
- 2026-08-27：建立实时研究总览；明确主入口、v3.3 当前状态、阻塞问题、预计投入和周报机制。
- 2026-08-27：冻结特征边界与外部验证最小字段清单，明确主模型只用紧凑预设特征集。
- 2026-09-01：完成 DHF 影像标注人工交接文件；确认当前阻塞是临床标注与裁决，而不是 BigQuery 权限或查询执行。
- 2026-08-27：090 compact feature pipeline 通过 5,555 stay 的唯一性、黑名单、manifest、缺失和三表连接 QC；Fine-Gray 5 折 baseline 已进入执行。
- 2026-08-27：091 Fine-Gray OOF 评估和 092/093 person-period 补充模型及评估完成，结果已落盘；主模型仍按预设 Fine-Gray 解释。
- 2026-08-27：完成第一版折间方向、校准和 top-risk 富集审阅；结果支持继续做敏感性分析，但暂不作为最终论文结论。
- 2026-08-28：完成 MIMIC-IV-Note/CXR 补装准备，明确 radiology 仅用于 pre-T0 表型验证，discharge summary 不作为实时诊断时间或预测器。
- 2026-08-28：修正 BigQuery 核心数据集命名导致的误判；先用版本化数据集重测权限，同时保留只读 Note 的 radiology 验证路径。
- 2026-08-28：修正 BigQuery 核心数据集名称，统一使用 `physionet-data.mimiciv_3_1_hosp` / `physionet-data.mimiciv_3_1_icu`；本地 PostgreSQL SQL 中的 `mimiciv_hosp` / `mimiciv_icu` 不作 BigQuery 名称使用。
- 2026-08-29：完成 104 年龄分层 NT-proBNP rule-in 审计；确认 650/66 应称 pragmatic strict operational AHF 候选，NT-proBNP>=300 仅为支持证据；新增 AHF 设计与文献依据报告，明确低维建模和敏感性分析边界。
- 2026-08-29：完成 105A legacy strict AHF candidate 低维输入表及 QC：650 stays、66 events、317 competing events、267 censoring，650/650 唯一；其 6 参数仅作历史可行性记录，待 DHF 多域表型确定后重新冻结最终模型。
- 2026-08-29：核验 ESC 2026 将 acute HF 改为 DHF；新增 v5 DHF 研究定义和完整影响评估。106 已导出 5,555 个 HF anchors 供 BigQuery pre-T0 radiology 多域验证；旧 650/66 只保留为 legacy DHF candidate。
- 2026-08-29：完成 DHF 文本/时序验证协议。106 v2 加入 report availability 时间审计，107 输出 patient-level 筛查汇总；建立盲法人工标注指南，明确规则筛查不替代临床表型验证。
- 2026-08-29：补齐 BigQuery 106 结果的本地导入 QC 与盲法标注包生成脚本；自动复核 pre-T0 `charttime`、`storetime` 可用性和三层抽样，但不读取结局或预测器。
- 2026-09-02：完成本院外部验证原始数据提取规格与字段映射模板；明确先提连续成年 ICU 原始候选宇宙、再按 MIMIC 冻结的 DHF 多域规则筛选，外部结局数据应与字段映射阶段隔离。
- 2026-08-29：发现 gcloud 已安装并登录 `zheyu.sy@gmail.com`，默认项目为 `project-9386bb9f-de39-47eb-886`；用户已完成候选 CSV/工作数据集准备，当前等待 106/107 查询结果；Codex 执行环境访问 Google API 超时，README 已补充本机 Terminal 命令。
- 2026-08-30：通过已登录 BigQuery 控制台成功执行修正版 106/107，发现并排除 6 个 `admittime > intime` 异常边界，保留 5,549 个有效候选；下载 4,303 条原始报告、5,549 行患者级汇总和 300 条分层抽样，完成时间/唯一性 QC 及盲法标注包。
- 2026-09-01：将 106/107 的有效候选、报告覆盖、可见性和 300/60 标注包同步到总览；继续将旧 `2,424/334` 与旧 `outputs/` 视为历史/诊断材料，并标记需清理旧文档。
- 2026-09-01：补齐 `STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md`，明确 Fine-Gray、person-period、竞争风险/Logistic/惩罚回归/机器学习的分工、折内调参、性能评价和禁止的单因素筛选；并核验关键 DOI。
- 2026-09-01：补充中英对照影像标注指南和中文快速开始；明确 Codex 可做 AI-assisted 草标，但最终临床表型仍需临床复核/裁决，且“未提及肺充血”不默认标为明确阴性。
- 2026-09-02：完成 300 条工作簿标注导入与 QC；按用户指示将 60 条复核定义为同标注者重复，构造性一致率 100%/kappa=1，不作为独立 inter-rater reliability。
- 2026-09-02：完成 5,549 stay 患者级规则支持表型、结局和 EPV 审计：candidate 650/66，ICU 前可见 definite radiology 580/72，radiology+IV loop 20/5；当前 45 预测器下各层 EPV 均不足以支持直接建模。
- 2026-09-03：完成 108 结构化心超审计和多域患者级审计；462 例有心超检查记录但结构化 LVEF 可用为 0，ICU 前可见 definite CXR/CT 为 425/55，CXR OR CT 为 449，CXR AND CT 为 31；主口径明确为 T12 前 DHF operational phenotype，不要求 T0 已确诊。
- 2026-09-03：形成心超必要性决策记录：异常心超是严格 `echo-supported DHF` 主队列的必要证据；提数阶段保留全 ICU 候选宇宙以审计心超选择性。主影像规则为 CXR OR CT，CXR AND CT 仅作敏感性分析。
- 2026-09-03：将方案升级为 v5.6：最终模型冻结前必须取得并时间审计心超结果；单独 CXR/CT、BNP 或利尿剂均不足以确诊 DHF。Codex 环境执行心超元数据盘点时未返回可用表清单，需在用户已登录的 Terminal 运行 `111_discover_echo_sources.sh`；这不涉及用户权限、SQL 或临床数据读取。
- 2026-09-03：根据用户确认更新院内提数口径 v1.2、严格研究定义 v5.7：最终严格队列必须是 ICU 患者，并具备 T12 前实际完成心超、结果可用和异常支持三级证据，同时满足 DHF 失代偿与治疗强化证据；不要求 T0 时已完成 DHF 诊断。提数阶段仍保留全部 ICU 候选者，专门评估心超选择性；此前 462/0 仅为 MIMIC 结构化结果可用性审计，不能外推为院内数字。
- 2026-09-04：完成“我院数据库”样例结构审计和 ICU/文本/心超专项复核。确认样例含入/出 ICU 文书、ICU 床旁记录以及普通 TTE、TEE、床旁心超、心超专科化评估报告；文本可作为 ICU 时间和临床表型抽取来源，但不能未经验证替代结构化 ICU stay、真实 eMAR 或 ICU 死亡/出科状态。院内规格升级为 v1.4，正式提数前继续完成时间语义确认和 20-50 例 QC。
- 2026-09-04：完成“我院数据库”样例结构审计和 ICU/文本/心超专项复核。确认样例含入/出 ICU 文书、ICU 床旁记录以及普通 TTE、TEE、床旁心超、心超专科化评估报告；文本可作为 ICU 时间和临床表型抽取来源，但不能未经验证替代结构化 ICU stay、真实 eMAR 或 ICU 死亡/出科状态。院内规格升级为 v1.5，新增字段语义确认清单，补充检验采样时间、报告时间和床旁空行风险；正式提数前继续完成时间语义确认和 20-50 例 QC。
- 2026-09-03：进一步冻结严格队列：ICU 身份、T12 前实际心超完成、结果可用、异常支持均为必要条件；补充 HFpEF 不能仅由 LVEF >=50% 排除，必须保留舒张功能/充盈压、左房、左室肥厚、右心、肺动脉压和瓣膜结果。T0 仍不是强制诊断时间点，证据可在 ICU 早期至 T12 前完成。
- 2026-09-03：根据 PhysioNet 官方 MIMIC-IV-Echo v1.0.1 页面定位 `physionet-data.mimiciv_echo` 及结构化字段；新增 111 定向 schema 盘点和 113 T12 Echo 结果审计 SQL。当前 Codex 环境 `gcloud` 认证可见，但 `bq ls` 仍在 Google API 阶段无返回，未伪造 Echo 计数。
- 2026-09-03：用户开通 MIMIC-IV-Echo 后，通过已登录 BigQuery 控制台完成 schema 和真实行级审计并创建 `echo_result_audit_v1`：5,549 个有效候选中仅 61 个窗口内链接 TTE/TEE、9 个关联 note 在 T12 前、41 个 draft 异常支持、6 个 strict draft。由此将 MIMIC Echo 从主队列硬门槛调整为高特异性验证/敏感性层；院内严格 `echo-supported` 队列保留，并需与 MIMIC 多域表型桥接报告。
- 2026-09-04：完成 114A-C 实验室时间窗和来源审计。原始乳酸在 ICU 0-12 h 覆盖为 52.40%，`derived.bg` 仅 42.50%，差异来自 550 个仅原始表有记录的 stay；090B 乳酸改为原始 `labevents itemid=50813` 并成功重建 090B-090D。24 h 对三项关键检验仅增加约 5 个百分点，故 `[T0,T12)` 保留为主预测窗，`[T0,T24)->[T24,T72)` 仅作为预设敏感性。
- 2026-09-04：完成 115 三态测量机制审计。主事件组乳酸/pH/base excess 的有效测量率均高于 alive ICU discharge 组，支持将折内 MICE + 缺失指示器固定为最终模型的必做敏感性，而不把高缺失简单填为正常或只作中位数插补。
- 2026-09-04：完成 094 五折嵌套 predictor-only MICE 可行性运行（每折 `m=5`、`maxit=5`）。MICE-only 与 MICE+缺失指示器的 48 h OOF AUC/Brier 分别为 `0.7533/0.06533` 和 `0.7566/0.06490`；无 MICE logged event。该运行证明流程可用，但等待最终 DHF 表型冻结后以 `m=20` 重跑锁模版。
- 2026-09-04：通过 GCS 完整导出主窗口 radiology 全文 `7,828/7,828`，完成 Parquet/CSV 行数、键唯一性、stay-level 对账和 SHA256 留档；补做 300 条旧 pre-T0 标注与新 landmark-12 报告精确链接，结果 `145/300`，明确两种时间窗不能合并估计主窗口标注性能。
- 2026-09-12：完成院内男女合并 ICU 主表和成人/index QC：8,654 个唯一候选就诊号、8,386 名候选患者；排除 1 条 17 岁记录后为 8,653 个成人候选就诊号、8,385 名成人患者；原始候选重复 9 行，所有候选均可连接完整就诊表。
- 2026-09-12：完成院内候选专用检查表心超三态审计：成人 index stay 中床旁心超报告覆盖 8,385/8,385，结果非空 8,383/8,385；8,266 例仅达到关键词异常支持 draft，必须人工复核，不能把“做过床旁心超”或“是否异常”字段直接写成 DHF 确诊。
- 2026-09-12：完成心超时间门控重跑和男女混合 50 例样例 QC。窗口内床旁心超为 2,519/8,385，结果可用 2,517/8,385，关键词异常支持 draft 为 2,475/8,385。样例显示“是否异常”字段与报告正文不一致且审核日期只有日期粒度；后续严格外部验证必须确认检查/结果可见时间语义并进行人工异常判定。
- 2026-09-12：完成 Gate 3 字段语义盘点并回填临床确认。T0 优先使用护理明确转入 ICU 事件时间，其次为“入ICU记录”正文时间，结构化“入区时间”作为代理；`出ICU记录`中的“入院时间”不能直接当作 ICU 入科时间。bedside 尿量按约 3–4 小时累计区间处理，吸氧浓度需结合给氧方式解释，插管/气切/吸痰分层。orders 可按开嘱-停嘱、途径、剂量和单位作为用药暴露/eMAR 区间记录，但不含逐次执行时刻和泵速变化；治疗升级主结局仍需实际执行证据或预设医嘱区间敏感性定义。已形成最小确认清单。
- 2026-09-13：根据用户反馈，前述字段语义不再列为待确认事项；已生成 50 例人工核对表 [`internal_gate3_manual_review_50_20260913.csv`](internal_validation/20260912/internal_gate3_manual_review_50_20260913.csv) 及填写说明，并生成全量三层底表 [`internal_dhf_three_tier_audit_20260913.csv`](internal_validation/20260912/internal_dhf_three_tier_audit_20260913.csv)。成人 index ICU 分母 8,385；报告时间窗口内床旁心超 2,519，结果可用 2,517，异常支持规则草稿 2,475。上述 2,475 仍是 draft，不能替代人工 DHF 结局标签；当前导出尚不能可靠计算 event/competing/censor，已在审计 JSON 中标记为 unavailable。
- 2026-09-13：用户确认排除 17 岁患者 `9204020`，成人 index ICU 分母锁定为 8,385（女 2,842、男 5,543）。G3-043 按首段 ICU index 且无 DHF 排除，G3-001 保留有效危重心超；G3-005/G3-015/G3-029/G3-050 均改为文书支持的明确 ICU 时间。50 例人工裁决已叠加到全量三级表，另生成 45 例 DHF 语义优先队列；当前不再重复询问已解决的 T0/episode 事实。
- 2026-09-14（续）：修复 Gate 3 可重复裁决脚本，将 G3-014（感染/肾功能不全主导、心超未支持）和 G3-040（脑出血/肺炎主导、无患者特异性 HF 锚点）纳入 `not_supported`；45 例结果现与脚本一致，为 8 retain / 37 exclude / 0 unresolved。新增院内 8,385 人三级表型审计 [`internal_dhf_three_tier_audit_20260914.csv`](internal_validation/20260912/internal_dhf_three_tier_audit_20260914.csv) 及 QC/任务报告；报告时间窗口内床旁心超完成/结果可用/关键词异常 draft 为 2,519/2,517/2,475，DHF 综合人工标签和事件/竞争事件/删失仍待完整文书、执行级 eMAR 与 ICU 转归时间后冻结。
- 2026-09-14：完成45例语义优先队列保守预审核：8例保留候选、37例保守排除、0例未决；输出 `internal_gate3_semantic_evidence_20260914_adjudicated.csv`。完成300条 MIMIC 影像 scope/模态/充血/替代解释预审核：胸部223、非胸部63、混合/不清14；明确充血97、可能充血8、无充血25、不确定170；31条边界行已有逐条草案，仅7条技术范围或混合报告保留为可选临床确认。新增 `DHF_OPERATIONAL_PHENOTYPE_v20260914.md`，冻结 A/B/C 多域定义、MIMIC与院内口径、人工裁决门槛及 TRIPOD/PROBAST/Fine–Gray 等文献依据；最终DHF队列仍需全量证据与结局数据后冻结。
