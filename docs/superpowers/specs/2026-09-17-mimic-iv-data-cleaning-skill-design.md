# MIMIC-IV 数据清洗 Skill 设计

日期：2026-09-17  
状态：书面设计，待用户复核后实施

## 1. 决策

采用“实验室优先、可扩展的守门型 Skill”，名称固定为 `mimic-iv-data-cleaning`，安装目标为用户本机 Codex 的 `~/.codex/skills/mimic-iv-data-cleaning`。

Skill 的职责不是替代临床判断，也不是自动修改患者级数据；它负责在 MIMIC-IV 提取、清洗、特征构建和 SQL 审计时主动发现语义污染、时间泄漏、单位错误、来源漏失和不可复现操作。

## 2. 第一版范围

第一版强制执行：

- MIMIC 版本、schema、表和官方 `mimic-code` commit 登记。
- `labevents` 与 `mimiciv_derived.chemistry/bg` 的实验室合同。
- `itemid × fluid × category × unit` allowlist 与隔离规则。
- `charttime/storetime` 结果可用时间门控。
- 比较符号、原始值、单位、标本、重复和 raw/derived 双向对账。
- 对现有 SQL 的只读静态风险扫描。

第一版不自动决定：

- 新临床阈值、异常值的临床含义或最终排除标准。
- MICE、模型选择、变量筛选或因果解释。
- 药物、尿量、生命体征的完整专科规则；这些领域先报告风险，待独立规则包验证后再升级为强制门控。
- 对既有 SQL、队列或患者级结果的批量改写。

## 3. 触发方式

以下请求应触发 Skill：

- “清洗/提取 MIMIC-IV 数据、实验室或特征”。
- “审查 MIMIC SQL、itemid、单位、标本或时间窗”。
- “为什么 raw 和 derived 数量不一致”。
- “把新的 MIMIC 清洗经验加入规则库”。

典型任务包括：

1. 审查 BUN 查询是否混入尿液、腹水或其他体液。
2. 对账 raw `labevents itemid=50813` 与 derived `bg.lactate`。
3. 检查 `[T0,T12)` 特征是否使用 T12 后才入库的结果。
4. 将一个新污染案例登记为候选规则并生成合成回归夹具。

## 4. 目录结构

```text
mimic-iv-data-cleaning/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── workflow.md
│   ├── rule-schema.md
│   ├── mimic-iv-lab-rules.json
│   └── source-provenance.md
└── scripts/
    ├── audit_mimic_sql.py
    ├── validate_rule_pack.py
    └── test_fixtures.py
```

- `SKILL.md`：保持精简，只规定执行顺序、失败边界和何时读取引用文件。
- `workflow.md`：定义数据合同、隔离、对账和输出流程。
- `rule-schema.md`：定义规则字段与证据状态。
- `mimic-iv-lab-rules.json`：存放可机器验证的实验室 allowlist、denylist、单位和来源合同。
- `source-provenance.md`：固定官方源码 commit、论文或项目回归案例的可追溯来源。
- `audit_mimic_sql.py`：只读扫描 SQL，识别名称模糊匹配、缺少标本/单位门控、只用 `charttime`、缺失值补零及缺少 raw/derived 对账等风险。
- `validate_rule_pack.py`：验证规则结构、状态、来源、版本和冲突。
- `test_fixtures.py`：运行纯合成数据回归测试，不包含任何患者级数据。

第一版不创建 `assets/`，避免无用途目录。

## 5. 执行流程

1. 读取研究合同，确认 cohort unit、index、landmark、predictor window 和 outcome window。
2. 确认 MIMIC 版本、源表和官方概念 commit；未知时停止过滤并标记 `not_run`。
3. 加载对应规则包，以精确 itemid 为主键核对 `fluid/category/unit/source`。
4. 保留 raw provenance，再生成规范化值；任何不匹配行进入 quarantine，不静默删除。
5. 使用 `GREATEST(charttime, COALESCE(storetime, charttime))` 作为实验室最早可用时间。
6. 按 `specimen_id × itemid` 检查重复与聚合，明确 first/last/min/max 的研究用途。
7. 对核心变量执行 raw→derived 与 derived→raw 双向 anti-join。
8. 输出门控结果、隔离原因、计数变化、异常样例和仍需人工决定的问题。

无患者级数据库连接时，Skill 只能生成 SQL、静态审计和 `not_run` 报告，不能把模板写成已完成的数据审计。

## 6. 规则与学习生命周期

