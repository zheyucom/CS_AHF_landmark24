# MIMIC 实验室主线修复、历史 SQL 隔离与发表复现质量门设计

日期：2026-09-19  
状态：用户已批准；阶段 A 已于 2026-09-19 实施，阶段 B/C 待后续门控

## 1. 决策

采用“当前主线修复 + 历史代码不可变隔离 + 发文前全仓复现审计”。

历史 SQL 不在原文件上重写，因为旧结果必须继续对应当时实际运行的代码。历史代码中发现的错误不会被忽略：它们进入机器可读的问题登记和扫描报告；任何最终流水线若引用历史文件、历史表或旧结果，必须 fail-closed。

最终论文只允许引用同一个冻结 run 产生的队列、特征、结局、表图和性能数字。

## 2. 已确认的问题

当前项目至少存在以下同类风险：

1. `sql_v3_2/modeling/090B_create_compact_predictors_v33.sql` 的 raw 乳酸只按 `charttime` 门控，尚未核对 `storetime`、fluid、category、unit、specimen 和重复。
2. 同一主模型中的 pH、base excess、BUN、肌酐、电解质、血常规及 INR 仍直接来自 derived 表，不能证明结果在 T12 前已经可用。
3. NT-proBNP 队列 SQL 使用 raw `labevents`，但只按 `charttime` 筛选，尚未完成单位、可用时间和重复门控。
4. 多个历史 `070E` 文件用 `CASE ... ELSE NULL` 静默丢弃范围外值，没有保留原值、异常标志和排除原因。
5. 同类逻辑分散在 `sql_v3`、`sql_v3_1`、`sql_v3_2`、`sql_v4`、`sql_v4_2` 和 recovered 文件中，仅凭目录名无法阻止误执行。

## 3. 权威状态模型

新增项目级代码权威清单：

`project_control/PIPELINE_AUTHORITY_MANIFEST.csv`

每个受版本控制的 SQL 必须且只能登记一次。

阶段 A 先覆盖全部 SQL；阶段 C 前清单必须扩展到所有会影响结果的 Python、R、Shell、配置、锁文件和 notebook 执行入口。未登记的可执行工件不得进入发表 run。

字段固定为：

- `path`
- `artifact_kind`：cohort / phenotype / outcome / feature / audit / export / modeling / tool / report / config
- `authority_status`
- `analysis_role`：main / sensitivity / audit / historical
- `engine`：postgres / bigquery / python / r / shell / notebook / config
- `replacement_path`
- `allow_final_run`
- `rationale`
- `reviewed_on`

`authority_status` 只能是：

- `ACTIVE`：可进入正式主分析或预设敏感性分析。
- `AUDIT_ONLY`：只可产生质量控制结果，不可直接生成正式特征、队列或结局。
- `LEGACY_BLOCKED`：保留历史证据，正式运行器拒绝执行。
- `SUPERSEDED`：已有明确替代文件；旧文件禁止执行。

初始分类原则：

- `sql_v3_2` 是当前主线候选，但必须完成依赖审计后才可逐文件标为 `ACTIVE`。
- `sql_v4_2` 只可能作为 pre-T0 等预设敏感性分析；未通过同一质量门前不得进入最终 run。
- `sql_v3`、`sql_v3_1`、`sql_v4`、`recovered_original` 及旧输出链默认 `LEGACY_BLOCKED`。
- `project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql` 为 `AUDIT_ONLY`。
- 不能通过“整个目录一刀切”代替逐文件登记。

运行时另行记录每个实际执行文件的 SHA-256；静态清单不硬编码会随正常修订变化的哈希。

## 4. 正式运行前置门

新增提交到仓库的前置校验器，并接入现有 `project_control/start_run.py` 或正式运行入口。前置门必须：

