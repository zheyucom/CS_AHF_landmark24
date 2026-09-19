# MIMIC-IV BigQuery 授权与表级访问预检报告

日期：2026-09-19
状态：通过（metadata + LIMIT 0 表级读取；患者级运行仍未执行）

## 本次实际验证

- `gcloud` 版本 583.0.0，`bq` 版本 2.1.38。
- 检测到 1 个活动认证账号；没有输出账号地址、token 或密码。
- PhysioNet 项目目录可见：`mimiciv_3_1_hosp`、`mimiciv_3_1_derived`、`mimiciv_3_1_icu`、`mimiciv_echo`、`mimiciv_note`。
- `mimiciv_3_1_hosp.labevents` 与 `d_labitems` 的 `LIMIT 0` 查询均成功。
- 两张表的必要字段均存在：labevents 包含 `labevent_id/specimen_id/itemid/charttime/storetime/value/valuenum/valueuom`；d_labitems 包含 `itemid/label/fluid/category`。
- 对 BUN 允许 itemid 51006 和 8 个隔离 itemid 做了字典级查询，只返回字典元数据，没有患者记录。

## 关键诊断

第一次查询把 BigQuery 作业提交到了 `physionet-data` 项目，失败原因为该项目不授予当前账号 `bigquery.jobs.create`。改用本机已配置的个人项目作为作业项目后，PhysioNet 受控表零行读取成功。因此此前问题是“作业项目选择错误”，不是需要重新授权 MIMIC 表。

此外，`bq` 不在默认 PATH 中，实际路径为：

`/Users/zheyu/google-cloud-sdk/bin/bq`

后续命令必须将 `/Users/zheyu/google-cloud-sdk/bin` 加入 PATH，或使用绝对路径。

## BUN 字典核验

当前 MIMIC-IV 3.1 字典确认：

- 允许：51006 = `Urea Nitrogen` / `Blood` / `Chemistry`。
- 隔离：51104（Urine）、51045（Other Body Fluid）、50851（Ascites）、51804（Cerebrospinal Fluid）、51825（Joint Fluid）、51842（Other Body Fluid）、51922（Pleural）、51951（Stool）。

这项字典证据已同步回项目内规则包；它仍是数据清洗合同，不是论文正文内容。

## 尚未执行的内容

本次没有读取患者级记录、没有导出数据、没有运行完整模型 SQL。当前状态应记为 `passed_metadata_and_zero_row_read`，而不是患者级 `passed`。下一步需将项目现有 PostgreSQL 风格 Phase-C SQL 与 BigQuery 执行环境做方言和作业项目适配，然后再进行最小范围的聚合 QC。

## 产物完整路径

- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/task_reports/TASK_REPORT_20260919_MIMIC_ACCESS_PREFLIGHT.md`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/audits/bigquery_mimic_access_preflight_20260919.json`
- `/Users/zheyu/Desktop/CS_AHF_landmark24/phase2_edit/bq_connectivity_update/skill_implementation/mimic-iv-data-cleaning/references/mimic-iv-lab-rules.json`