每条规则使用统一状态：

`proposed → sourced → fixture_added → regression_tested → active → deprecated`

升级要求：

- `proposed`：记录触发案例、风险和适用版本，不参与自动过滤。
- `sourced`：补充官方源码、数据字典或可复核研究来源。
- `fixture_added`：加入能复现错误的最小合成夹具。
- `regression_tested`：错误夹具失败、修复后通过，并验证无相邻规则回归。
- `active`：经人工批准后才进入强制门控。
- `deprecated`：保留历史原因和替代规则，不直接删除。

Codex 可以自动提出 `proposed` 规则、补充来源和生成测试，但不得自行把规则提升为 `active`。这样能够积累经验，同时避免把单篇论文、偶然异常或模型误判固化为临床规则。

每条规则至少包含：`rule_id`、MIMIC 版本、概念名、允许/隔离 itemid、fluid、category、单位、时间字段、来源表、官方 concept、处理动作、reason code、证据链接、状态和测试 ID。

## 7. 首批强制回归案例

### BUN

- 接受 `itemid=51006` 且语义为 `UREA NITROGEN | CHEMISTRY | BLOOD`。
- 隔离 `51104`（尿）、`51045`（其他体液）、`50851`（腹水）。
- 名称含 “urea nitrogen” 但不在 allowlist 的新 itemid 必须 fail-closed。
- 官方 derived 范围 `0 < valuenum <= 300` 用于分析值合同；raw 原值和隔离原因必须保留。

### 乳酸

- 核心 itemid 为 `50813`，保留 `specimen_id`、标本描述、`charttime` 和 `storetime`。
- 测试 raw-only、derived-only、both 三类对账。
- 固化本项目“derived `bg` 曾漏掉 550 个 raw 有效 stay”为回归背景，但测试只使用合成行，不嵌入患者标识或患者级计数明细。

### 通用实验室风险

- `>x`、`<x`、区间值保留上下界和 censor type，不改写为精确值。
- 未知单位、fluid/category 不匹配、结果晚于 landmark、重复 specimen 和跨 stay 连接不确定均进入 quarantine。
- 禁止按最常见单位自动删除少数单位，禁止用经验分位数静默截尾，禁止把缺失实验室或尿量补为 0。

## 8. 输出合同

每次审计输出：

- `audit_manifest.json`：版本、commit、输入指纹、SQL hash、运行状态和时间合同。
- `preflight_report.md`：硬失败、警告、未决问题和建议动作。
- `concept_coverage.csv`：每个概念的纳入、隔离及 raw/derived 覆盖计数。
- `quarantine_reasons.csv`：reason code 级汇总；默认不导出患者级样例。

输出属于当前研究项目，不写入 Skill 安装包。若需要患者级样例，只保存在已授权项目目录中并遵循原数据访问要求。

## 9. 错误处理

- MIMIC 版本、字典或时间合同未知：停止过滤，输出硬失败。
- 规则之间存在重叠或冲突：`validate_rule_pack.py` 失败，不加载冲突规则。
- 数据库不可用：输出 `not_run`，保留待执行 SQL。
- derived 覆盖异常：不自动回填，先输出双向差集和 join 路径审计。
- 新 itemid/单位出现：隔离并建立 `proposed` 规则，不猜测归类。

## 10. 验证与验收

实施完成需同时满足：

1. Skill Creator `quick_validate.py` 通过，`agents/openai.yaml` 与 `SKILL.md` 一致。
2. BUN 正确血液行通过，尿/体液/腹水污染行全部被隔离。
3. 乳酸 raw-only/derived-only/both 对账结果正确。
4. T12 后 storetime 行被隔离，T12 前可用行保留。
5. 比较符号、未知单位、重复 specimen 和缺失值补零风险均有测试。
6. SQL 扫描器在危险夹具上失败、在合规夹具上通过。
7. 本机安装目录不包含患者级数据、密钥、项目绝对路径、未完成标记或占位文件。
8. 在新上下文中用原始任务前向测试，能够主动指出错误标本和时间泄漏，不依赖当前对话提示。

## 11. 安装与后续扩展

先在项目暂存目录构建和验证，再复制到用户本机 Codex Skill 目录；不修改现有 Skills，不初始化项目 Git 仓库。完成后保留可分享的无患者数据副本。

药物、尿量、生命体征等领域以独立规则文件扩展。eICU、OMOP 等数据库不共用 MIMIC itemid 规则，而是复用相同生命周期和审计接口建立各自 Skill。