1. 扫描 Git 跟踪的全部 SQL，未登记文件直接失败。
2. 拒绝 `allow_final_run=false` 的文件进入执行计划。
3. 拒绝 ACTIVE 文件读取仅由 LEGACY_BLOCKED/SUPERSEDED 文件生成的表。
4. 拒绝当前主线引用旧 schema、旧导出目录或历史模型结果。
5. 要求正式 run 在干净 Git 工作树和固定 commit 上启动。
6. 保存 Git HEAD、SQL 哈希、输入快照指纹、执行顺序、数据库引擎和退出码。
7. 数据库不可用或依赖图不完整时标记 `not_run`，不能把静态检查写成数据运行成功。

最终执行计划只能由权威清单生成，不能接受任意路径参数绕过清单。

## 5. 统一 raw 实验室数据层

当前主线不再让 cohort、phenotype、outcome 和 predictor SQL 各自直接读取实验室表。新建一个版本化的 raw 实验室合同层，逻辑上分为四层：

1. `lab_contract`：概念、itemid、fluid、category、unit、MIMIC release、用途及规则版本。
2. `lab_event_classified`：保留原始行并计算语义、单位、时间、重复和 episode 状态。
3. `lab_quarantine` / `lab_eligible`：按显式 reason code 分流，不能静默删除。
4. `lab_feature_rollup`：只从 eligible 行按预先登记的 first/last/min/max/delta 规则生成正式特征。

至少保留：

- `labevent_id`、`specimen_id`、`subject_id`、`hadm_id`、`stay_id`
- `itemid`、label、fluid、category
- `charttime`、`storetime`、`availability_time`
- raw `value`、`valuenum`、`valueuom`
- 参考区间、flag、priority、comments
- `censor_type`、上下界
- `rule_id`、`rule_version`
- `quarantine_reason`、`implausible_value_flag`

项目仓库只保存规则、SQL、测试和聚合 QC；患者级表留在授权数据库中，不提交 Git。

## 6. 语义与时间规则

### 6.1 正式语义合同

正式实验室纳入必须同时满足：

- 精确 itemid allowlist；
- 精确 fluid；
- 精确 category；
- 已批准 unit；
- 对应 MIMIC release 的字典合同匹配。

名称正则只允许用于 `d_labitems` 候选发现，不能直接纳入患者行。新 itemid 或单位默认为 quarantine，并进入 `proposed` 规则生命周期。

BUN 必须仅接受血液 BUN 合同；尿液、腹水、胸水、脑脊液、关节液、粪便及其他体液继续按具体 reason code 隔离。

### 6.2 角色特异的时间合同

- predictor、T12 风险集和 T12 前表型证据：  
  `availability_time = GREATEST(charttime, COALESCE(storetime, charttime)) < T12`。
- pre-T0 敏感性：`availability_time < T0`，并满足预先登记的窗口下界。
- post-T12 outcome confirmation：`charttime` 必须位于结局窗口，且结果必须在预设观察截止时间前可用；具体截止时间随 outcome contract 固定。
- `storetime < charttime`、缺失关键时间、跨 episode 多重匹配均进入 quarantine。
- derived 表缺少充分可用时间字段时，只能用于覆盖对账或 AUDIT_ONLY，不得回填正式特征、资格或结局确认。

### 6.3 重复、删失和异常值

- `specimen_id × itemid` 重复在聚合前隔离；没有明确来源依据时不得任意挑一条。
- `>x`、`<x` 和区间结果保存原值、边界与 censor type，不改写成精确值。
- 范围外值先保留原值并设置 `implausible_value_flag`；只有预先批准的物理不可能范围才能令分析值缺失，且必须输出排除原因和计数。
- 统计离群但临床可能真实的值不自动删除或 Winsorize。
- 单位转换只允许确定性、来源明确、版本化的映射；同时保留原单位、原值、转换因子和规范化值。
- 缺失不能补零。

## 7. raw 与 derived 的关系

raw 是正式实验室事实源；derived 只承担：

- raw-only / derived-only / both 覆盖审计；
- 官方概念逻辑对照；
- 预设敏感性分析。

禁止：

- derived-only 记录绕过 raw 的 `storetime/T12` 门控；
- 用 derived 覆盖 raw 原值；
- 将 derived 覆盖不足解释为真实未测；
- 在未保存差异报告时混用 raw 与 derived。

