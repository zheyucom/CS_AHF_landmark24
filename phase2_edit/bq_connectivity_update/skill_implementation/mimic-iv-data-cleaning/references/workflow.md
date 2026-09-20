# MIMIC-IV 清洗工作流

## 目录

1. 前置合同
2. 实验室数据合同
3. 时间、重复与派生表对账
4. 输出合同
5. 运行状态

## 1. 前置合同

开始前记录：

- MIMIC-IV release 与 schema。
- 官方 `mimic-code` commit。
- cohort unit（subject、hadm、stay 或 landmark episode）。
- index、landmark、predictor window 与 outcome window。
- 源表、join key、过滤 SQL hash 和输入快照标识。

任一项未知时，不执行正式过滤。输出 `not_run`，列明缺失合同及待执行 SQL。

## 2. 实验室数据合同

正式变量必须通过 `itemid × fluid × category × unit` allowlist。`label`、LOINC 或正则匹配只能发现候选，不能直接生成特征。

先保存以下 raw provenance，再生成任何分析值：

```text
subject_id, hadm_id, stay_id/episode_id, specimen_id, itemid,
label, fluid, category, value, valuenum, valueuom,
charttime, storetime, flag, comments, source_table, rule_id
```

建议 reason code：

| reason_code | 含义 |
| --- | --- |
| `unregistered_itemid` | itemid 不在已激活 allowlist |
| `wrong_fluid_*` | 已知同名但错误标本 |
| `fluid_mismatch` | 字典 fluid 与合同不一致 |
| `category_mismatch` | 字典 category 与合同不一致 |
| `unknown_unit` | 单位缺失或未登记 |
| `available_after_landmark` | 结果在窗口结束时尚不可见 |
| `duplicate_specimen_itemid` | 同一 specimen/itemid 出现冲突或重复 |
| `ambiguous_episode_join` | 无法唯一归属 episode |

异常先进入 quarantine。分析范围过滤、单位换算或去重必须作为后续显式步骤，并保留原值、规则 ID 和前后计数。

## 3. 时间、重复与派生表对账

实验室最早可用时间：

```sql
GREATEST(le.charttime, COALESCE(le.storetime, le.charttime))
```

默认要求该时间严格早于窗口终点。另行审计 `storetime IS NULL`、`storetime < charttime` 和跨 episode 连接。

对于 landmark 前后分窗，sample time and availability time 必须同时落在
same analysis window。T12 前采样但 T12 后才可用的结果属于迟到结果，
must not be reclassified as a post-landmark sample，也不得进入 pre-landmark 特征。first/last
按 `charttime, labevent_id` 确定性排序；delta 必须显式定义方向，例如
`last - first`。可用时间决定资格，采样时间决定合格记录之间的生理顺序。
静态扫描器以 `MIMIC010` 标记 charttime 前后分窗缺少 availability 双边界的 SQL；
这是 fail-closed 预检，不替代对 CTE 数据流、边界开闭和临床时间定义的人工复核。

在聚合前检查 `specimen_id × itemid`。若选择 first、last、min 或 max，记录选择服务于基线状态、最差状态、治疗反应还是其他预注册目标。

核心变量必须在相同 cohort、键和时间窗下进行双向覆盖：

```text
raw_only     = raw keys - derived keys
derived_only = derived keys - raw keys
both         = raw keys ∩ derived keys
```

覆盖异常不自动回填。先按 itemid、标本、单位、时间和 join 路径定位原因。

## 4. 输出合同

每次审计至少生成：

- `audit_manifest.json`：release、commit、输入指纹、SQL hash、运行状态、时间合同和规则包版本。
- `preflight_report.md`：硬失败、警告、未决问题与建议动作。
- `concept_coverage.csv`：概念级纳入、隔离、raw-only、derived-only、both 计数。
- `quarantine_reasons.csv`：reason code 级汇总；默认不导出患者级样例。

输出写到当前研究项目，不写入 Skill 安装目录。

## 5. 运行状态

- `passed`：所有硬门控通过，并有实际执行证据。
- `failed`：存在语义、时间、单位、连接或覆盖硬失败。
- `not_run`：缺少数据库、权限、版本、合同或尚未执行。
- `not_run_access_denied`：API 可连接、SQL 可验证，但目标 MIMIC 表明确返回 `Access Denied`；不得用 `SELECT 1`、dry-run 或其他镜像替代数据授权证明。

静态 SQL 扫描通过不等于 `passed`；连接测试通过不等于数据授权通过；dry-run 通过不等于患者级运行通过。没有患者级连接或表权限时只能报告静态结果与相应的 `not_run` 状态。
