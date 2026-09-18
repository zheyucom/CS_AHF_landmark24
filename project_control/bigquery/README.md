# BigQuery 路径：MIMIC-IV-Note 表型验证

## 能否直接获取

本机 `gcloud`/`bq` 当前账号为 `zheyu.sy@gmail.com`，但 CLI 到 Google API 的连接仍可能超时。2026-09-03 已通过用户已登录的 BigQuery 控制台成功读取 MIMIC-IV-Echo schema、运行临床数据审计并创建结果表；因此可优先使用控制台。不会要求用户提供 Google 密码、服务账号密钥或 OAuth token。

你已经获得的 MIMIC-IV-Note 2.2 访问权限足以读取 Note 文本，但本研究还需要：

1. 同一 Google 账号对 BigQuery 中的 MIMIC-IV-Note 表有读取权限；核心表权限只在需要从 BigQuery 重新连接结构化核心数据时才需要；
2. 一个你自己的 GCP 项目作为查询作业的 billing/quota project；
3. 该项目中启用 BigQuery API，并具备创建查询作业和写入自己的临时/结果数据集的权限。通常需要 `BigQuery Job User`，若要上传 CSV 或创建结果表，还需要对自己项目数据集的表创建/写入权限。

Note 权限本身不自动授予核心 MIMIC-IV 表权限，也不自动提供查询费用项目。当前查询已改为使用本地审计后导出的时间字段，因此不会因核心表 `bigquery.tables.getData` 不足而阻塞。

### MIMIC-IV-Echo（新增）

