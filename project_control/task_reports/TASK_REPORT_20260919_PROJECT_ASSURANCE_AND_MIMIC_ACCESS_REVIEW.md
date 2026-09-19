# 任务报告：项目质量保证体系与当前 MIMIC 访问复核

日期：2026-09-19

## 1. 用户问题与本轮范围

用户担心自己无法逐行审查 Codex 生成的 SQL、数据清洗和统计代码，因此难以判断课题质量；同时询问 Prompt/可复现合同是否足够、临床数据库文章的高质量研究套路、BigQuery 与本地 MIMIC-Note 的差异，以及当前是否可以连接 MIMIC。

本轮目标是：

1. 评估当前 DHF 项目的“科学问题—数据—表型—结局—模型—验证—报告”审查链条；
2. 给出不依赖逐行读代码的可执行质量保证办法；
3. 核验本机 PostgreSQL、MIMIC-Note/ED 资源和 BigQuery 的当前状态；
4. 不改变队列、变量、结局或模型定义。

## 2. 使用的文件、版本和数据状态

- 本机正式项目：`/Users/zheyu/Desktop/CS_AHF_landmark24`
- 当前 Git 分支：`main`
- 重点文件：
  - `project_control/DHF_PROJECT_REPRODUCIBILITY_CONTRACT_V1.md`
  - `project_control/STATISTICAL_ANALYSIS_PLAN_DHF_PREDICTION_V1.md`
  - `project_control/PIPELINE_AUTHORITY_MANIFEST.csv`
  - `project_control/task_reports/TASK_REPORT_20260919_MIMIC_LAB_PIPELINE_QUALITY_GATE_PHASE_A.md`
  - `project_control/task_reports/TASK_REPORT_20260917_BIGQUERY_CONNECTIVITY_AND_ACCESS.md`
  - `project_control/MIMIC_NOTE_DOWNLOAD_AND_INSTALL.md`
  - `project_control/MIMIC_DHF_SOURCE_COVERAGE_LEDGER_20260916.md`
- 本轮只读核验本机数据库元数据和表统计，不查询患者级明细，不重跑队列或模型。

## 3. 当前 MIMIC 访问核验

### 3.1 本机 PostgreSQL

本机通过以下只读连接成功：

```text
database: mimiciv31
user: postgres
server: PostgreSQL 12.18
```

可见 schema 及表数量：

| Schema | 当前可见表数 | 说明 |
|---|---:|---|
| `mimiciv_hosp` | 22 | 核心住院模块 |
| `mimiciv_icu` | 9 | 核心 ICU 模块 |
| `mimiciv_derived` | 63 | 官方派生概念 |
| `mimiciv_note` | 未发现 | 当前本机未加载 |
| `mimiciv_ed` | 未发现 | 当前本机未发现 |
| `eicu` | 未核验 | 不把其存在或可用性假设为事实 |

当前关键表可见：`patients`、`admissions`、`icustays`、`labevents`、`chartevents`。数据库统计信息显示约有 364,627 patients、546,028 admissions、94,458 icustays、约 1.58 亿 labevents、约 4.33 亿 chartevents；这些是数据库统计值，正式论文仍应由冻结运行中的精确计数和 QC 表提供。

结论：本机 MIMIC 核心结构化数据现在可以只读调用；这不等于 Note、ED、CXR 或 ECG/Waveform 已加载，也不等于 DHF 正式队列已经冻结。

### 3.2 BigQuery

本轮本机 shell 未发现可直接调用的 `bq`/`gcloud` CLI。项目最近的连接报告显示：

- Google API 已能被访问，连接超时问题已解决；
- 但访问 `physionet-data:mimiciv_hosp.d_labitems` 返回 `Access Denied`；
- 因此 `MIMIC_LAB_AUDIT_V2` 的状态是 `not_run_access_denied`；
- dry-run 或 `SELECT 1` 只能证明 SQL/API 解析和网络路径，不证明患者级 MIMIC 表读取权限。

结论：BigQuery 当前不能按“已可正式取数”处理。需要在授权账号、PhysioNet 数据协议和目标项目权限确认后，重新执行只读字典查询，再执行患者级审计。

### 3.3 Note 是否必须下载

当前本机没有 `mimiciv_note`。这不是整个课题的硬性阻塞：

- 如果主问题依赖结构化实验室、生命体征、ICU治疗和时间窗，核心分析可以在 hosp/icu/derived 上完成；
- Note 的价值主要是补充 HF 锚点、否定/不确定语义、替代诊断和放射科文本证据；
- 没有 Note 不能把“未见文本证据”当作阴性；
- 是否下载 Note 应由表型缺口和预设敏感性分析决定，而不是因为其他论文下载了就照搬；
- 如果使用 BigQuery 导出的放射科报告，应把它作为独立、不可变、带版本和哈希的文本快照，不要写成当前 PostgreSQL 已加载 Note。

