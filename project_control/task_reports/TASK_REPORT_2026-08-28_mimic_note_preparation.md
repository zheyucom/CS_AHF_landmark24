# TASK_REPORT — 2026-08-28 MIMIC-IV-Note 补装准备

## 本轮完成

- 明确 MIMIC-IV-Note 可提供 `discharge`、`radiology` 及 detail 表；当前项目数据库尚未安装这些 schema。
- 明确 MIMIC-IV-Note 不能假定提供完整 ED/住院 physician notes、床旁查体、肺超声或可靠的首次医生 AHF 诊断时间。
- 建立文本/影像抽取的时间边界：只有 `admittime <= charttime < intime` 的报告才能作为 pre-T0 证据；出院总结只作回顾性验证，不能进入 0–12 h 预测器。
- 新增安装脚本、schema 可用性审计 SQL 和 AHF 文本/影像抽取方案文档。

## 新增产物

- `scripts/prepare_mimic_note.sh`
- `sql_v3_2/audits/100_audit_note_source_availability.sql`
- `project_control/reports/2026-08-28_mimic_text_ahf_extraction_plan.md`

## 当前未执行原因

本机尚未发现已下载的四个 Note 压缩文件，且 PostgreSQL 连接需要密码。因此本轮没有执行加载、没有产生 Note 行数，也没有伪造影像覆盖率。

## 用户侧准备

1. 通过 PhysioNet 授权下载 MIMIC-IV-Note 2.2 的 `note/` 目录四个压缩文件。
2. 确认 PostgreSQL 用户可以连接 `mimiciv31`，并保证磁盘空间足够。
3. 运行：`scripts/prepare_mimic_note.sh /path/to/mimic-iv-note/2.2/note`

## 下一步自动化工作

加载成功后，我会继续建立 radiology pre-T0 证据表，抽取肺水肿/血管充血/胸腔积液及否定表达，进行人工抽样复核，再与 `650/66` 队列连接，报告表型覆盖率和敏感性结果。

## 本轮续作补充

- 增强 `scripts/prepare_mimic_note.sh`：增加 `psql`、文件可读性、无交互数据库认证和磁盘空间预检，避免安装过程中无提示卡在密码输入。
- 新增 `sql_v3_2/audits/101_create_pre_t0_radiology_ahf_evidence.sql`：按 `admittime <= charttime < ICU intime` 抽取放射科报告中的肺水肿、血管充血、胸腔积液、心影增大、否定和不确定表达；当前仅作为验证层。
- 新增 `project_control/MIMIC_NOTE_DOWNLOAD_AND_INSTALL.md`：记录 PhysioNet 官方入口、最小下载范围、本机安装命令、认证、空间和后续抽取步骤。

当前卡点仍是用户侧尚未下载四个 Note 压缩文件；数据到位后再执行加载和真实覆盖率统计。本轮未伪造 Note 行数、影像支持率或人工复核精度。

## 实际源审计结果

已在本机 `mimiciv31` 执行 `sql_v3_2/audits/100_audit_note_source_availability.sql`：

- `mimiciv_note.discharge`：`not_installed`
- `mimiciv_note.radiology`：`not_installed`
- `mimiciv_note.discharge_detail`：`not_installed`
- `mimiciv_note.radiology_detail`：`not_installed`
- `mimiciv_cxr.cxr`：`not_installed`

因此，当前不能报告 Note 行数、放射科覆盖率或影像阳性率。用户侧下一动作见 `project_control/MIMIC_NOTE_DOWNLOAD_AND_INSTALL.md`；优先下载 Note 四表即可，不需要先下载完整 CXR 影像。

## BigQuery 路径补充

- 用户已获得 MIMIC-IV-Note 2.2 的 GCP BigQuery 访问权限。
- 当前 Codex 会话未启用 BigQuery 原生连接器，本机也没有 `gcloud/bq` 登录，因此不能代提交 BigQuery job；未索取用户密码或服务账号密钥。
- 新增 `sql_v3_2/audits/102_export_strict_ids_for_bigquery.sql`，可从本地 PostgreSQL 导出严格队列的三列最小 join key。
- 新增 `project_control/bigquery/103_query_pre_t0_radiology.sql`，在用户自己的 BigQuery 项目中只查询严格队列对应的 pre-T0 radiology 报告。
- 新增 `project_control/bigquery/README.md`，说明 Note 权限、MIMIC-IV core 权限、billing/quota project 和 BigQuery Job User 的区别。

下一步：用户可先执行本地 ID 导出，再在 BigQuery 控制台上传 ID 表并运行 103 查询；若希望我直接执行，需要在 Codex/ChatGPT 中启用并连接 BigQuery 原生连接器，当前会话尚未具备该工具。

## 本轮执行结果

- 已修复 `102_export_strict_ids_for_bigquery.sql` 的 `psql \copy` 换行问题。
- 已成功导出 `650` 行严格队列 ID（另含 1 行表头）：`project_control/bigquery/strict_pre_t0_ahf_ids.csv`。
- 已通过安装脚本 shell 语法检查。