PhysioNet 已发布独立的 [MIMIC-IV-Echo v1.0.1](https://physionet.org/content/mimic-iv-echo/1.0.1/)，包含结构化 TTE、TEE 和 stress echo 测量。研究所需的 BigQuery 数据集为 `physionet-data.mimiciv_echo`，已知表包括：

- `echo_record_list`：DICOM 文件、`study_id`、`subject_id`、采集时间；
- `echo_study_list`：`study_id` 与结构化测量及可用心超报告的时间关联；
- `structured_measurement`：`subject_id`、`measurement_id`、`measurement_datetime`、`test_type`、`measurement`、`measurement_description`、`result`、`unit`。

该数据集需要单独的 credentialed access；MIMIC-IV-Note 访问权限不自动包含 MIMIC-IV-Echo 权限。当前账号已经取得读取权限。真实 schema 显示 `echo_study_list` 含 `study_datetime`、`note_id` 和 `note_charttime`，故本项目以 `study_datetime` 审计检查时间、以 `note_charttime` 作为结果可用性代理。后者不是独立的报告签署时间，不能写成严格的“报告在 T12 前签署”。

MIMIC-IV-Echo 只按 `subject_id` 连接，不能直接保证心超发生在 index ICU 或同一次住院内；必须同时满足候选表中的 `subject_id`、`admittime`、`intime` 和 `[T0-24 h,T12)` 时间窗。官方页面还明确给出存在与 MIMIC-IV encounter 无对应关系的 Echo 研究，因此不能按患者 ID 直接纳入。

## 推荐流程

### 1. 从本地数据库导出 5,555 个 DHF radiology 候选 ID

在项目根目录执行：

```sh
cd /Users/zheyu/Desktop/CS_AHF_landmark24
/Library/PostgreSQL/12/bin/psql -X -w -v ON_ERROR_STOP=1 \
  -h localhost -U postgres -d mimiciv31 \
  -f sql_v3_2/audits/106_export_dhf_radiology_candidates_for_bigquery.sql
```

输出文件：

```text
project_control/bigquery/dhf_radiology_candidates.csv
```

该文件包含 5,555 个 landmark-eligible HF ICD 锚点的 `stay_id, subject_id, hadm_id, admittime, intime` 和 3 个既有审计标记，不包含 Note 文本；时间列用于保持严格的 pre-T0 边界。当前已生成并通过字段数 QC：5,556 行含表头、`bad_rows=0`。

### 2. 在自己的 BigQuery 项目创建工作数据集

在 BigQuery 控制台选择自己的 GCP 项目，创建数据集，例如 `ahf_work`。随后把上述 CSV 上传为表：

```text
YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_candidates
```

上传字段类型建议：前三个 ID 为 `INTEGER`，`admittime/intime` 为 `TIMESTAMP`，三个现有标记为 `INTEGER`；首行作为列名。

`admittime` 和 `intime` 已由本地审计队列导出。这样 radiology 验证查询不再读取
`mimiciv_3_1_hosp.admissions` 或 `mimiciv_3_1_icu.icustays`，可以绕开当前核心表的
`bigquery.tables.getData` 权限阻塞；时间边界仍严格是 `admittime <= charttime < intime`。

### 3. 运行项目查询

打开 `project_control/bigquery/106_query_pre_t0_dhf_radiology.sql`，将其中的 `YOUR_BILLING_PROJECT` 替换成你的项目 ID，在 BigQuery 控制台运行，并把查询结果保存/导出为 CSV。

查询返回全部 5,555 个 HF ICD anchor 对应的 pre-T0 radiology 报告，并严格执行：

```text
admittime <= radiology.charttime < ICU intime
```

结果保留原始报告文本、时间、命中词、否定/不确定标志、`report_available_pre_t0_flag` 和规则版本，供后续人工抽样复核。它不会把文本变量放进 0-12 h 预测器，也不会直接把 regex 命中当作 DHF 金标准。

将 106 的完整结果保存为：

```text
YOUR_BILLING_PROJECT.ahf_work.dhf_radiology_raw_v2
```

然后运行 `project_control/bigquery/107_query_dhf_radiology_patient_summary.sql`，得到 5,555 个候选的 patient-level 报告覆盖、报告可用性和 congestion-screen 汇总。107 是筛查汇总，不是最终 DHF 标签。

### 4. 导出 106 结果后生成本地 QC 与盲法标注包

将 106 结果导出为本地 CSV（保留原始列名），然后运行：

```sh
python3 project_control/bigquery/prepare_dhf_radiology_annotation.py \
  --raw-csv /absolute/path/to/dhf_radiology_raw_v2.csv \
  --output-dir project_control/bigquery/controlled_annotation_20260829
```

脚本会重新核验 `admittime <= charttime < intime`、统计 `storetime` 在 ICU 前可用的比例，并从 definite-positive、negated/uncertain 和 no-hit 三层各随机抽取至多 100 份报告。它生成：

- `dhf_radiology_annotation_round1.csv`：第一位标注者的盲法工作表；
- `dhf_radiology_annotation_round2_blinded.csv`：20% 独立双盲复核工作表；
- `dhf_radiology_sampling_key_restricted.csv`：仅用于主持人保留的抽样层信息；
- `README.md`：导入 QC、抽样量和数据使用边界。

这些输出含受控临床文本，不能与结局、预测器或模型预测结果合并，也不能写入公开论文工件。

人工抽样验证的标签定义与盲法要求见：

```text
project_control/templates/DHF_RADIOLOGY_ANNOTATION_GUIDE.md
```

旧 `102_export_strict_ids_for_bigquery.sql` 与 `103_query_pre_t0_radiology.sql` 保留用于复核原有 650 例 strict candidate，不能替代 106/107 的广义 DHF 表型验证。

### 5. 补齐主分析窗口 `[T0-24 h,T12)`

106/107 只覆盖严格 pre-T0，不能替代主研究窗口。主队列的 radiology 证据还需运行新增的 109/110：

```sh
sed 's/YOUR_BILLING_PROJECT/project-9386bb9f-de39-47eb-886/g' \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/109_query_landmark12_dhf_radiology.sql \
  > /tmp/109_query_landmark12_dhf_radiology_filled.sql
bq --location=US query --use_legacy_sql=false \
  --destination_table=project-9386bb9f-de39-47eb-886:ahf_work.dhf_radiology_raw_landmark12_v1 \
  --replace < /tmp/109_query_landmark12_dhf_radiology_filled.sql
```

然后生成患者级汇总：

```sh
sed 's/YOUR_BILLING_PROJECT/project-9386bb9f-de39-47eb-886/g' \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/110_query_landmark12_dhf_radiology_patient_summary.sql \
  > /tmp/110_query_landmark12_dhf_radiology_patient_summary_filled.sql
bq --location=US query --use_legacy_sql=false \
  --format=csv < /tmp/110_query_landmark12_dhf_radiology_patient_summary_filled.sql \
  > /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/dhf_radiology_patient_summary_landmark12_v1.csv
```

109 的原始结果包含 `[T0-24 h,T12)` 内的报告文本、检查时间和报告可见时间；110 是一人一行筛查汇总。两者都只用于 DHF 表型验证，不得作为 0-12 h 预测器。运行后将 109 原始 CSV 和 110 汇总 CSV 放回项目目录，再进行本地模态分类、人工抽样和事件数/EPV 审计。

### 网页控制台替代路径（已验证）

若 `bq`/`gcloud` 在 Codex 进程中连接 `bigquery.googleapis.com:443` 超时，可直接使用已登录的 [BigQuery 控制台](https://console.cloud.google.com/bigquery?project=project-9386bb9f-de39-47eb-886)。这不是再次认证，也不需要提供密码或 token。

在 SQL 编辑器中，把 109/110 文件内的 `YOUR_BILLING_PROJECT` 替换为 `project-9386bb9f-de39-47eb-886`，并分别用下列前缀包裹查询，使结果持久化：

```sql
CREATE OR REPLACE TABLE `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_raw_landmark12_v1` AS
-- 109 查询正文
```

```sql
CREATE OR REPLACE TABLE `project-9386bb9f-de39-47eb-886.ahf_work.dhf_radiology_patient_summary_landmark12_v1` AS
-- 110 查询正文
```

2026-09-04 已通过此路径完成两张表；QC 为 `5,549` 个有效候选、`7,828` 份主窗口报告、`3,886` 个有报告 stay、`3,542` 个 T12 前可见 stay，且报告 `storetime` 无缺失。运行后通过结果面板的“保存查询结果”下载 CSV，并放回本目录，文件名保持为 `dhf_radiology_raw_landmark12_v1.csv` 与 `dhf_radiology_patient_summary_landmark12_v1.csv`。

### 6. 核查并审计 MIMIC-IV-Echo

先确认当前账号是否可见 Echo 数据集和真实 schema：

```sh
bq --location=US ls --project_id=physionet-data mimiciv_echo
bq --location=US show --format=prettyjson physionet-data:mimiciv_echo.echo_record_list
bq --location=US show --format=prettyjson physionet-data:mimiciv_echo.echo_study_list
bq --location=US show --format=prettyjson physionet-data:mimiciv_echo.structured_measurement
```

三张表已于 2026-09-03 核验可读，并已在控制台运行以下查询创建 `echo_result_audit_v1`。下列命令保留为 CLI 可复现路径：

```sh
sed 's/YOUR_BILLING_PROJECT/project-9386bb9f-de39-47eb-886/g' \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/113_query_mimic_echo_strict_candidate.sql \
  > /tmp/113_query_mimic_echo_strict_candidate_filled.sql
bq --location=US query --use_legacy_sql=false \
  --destination_table=project-9386bb9f-de39-47eb-886:ahf_work.echo_result_audit_v1 \
  --replace < /tmp/113_query_mimic_echo_strict_candidate_filled.sql
```

该查询只审计 TTE/TEE 结构化结果，不把 procedure 记录、单独 LVEF 正常值或单独 BNP 当成 DHF 确诊；输出中的 `echo_abnormal_support_draft_flag` 仍需按 measurement description/result 抽样复核后才能冻结。实测 `[T0-24 h,T12)` 结果为 5,549 个有效候选、61 个链接 study、9 个 `note_charttime<T12`、41 个 draft abnormal-support 和 6 个 strict draft。因此 Echo 只能用作 MIMIC 的高特异性验证层，不能作为主开发队列硬门槛。

## 先做权限测试

### 命令行状态（2026-08-29）

本机已发现 gcloud 安装在 `/Users/zheyu/google-cloud-sdk/bin`，当前账号为
`zheyu.sy@gmail.com`，默认项目为 `project-9386bb9f-de39-47eb-886`，并已成功取得
access token。Codex 执行环境访问 Google API 时出现网络连接超时，因此下面命令应在你自己的
Terminal 中运行；不要把 token 或凭据发回项目目录。

先在 Terminal 执行：

```sh
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
gcloud auth list
gcloud config set project project-9386bb9f-de39-47eb-886
```

创建工作数据集并上传候选 CSV：

```sh
bq --location=US mk --dataset project-9386bb9f-de39-47eb-886:ahf_work
bq --location=US load --replace --skip_leading_rows=1 \
  --source_format=CSV \
  project-9386bb9f-de39-47eb-886:ahf_work.dhf_radiology_candidates \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/dhf_radiology_candidates.csv \
  'stay_id:INT64,subject_id:INT64,hadm_id:INT64,admittime:TIMESTAMP,intime:TIMESTAMP,acute_hf_icd_anchor_flag:INT64,pre_t0_iv_loop_emar_flag:INT64,pre_t0_ntprobnp_ge300_flag:INT64'
```

然后先验证两张源表：

```sh
bq --location=US query --use_legacy_sql=false \
  'SELECT COUNT(*) AS n FROM `physionet-data.mimiciv_note.radiology`'
bq --location=US query --use_legacy_sql=false \
  'SELECT COUNT(*) AS n FROM `physionet-data.mimiciv_3_1_hosp.admissions`'
```

查询 106 时，先将 SQL 中的 `YOUR_BILLING_PROJECT` 替换为
`project-9386bb9f-de39-47eb-886`，然后可将结果直接保存为工作表：

```sh
sed 's/YOUR_BILLING_PROJECT/project-9386bb9f-de39-47eb-886/g' \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/106_query_pre_t0_dhf_radiology.sql \
  > /tmp/106_query_pre_t0_dhf_radiology_filled.sql
bq --location=US query --use_legacy_sql=false \
  --destination_table=project-9386bb9f-de39-47eb-886:ahf_work.dhf_radiology_raw_v2 \
  --replace < /tmp/106_query_pre_t0_dhf_radiology_filled.sql
```

再运行 107 并导出汇总：

```sh
sed 's/YOUR_BILLING_PROJECT/project-9386bb9f-de39-47eb-886/g' \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/107_query_dhf_radiology_patient_summary.sql \
  > /tmp/107_query_dhf_radiology_patient_summary_filled.sql
bq --location=US query --use_legacy_sql=false \
  --format=csv < /tmp/107_query_dhf_radiology_patient_summary_filled.sql \
  > /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/dhf_radiology_patient_summary_v2.csv
```

若 `ahf_work` 已存在，第一条 `bq mk` 报已存在即可继续；若 CLI 报 `Access Denied`，记录完整错误中的
权限名称即可，不要改动 SQL 规则。

可在 BigQuery 控制台分别执行：

```sql
SELECT COUNT(*) AS n
FROM `physionet-data.mimiciv_note.radiology`;
```

```sql
SELECT COUNT(*) AS n
FROM `physionet-data.mimiciv_3_1_hosp.admissions`;
```

```sql
SELECT COUNT(*) AS n
FROM `physionet-data.mimiciv_3_1_icu.icustays`;
```

若 Note 查询成功而 core 查询失败，仍可直接运行本项目的 radiology 验证 SQL；只有在需要用 BigQuery 重新连接核心表、扩展其他结构化字段或独立复核时间边界时，才需要申请 MIMIC-IV core 数据集权限。若 Note 查询也失败，则需要确认 Note 数据集授权；若查询作业无法启动，再配置 billing/quota project 或 `BigQuery Job User`。

## 当前本地结果版本

### 2026-09-04 主窗口网页导出限制

109/110 主窗口查询已在网页控制台成功运行。患者级汇总可完整保存为 5,549 行；网页本地全文下载曾被 BigQuery 限制为 `7,558/7,828` 行，但 2026-09-04 已通过 GCS 完整导出并下载 `7,828/7,828` 行。当前模态、CXR/CT 覆盖率和阳性层审计只能使用 `dhf_radiology_raw_landmark12_v1_complete.csv`，不能使用历史不完整文件。

推荐先在网页控制台运行 `111_query_landmark12_radiology_report_audit.sql`，将结果保存为 BigQuery 表 `ahf_work.dhf_radiology_report_audit_landmark12_v1`，再查询并下载只含结构化标志的紧凑表。完整全文也可使用 GCS 路径 `gs://ahf_bigquery_export/dhf_landmark12/radiology_raw_v1_000000000000.parquet`。下载后必须验证报告行数等于 7,828；本地脚本 `build_landmark12_radiology_audit.py` 在不完整时会保留警告标志，不会静默当成全量。

若需要保留全文，可使用 `112_query_landmark12_radiology_batch.sql` 分四批导出：将 `YOUR_BILLING_PROJECT` 替换为 `project-9386bb9f-de39-47eb-886`，再依次将 `BATCH_OFFSET` 替换为 `0`、`2000`、`4000`、`6000`。每批运行后在网页结果菜单选择本地 CSV 下载，文件分别命名为 `batch0.csv`、`batch2000.csv`、`batch4000.csv`、`batch6000.csv`。最后运行：

```sh
python3 project_control/bigquery/merge_landmark12_radiology_batches.py \
  batch0.csv batch2000.csv batch4000.csv batch6000.csv \
  project_control/bigquery/dhf_radiology_raw_landmark12_v1_complete.csv
```

脚本会强制检查总行数 `7,828`、表头一致和 `(stay_id,note_id)` 无重复；任一批下载不完整都会停止，不能继续用于冻结影像表型。

更推荐使用 GCS 中转导出全文：先在与 BigQuery 数据集相同区域（当前为 `US`）的 Cloud Storage bucket 中建立私有目录，再运行 `114_export_landmark12_radiology_to_gcs.sql`。该 SQL 使用 Parquet 和通配符文件名，适合长文本字段和分片导出；下载 GCS 文件后再在本地合并/读取。所需权限为：运行 BigQuery 作业的权限，以及目标 bucket 的 `storage.objects.create`；只有新建 bucket 才需要额外的 bucket 创建权限。建议使用一次性新目录并保持 `overwrite = false`，避免申请或使用项目级 Owner 权限。

当前有效版本为：

- `dhf_radiology_raw_v2.csv`：4,303 条 pre-T0 radiology 报告；
- `dhf_radiology_patient_summary_v2.csv`：5,549 个有效时间边界候选的一行级汇总；
- `dhf_radiology_annotation_sample300_v2.csv`：每个规则筛查层 100 条的 300 条抽样；
- `controlled_annotation_20260830_v2/`：300 条第一轮盲法标注表、60 条第二标注者复核表和抽样 key。

目录中的 `dhf_radiology_patient_summary_v1.csv` 是排除异常时间边界前的旧导出，不得用于最终表型审计。

## 是否还要申请更多数据

当前不需要先申请或下载完整 MIMIC-CXR 影像。对肺部证据，先用 MIMIC-IV-Note radiology 报告做时间合规的 CXR/CT 验证即可。MIMIC-IV-Echo credentialed access 已生效并已完成第一轮行级审计；下一步是分层人工复核 61 个链接 study。MIMIC-IV-Note 仍不保证提供完整连续的 ED physician notes、肺超声或可靠的首次医生诊断时间，因此不能把它描述成完整临床金标准。