覆盖键必须按概念预先规定，例如 BUN 使用 `stay_id + specimen_id`，乳酸在 derived 不暴露 specimen 时使用已登记的替代键并说明限制。

## 8. 项目扫描器与 Skill 的关系

项目内新增受 Git 管理的质量门目录，作为论文复现的权威实现：

`project_control/quality_gates/mimic_lab/`

包含：

- 规则包；
- SQL 扫描器；
- 权威清单校验器；
- 合成失败夹具；
- 扫描结果 schema；
- 运行说明。

本机 `mimic-iv-data-cleaning` Skill 是可复用镜像，不是论文事实源。通用规则只有在完成来源核验、失败夹具、回归验证和用户批准后，才从项目规则包同步到 Skill。正式 run 记录项目规则包和所调用 Skill 的版本/哈希，防止两者静默漂移。

规则生命周期保持：

`proposed → sourced → fixture_added → regression_tested → active → deprecated`

Codex 可以自动提出和验证规则，但不能在无来源、无测试或无批准时提升为 active。

## 9. 扫描规则

ACTIVE SQL 出现以下情况必须报错：

- labevents 使用名称/元数据模糊匹配纳入特征；
- raw 实验室缺少 availability-time 门控；
- 缺少 unit、fluid、category 或 specimen 合同；
- 使用已知错误体液 itemid；
- derived 实验室直接生成主特征、入组资格或正式结局确认；
- `COALESCE(value/valuenum, 0)`；
- 范围外值静默 `ELSE NULL` 且没有原值、flag 和 reason；
- 未登记的实验室 itemid；
- ACTIVE 文件引用历史 schema、历史结果或 blocked 产物。

AUDIT_ONLY 文件可以读取 derived 或隔离 itemid，但必须显式标注审计用途且不能输出到正式分析表。

LEGACY_BLOCKED/SUPERSEDED 文件仍接受全仓扫描并生成问题清单；发现问题不修改历史原件，但任何 ACTIVE 依赖会升级为硬失败。

## 10. 测试策略

实施采用 red-green-refactor。首批失败夹具至少覆盖：

1. 血 BUN 正确纳入。
2. 尿液及其他体液 BUN 隔离。
3. charttime 在 T12 前但 storetime 在 T12 后。
4. 缺失/未知单位。
5. specimen 重复。
6. `>x`、`<x` 和区间原值保留。
7. derived-only 不得成为正式特征。
8. 静默范围置 NULL 被扫描器阻止。
9. ACTIVE SQL 引用 LEGACY_BLOCKED 表或文件。
10. 未登记 SQL 进入执行计划。
11. Postgres 与 BigQuery schema 映射不改变概念合同。
12. 合规 SQL 通过且危险夹具按预期失败。

测试全部使用合成数据或 SQL 文本，不嵌入患者级数据。

## 11. 初始修订范围

第一实施批次覆盖：

- 当前主线 `sql_v3_2` 中所有实验室依赖及其传递上游；
- `090B_create_compact_predictors_v33.sql` 的实验室特征；
- NT-proBNP 队列/表型路径；
- 使用乳酸、pH 或其他实验室的 eligibility、shock proxy、secondary outcome 路径；
- `sql_v4_2` 中计划保留为正式敏感性分析的文件；
- BigQuery V2 审计和 Postgres 正式流水线间的合同一致性。

历史目录不原地改写。若需要其中逻辑，复制为新的版本化 ACTIVE 文件并记录 replacement；历史文件继续 blocked。

## 12. 发文前全仓复现审计

正式投稿前必须从空白版本化 schema 重跑一次完整流水线。审计范围包括所有影响结果的 SQL、Python、R、Shell、配置、锁文件和 notebook；notebook 必须可无状态重跑并保存执行环境，否则标为禁止进入发表 run。运行后生成：