## 4. 对当前项目质量的判断

当前项目可以分成两个层面：

### 已较强的部分

- 已明确科学问题、T0/T12/T60 时间轴和竞争事件；
- 已把 D​​HF 表型拆成 HF 锚点、失代偿/充血和客观检查/管理支持，避免单项 ICD、BNP 或影像直接充当确诊；
- 已有项目级复现合同、变量字典、语义规则、验收标准、运行登记和来源覆盖登记；
- 已明确原始值、单位、比较符号、时间、缺失语义和代理暴露不能被静默覆盖；
- 已把历史 SQL 与当前主线隔离，阶段 A 质量门使 `ACTIVE=0` 时正式运行 fail-closed；
- 已在统计方案中写明 Fine–Gray 主模型、person-period 补充、校准、Brier、竞争风险口径和外部验证角色。

### 仍不能声称完成的部分

- 最终 DHF 操作性表型未冻结；
- T12 风险集和三态结局未冻结；
- 300 条放射科标注仍不是临床金标准，若报告一致性还需要第二位独立盲法标注者；
- 医嘱代理仍不等同于 eMAR 实际执行；
- MIMIC 实验室流水线阶段 A 只建立了“不能误跑”的边界，阶段 B 的 raw 合同层、eligible/quarantine、正式 rollup 和数据库级 QC 尚未完成；
- 当前 `ACTIVE=0`，不能从历史 SQL 或旧模型输出直接产生最终论文结果；
- 最终模型、锁模、严格内部验证和本院外部验证尚未完成。

综合判断：你的项目“研究控制基础”已经明显高于仅靠一段 Prompt 生成 SQL 的项目，但“临床科学闭环和最终统计证据”尚未完成。当前不应把项目描述为已经达到高分期刊投稿就绪。

## 5. 不需要逐行读代码的质量保证方案

逐行读代码不是唯一、也不是最有效的审查方式。建议采用五层独立证据链：

### 第一层：科学合同审查

只检查一页合同是否回答：

- 研究对象是谁；
- T0 是什么；
- 预测信息截止何时；
- 目标事件和竞争事件是什么；
- 研究是预测还是因果；
- 主要 estimand 和主模型是什么；
- 哪些定义在看结果前已经冻结。

这一层由研究者和临床/统计顾问负责，Codex 只能整理和质疑，不能替你决定临床含义。

### 第二层：数据合同审查

每个变量必须有：schema、表名、字段/itemid、时间字段、单位、聚合规则、重复值规则、缺失语义、临床范围、是否允许进主模型和证据来源。

要求 Codex 输出“变量审计表”，不要只输出长 SQL。每一行都要能回答“从哪里来、取哪个时间、为什么这样聚合、缺失代表什么”。

### 第三层：程序不变量审查

不看每一行 SQL，先看可验证的不变量：

- 输出粒度是否严格为一患者一个 index ICU episode；
- 主键是否唯一；
- 时间窗是否满足 `T0 <= time < T12`；
- 预测器是否没有读取 T12 后字段；
- 原始值是否保留；
- 单位和体液是否经过精确 allowlist；
- 行数漏斗是否逐步可解释；
- 错误值进入 quarantine 而不是静默变成 NULL/0；
- 每个输入和输出是否有 SHA-256、版本和运行日志。

可用合成夹具、抽样病例和独立 Python/R 小程序验证，不需要人工通读全部 SQL。

### 第四层：统计审查

每次模型运行至少检查：

- 事件、竞争事件、观察不完整和删失数；
- 每个外层折的分布；
- 有效参数数和收缩规则；
- 所有插补、标准化、编码、变量选择是否在训练折内；
- OOF 性能、校准截距/斜率、Brier、时间依赖 AUC、决策曲线；
- 外部验证是否原样锁模，而不是在院内数据上重新调参；
- 敏感性分析是否在看结果前预先登记。

### 第五层：临床与报告审查

- 对关键表型做预设人工抽样；
- 若报告 inter-rater reliability，第二位标注者必须独立盲法；
- 用 TRIPOD+AI、PROBAST+AI、RECORD/STROBE 做投稿前缺口清单；
- 把候选人数、工作结果、可行性结果和最终冻结结果严格分栏。

## 6. Prompt 和可复现合同能解决什么

Prompt/合同有用，但只能解决“说清楚和留下证据”的问题：

