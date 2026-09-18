# MIMIC-IV 清洗 Skill 交付说明

日期：2026-09-17

## 结论

`mimic-iv-data-cleaning` 已安装到本机 Codex，并在项目内保留可分享副本。Skill 第一版聚焦实验室数据，主动检查 itemid、标本、类别、单位、结果可用时间、重复 specimen、比较符号、缺失补零和 raw/derived 覆盖。

## 本机直接打开路径

- 本说明：`/Users/zheyu/Desktop/CS_AHF_landmark24/deliverables/MIMIC-IV清洗Skill-交付说明-2026-09-17.md`
- 可分享 Skill：`/Users/zheyu/Desktop/CS_AHF_landmark24/deliverables/mimic-iv-data-cleaning/`
- Codex 安装目录：`/Users/zheyu/.codex/skills/mimic-iv-data-cleaning/`
- 书面设计：`/Users/zheyu/Desktop/CS_AHF_landmark24/docs/superpowers/specs/2026-09-17-mimic-iv-data-cleaning-skill-design.md`
- 实施计划：`/Users/zheyu/Desktop/CS_AHF_landmark24/docs/superpowers/plans/2026-09-17-mimic-iv-data-cleaning-skill-implementation.md`
- 实验室审计 V2：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.sql`
- V2 说明：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/MIMIC_LABEVENTS_SEMANTIC_AUDIT_V2.md`
- BigQuery 连接与权限报告：`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/task_reports/TASK_REPORT_20260917_BIGQUERY_CONNECTIVITY_AND_ACCESS.md`

在 Finder 按 `Command + Shift + G`，粘贴任一路径即可定位。安装目录中的主入口是 `SKILL.md`。

## 新鲜验证证据

- 13/13 Skill 合成回归通过，8/8 SQL 结构回归通过；V1 误执行会先触发 `ASSERT FALSE`，不会读取患者级表。
- 规则包校验通过，共 2 条 active 实验室规则：BUN 与乳酸。
- Python 语法编译通过。
- Skill Creator 官方 `quick_validate.py`：`Skill is valid!`
- 安装目录与项目可分享副本逐文件一致（忽略 Python `__pycache__`）。
- V2 经清洗 Skill 静态扫描无硬失败；候选发现 SQL 不读取患者级表。

## 项目 SQL 的实际发现

旧 `project_control/MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql` 命中过：

1. `MIMIC001`：名称或元数据正则参与实验室纳入。
2. `MIMIC003`：时间窗没有使用 `GREATEST(charttime, COALESCE(storetime, charttime))`。
3. `MIMIC008`：模糊候选查询没有绑定已批准的精确 itemid。
4. `MIMIC007`（警告）：未展示 raw↔derived 的 raw-only、derived-only、both 双向对账。

扫描过程一度误报 3 个影像 SQL；该误报已先写成失败夹具，再把规则收紧为仅在 `labevents` 上触发。重新扫描后影像 SQL 均不再误报。

V1 现已标记为 `superseded_not_run`。V2 将名称候选发现与正式患者级审计分离，并修复上述四类缺口。

## 已激活的关键规则

- BUN：只接受 `itemid=51006`、`Blood / Chemistry / mg/dL`。
- BUN 隔离扩展为 8 个有来源的非血液 itemid：`51104`、`51045`、`50851`、`51804`、`51825`、`51842`、`51922`、`51951`。
- 乳酸：核心 `itemid=50813`，必须保留 specimen、charttime/storetime，并双向对账 raw 与 `mimiciv_derived.bg`。
- 新规则只能按 `proposed → sourced → fixture_added → regression_tested → active` 升级；Codex 不得自行激活临床规则。

## 下一步

网络问题已修复：gcloud 已写入本机系统代理 `127.0.0.1:7897`，清空 proxy 环境变量后 `bq SELECT 1` 和 V2 dry-run 均成功。当前患者级状态为 `not_run_access_denied`：访问 `physionet-data:mimiciv_hosp.d_labitems` 被拒绝。需先完成 PhysioNet/MIMIC 授权并确认同一 Google 账号有表读取权限，再执行字典候选、V2 dry-run 和正式汇总；在此之前不冻结实验室变量。