1. `final_run_manifest.json`：commit、输入快照、全部执行代码/规则/config 哈希、软件版本和执行顺序。
2. `pipeline_authority_audit.csv`：每个可执行工件的状态、引用关系和扫描结论。
3. `lab_quality_summary.csv`：各概念 eligible、quarantine、late、wrong-fluid、unknown-unit、duplicate、censor 和 raw/derived 覆盖计数。
4. `cohort_flow_frozen.csv`：每个排除步骤的唯一人数与原因。
5. `feature_manifest_frozen.csv`：最终变量、来源、窗口、单位、聚合、缺失策略和模型顺序。
6. `outcomes_frozen.csv` 的聚合核对结果及三态结局计数；患者级文件仍留在受控环境。
7. `publication_evidence_matrix.csv`：论文每个数字、表、图和结论对应的 run、脚本、输入和输出哈希。
8. `stale_result_scan.md`：README、周报、PPT、旧输出中可能误引的历史人数和性能清单。

发表验收还必须确认：

- 工作树干净，Git HEAD 与远端一致；
- 所有最终数字来自同一 run；
- 从 cohort 到图表无人工复制数字；
- 训练折之外没有插补、缩放、筛选或校准拟合；
- 主分析与敏感性分析使用明确分开的 manifest；
- 旧 `2,424/334`、旧 `5,555/454` 等未冻结数字未被误写为最终结果；
- 方法、结果、补充材料与实际代码合同一致。

## 13. 分阶段实施

### 阶段 A：代码权威与静态质量门

建立权威清单、扫描器、依赖检查和合成夹具；扫描全仓并形成历史问题账本。此阶段不运行患者级数据。

### 阶段 B：当前主线实验室重构

建立 raw 合同层，修订当前主线和正式敏感性路径；执行 Postgres/BigQuery 语法、数据合同、覆盖和计数 QC。旧结果全部标为历史，不覆盖。

### 阶段 C：最终队列后的冻结运行

DHF 表型、T12 风险集和三态结局通过临床门控后，复制最终 cohort 快照，从空白 schema 全链重跑，冻结特征、模型和论文证据矩阵。

阶段 A/B 不能宣称最终模型完成；阶段 C 未通过前不得发表最终人数或性能。

## 14. 故障与回滚

- 规则冲突、未知 itemid/单位、未登记 SQL、历史依赖或时间合同缺失：硬失败。
- 数据库/网络不可用：`not_run`，保留待执行命令，不伪造成功。
- 新主线重构结果与历史结果不同：保留两套结果，先定位差异来源，不以追求旧数字为目标。
- 规则更新导致特征变化：提升规则版本，复制新输出表，不覆盖前一版本。
- 若新实现失败，可回退 Git commit；不得把 LEGACY_BLOCKED 文件重新标成 ACTIVE 作为临时绕过。

## 15. 非目标

本设计不在当前阶段：

- 冻结最终 DHF 人数、事件数或模型性能；
- 自动把论文或经验阈值升级为 active 规则；
- 修改 MIMIC 原始表；
- 把患者级 quarantine 样例提交 Git；
- 同时重构生命体征、药物、尿量和影像的全部语义；这些领域复用同一权威状态与规则生命周期，分别建立后续规则包。

## 16. 验收标准

实施完成必须同时满足：

1. 阶段 A 中 Git 跟踪的 SQL 100% 登记；阶段 C 前所有影响结果的可执行工件 100% 登记，重复和遗漏均为零。
2. 正式执行计划不含 LEGACY_BLOCKED、SUPERSEDED 或未登记文件。
3. 当前主线全部实验室输入通过精确语义、单位、可用时间、重复和 episode 门控。
4. 正式特征不存在 derived-only 静默回填。
5. 范围外值均可追溯到原值、flag 和 reason。
6. BUN 错误体液夹具及实际聚合隔离继续通过。
7. scanner 危险夹具按预期失败，合规夹具通过。
8. 相关单元、静态、数据库语法和聚合 QC 全部通过。
9. 项目规则包、安装 Skill 与运行 manifest 的版本关系可核验。
10. 最终发表 run 能从空白 schema 重现，并生成论文证据矩阵。