- 固定问题、输入、输出、时间窗和验收标准；
- 减少聊天上下文丢失；
- 使另一位分析者能按同一规范复跑；
- 让 Codex 在运行前暴露缺失字段和阻塞项；
- 记录 SQL、脚本、版本、seed、哈希和运行结果。

它们不能自动解决：

- DHF 临床定义是否合理；
- 文本判读是否为金标准；
- 医嘱是否等于实际给药；
- 竞争风险是否与 estimand 匹配；
- 变量是否因缺失机制而产生偏倚；
- 外部验证人群是否可迁移；
- 结果是否具有临床价值。

因此“长 Prompt + 代码跑通”不等于“研究正确”。当前最稳妥的组合是：项目级合同 + 步骤级协议 + 独立审计 + 合成测试 + 人工临床裁决 + 冻结运行登记。

## 7. 建议的 Codex 角色分离

同一轮不要让 Codex 同时“提出定义、写代码、宣称通过”。建议按以下命令分阶段：

1. `PLAN ONLY`：只读合同和文件，输出 estimand、字段映射、风险和阻塞，不写代码。
2. `IMPLEMENT`：按已批准合同写 SQL/脚本和测试。
3. `AUDIT ONLY`：像审稿人一样独立检查，不修改代码，不接受上一轮“已通过”结论。
4. `REPRODUCE ONLY`：在干净环境重跑，比较输入/输出哈希和 QC。
5. `CLINICAL REVIEW PACK`：生成病例抽样表、原文行号和盲法标注包；不自动把 AI 草案升为金标准。
6. `REPORT`：只在门控通过后更新任务报告、总览和运行登记。

可直接给本地 Codex 的最小提示词：

```text
任务类型：[PLAN ONLY / IMPLEMENT / AUDIT ONLY / REPRODUCE ONLY]
科学合同：[文件路径和版本]
本轮只允许：[明确范围]
禁止：[改队列定义、使用未冻结结果、把医嘱写成执行、把AI预审写成金标准]
必须先输出：
1. 输入/输出粒度；
2. 表、字段、itemid、时间窗、单位和缺失规则；
3. 潜在泄漏和替代定义；
4. 逐门控验收标准；
5. 未决问题和阻塞项。
只有所有硬门通过后，才允许执行或修改，并生成任务报告。
```

## 8. 评价高质量临床数据库文章的实际套路

高分文章的核心不是“用了多少模型”或“用了 BigQuery 还是本地数据库”，而是：

```科学问题
→ 明确 estimand/时间零点
→ 可辩护的操作性表型
→ 可追溯数据合同
→ 队列流图与排除原因
→ 无泄漏变量构建
→ 与结局结构匹配的统计模型
→ 严格内部验证和校准
→ 原样外部验证/可迁移性
→ 预设敏感性与局限性
→ TRIPOD+AI/PROBAST+AI/RECORD 透明报告
```

你目前已经掌握了这条路线的骨架和很多防错工具，但还没有完成最后的科学冻结和验证闭环。尤其需要把“Codex 生成了代码”升级为“每个关键判断都有独立证据和失败条件”。

## 9. 当前建议的优先顺序

1. 暂不因“别人下载了 Note”而立即扩展数据；先做表型缺口审计，确认 Note 能改变哪一个预先定义的门控。
2. 完成 MIMIC 实验室流水线阶段 B：raw 合同层、eligible/quarantine、正式 rollup、数据库级 QC；逐文件通过后才将 SQL 标为 ACTIVE。
3. 建立 10–15 个合成边界夹具和 20–30 个独立人工核对病例，至少覆盖时间边界、单位、比较符号、错误体液、重复值、缺失和治疗代理。
4. 冻结 MIMIC DHF 表型、T12 风险集、三态结局和观察完整性。
5. 依据冻结事件数重新确定有效参数和收缩策略，再运行最终模型。
6. 在锁模后将同一预处理和系数原样用于本院外部验证，并报告校准与临床净获益。

## 10. 本轮修改文件

- `project_control/task_reports/TASK_REPORT_20260919_PROJECT_ASSURANCE_AND_MIMIC_ACCESS_REVIEW.md`
- `project_control/RESEARCH_DASHBOARD.md`
- `project_control/task_reports/README.md`

本轮没有修改研究定义、队列、变量、结局或模型。

## 11. 可重复性信息

- PostgreSQL 只读核验：`/Library/PostgreSQL/12/bin/psql -X -w -h localhost -U postgres -d mimiciv31`
- 核验内容：数据库身份、schema 表数、关键表存在性和统计值。
- BigQuery 状态依据项目连接报告，不将 dry-run 解释为患者级访问。
- 本轮没有使用患者级查询结果作为论文结论，没有设置或消耗随机种子。
