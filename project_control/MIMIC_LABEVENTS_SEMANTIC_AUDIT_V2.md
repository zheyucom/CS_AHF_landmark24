# MIMIC-IV 实验室语义与可用时间审计 v2

状态：`not_run`。2026-09-17 本机 BigQuery dry-run 因无法连接 `bigquery.googleapis.com:443` 而超时；本地结构测试与清洗 Skill 静态审计已通过，但不能据此声称 BigQuery 语法或患者级结果已验证。

## 这版解决什么

V2 将“发现候选概念”和“正式纳入数据”拆成两个文件：

- `MIMIC_LABITEM_CANDIDATE_DISCOVERY_V1.sql` 只读取 `d_labitems`，允许用名称正则发现候选，不读取患者行，也不激活规则。
- `MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql` 只使用精确 `itemid × fluid × category × unit` 合同读取 `labevents`，不以名称正则纳入特征。

V1 保留为历史模板，但已被 V2 取代，不能继续作为正式实验室冻结依据。

## 当前精确合同

| 概念 | itemid | fluid / category | 单位 | 状态 |
| --- | ---: | --- | --- | --- |
| BUN | 51006 | Blood / Chemistry | mg/dL | 正式合同 |
| 乳酸 | 50813 | Blood / Blood Gas | mmol/L | 正式合同 |
| 肌酐 | 50912 | Blood / Chemistry | mg/dL | 项目审计合同 |
| pH | 50820 | Blood / Blood Gas | units | 项目审计合同 |
| NT-proBNP | 50963 | Blood / Chemistry | pg/mL | 项目审计合同 |
| Troponin T | 51003 | Blood / Chemistry | ng/mL | 项目审计合同 |

Troponin I、新一代高敏肌钙蛋白及其他名称候选不会自动进入正式合同；须经当前 release 字典核验、来源记录、失败夹具、回归测试和人工批准。

## BUN 污染隔离

V2 显式统计但不纳入以下非血液 itemid：

- `51104` 尿；`51045`、`51842` 其他体液；`50851` 腹水。
- `51804` 脑脊液；`51825` 关节液；`51922` 胸水；`51951` 粪便。

任何新出现、名称相似但未登记的 itemid 只能由候选发现 SQL 输出为 `proposed_candidate`。

## 时间与重复合同

- 当前审计框架使用项目表 `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_candidates`，窗口为 `[ICU T0, T12)`；它是现有审计框架，不是最终冻结模型队列。
- 结果可用时间固定为 `GREATEST(charttime, COALESCE(storetime, charttime))`，必须严格早于 T12。
- `storetime < charttime`、跨多个 episode、缺少 specimen、`specimen_id × itemid` 重复均进入 quarantine。
- 最终冻结队列建立后，只替换并重新验证 `cohort` 数据源，不改变实验室语义与可用时间合同。

## 原值与删失结果

保留 `labevent_id`、`specimen_id`、`value`、`valuenum`、`valueuom`、参考区间、flag、priority、comments、charttime 和 storetime。

- `>x`/`>=x` 保存 lower bound。
- `<x`/`<=x` 保存 upper bound。
- `x-y` 或 `x/y` 保存区间，不取中点。
- 未知/缺失单位进入 quarantine；不凭数值范围换算。
- 不把缺失补为 0，不静默截尾、winsorize 或覆盖 raw 值。

## raw/derived 对账

- BUN：raw 与 `mimiciv_derived.chemistry` 按 `stay_id + specimen_id` 汇总 `raw_only / derived_only / both`。
- 乳酸：因 `mimiciv_derived.bg` 不暴露 `specimen_id/storetime`，按 `stay_id + charttime` 对账，并在输出 notes 明示该限制。
- derived 表没有足够的结果可用时间字段，不能替代 raw 表的 T12 门控。

## 输出与执行边界

最终输出只有聚合行：字典合同、语义/时间/quarantine 汇总及 raw/derived 覆盖；默认不输出患者标识。

网络恢复后依次执行：

```bash
bq query --project_id=project-9386bb9f-de39-47eb-886 --location=US \
  --use_legacy_sql=false --dry_run \
  < project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql

bq query --project_id=project-9386bb9f-de39-47eb-886 --location=US \
  --use_legacy_sql=false --format=csv \
  < project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql \
  > project_control/bigquery/mimic_labevents_semantic_audit_v2_summary.csv
```

执行后登记查询 hash、处理字节数、运行时间、MIMIC release、每个 reason code 计数和 raw/derived 差集；在这些证据存在前，状态保持 `not_run`。
