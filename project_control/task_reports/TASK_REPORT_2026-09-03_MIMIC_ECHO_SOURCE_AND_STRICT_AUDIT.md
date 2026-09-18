# 任务报告：MIMIC-IV-Echo 数据源定位与严格 DHF 心超审计准备

日期：2026-09-03  
状态：本轮执行准备完成；等待用户 Terminal 完成 BigQuery 权限/schema/查询核验

补充执行记录：当前环境可读取 `gcloud auth list`，活动账号为 `zheyu.sy@gmail.com`；实际执行 `bq --location=US ls --project_id=physionet-data mimiciv_echo` 约 30 秒无返回后中止，未取得数据集列表或临床行数据。该结果只能说明当前执行环境到 BigQuery API 的连接仍不稳定，不能解释为 Echo 数据集不存在或账号权限不足。

## 本轮结论

严格研究对象仍冻结为：

> 成人首次 index ICU stay 中，在 `[T0-24 h,T12)` 已有可追溯的 `echo-supported DHF` 操作性表型，并到达 T12；不要求患者在 T0 入 ICU 时已经完成 DHF 诊断。

严格入组的心超条件不是“临床上推测应该做过”，而是数据中必须同时能够证明：

```text
ICU patient
AND echo actually performed
AND echo result available before T12
AND result supports cardiac structural/functional abnormality
```

此外仍需 HF retrospective anchor、肺充血或临床失代偿证据、治疗/管理强化证据，以及 T12 前无预设 overt shock proxy。未做心超、只有医嘱/操作记录、结果缺失或结果明确正常者不能进入严格 `echo-supported DHF`；但必须保留在全 ICU 候选宇宙中报告选择性，不能把它们统一编码成“心超阴性”。

## 新确认的数据源

官方 MIMIC-IV-Echo v1.0.1 页面：

<https://physionet.org/content/mimic-iv-echo/1.0.1/>

官方说明确认：

- 结构化 Echo 表包含约 206,488 项研究的长格式测量；
- 主要字段为 `subject_id`、`measurement_id`、`measurement_datetime`、`test_type`、`measurement`、`measurement_description`、`result`、`unit`；
- `test_type` 可区分 TTE、TEE 和 stress echo；本研究初始审计只纳入 TTE/TEE；
- `measurement_datetime` 是检查执行/测量时间，但没有独立的报告签署或结果可见时间；
- 结构化结果可通过 `subject_id` 连接 MIMIC-IV，但不能仅凭患者 ID 证明属于同次住院或 index ICU；
- `echo_study_list` 可用于 study 与结构化测量、心超报告的时间关联，但当前是否可查及真实 schema 仍需用户 Terminal 核验。

因此当前只能把 `measurement_datetime` 作为结果可用性的保守代理，不能在论文中写成严格的“报告在 T12 前签署”。这个限制会写入方法和局限性。

## 已完成的文件工作

1. 更新 `project_control/bigquery/README.md`：加入 MIMIC-IV-Echo 数据源、单独授权要求、schema 核验命令和 113 查询路径。
2. 更新 `project_control/bigquery/111_discover_echo_sources.sh`：先定向核查 `mimiciv_echo.echo_record_list`、`echo_study_list` 和 `structured_measurement`，再扫描其他可见数据集。
3. 新增 `project_control/bigquery/113_query_mimic_echo_strict_candidate.sql`：
   - 保留全部候选 ICU stay；
   - 严格使用 `[T0-24 h,T12)`；
   - 只纳入 TTE/TEE 结构化测量；
   - 分开输出结构化心超记录、结果时间代理和 draft abnormal-support flag；
   - 不把单独 LVEF、BNP、procedure 或缺失结果当作 DHF 确诊；
   - 为 HFpEF 保留舒张功能、充盈压、左房/左室、右心、肺动脉压和瓣膜等结果描述的筛查入口。
4. 更新 `project_control/RESEARCH_DASHBOARD.md`、`project_control/README.md` 和严格研究定义，记录 Echo 数据源和时间字段限制。

## 当前已知事实

- 本地 108 审计：5,549 个有效候选 stay；462 例有 TTE/TEE 操作记录；可用结构化 LVEF 为 0。
- 这 462 例不能直接当作“心超异常”或“严格 DHF”；当前仍没有最终 `echo-supported DHF` 队列计数。
- `CXR OR CT` 仍是肺充血证据域的主审计规则；CXR+CT 同时阳性只作敏感性分析，不是心超严格入组条件。

## 用户下一步

在自己的 Terminal 执行以下命令，不要把 token、密码或原始临床文本发回项目：

```sh
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
bq --location=US ls --project_id=physionet-data mimiciv_echo
bq --location=US show --format=prettyjson physionet-data:mimiciv_echo.echo_record_list
bq --location=US show --format=prettyjson physionet-data:mimiciv_echo.echo_study_list
bq --location=US show --format=prettyjson physionet-data:mimiciv_echo.structured_measurement
```

确认三张表可读后，运行：

```sh
sed 's/YOUR_BILLING_PROJECT/project-9386bb9f-de39-47eb-886/g' \
  /Users/zheyu/Desktop/CS_AHF_landmark24/project_control/bigquery/113_query_mimic_echo_strict_candidate.sql \
  > /tmp/113_query_mimic_echo_strict_candidate_filled.sql
bq --location=US query --use_legacy_sql=false \
  --destination_table=project-9386bb9f-de39-47eb-886:ahf_work.echo_result_audit_v1 \
  --replace < /tmp/113_query_mimic_echo_strict_candidate_filled.sql
```

返回结果后首先报告这些计数：

```text
n_candidate_stays
n_stays_with_tte_or_tee_result
n_stays_with_draft_abnormal_support
n_stays_without_echo_result
n_studies_by_test_type
```

然后从有结果、疑似异常、明确正常/不确定三类抽取 20-50 个 study 做人工核查。人工核查完成前，`strict_echo_supported_draft_flag` 只能叫 draft，不能用于最终建模或论文主结果。

## 尚未完成与阻塞

1. 用户账号是否获得 MIMIC-IV-Echo 的 credentialed access 尚未确认。
2. BigQuery 三张表的真实 schema 和可查询性尚未由当前 Codex 执行环境完成核验。
3. 113 输出尚未生成，因此不能报告严格 Echo-supported 队列人数、事件数或 EPV。
4. MIMIC Echo 结果时间只有 `measurement_datetime` 代理，必须在论文中披露。
5. 严格表型冻结后，才可按最终事件数重新冻结低维特征并运行 Fine-Gray 主模型及 person-period 补充模型。

## 本轮资源估计

- 用户 Terminal 权限/schema 核验：约 10-20 min；
- 113 查询及结果导出：约 10-30 min，取决于 BigQuery 作业；
- 20-50 条 Echo 结果人工核查与规则修订：约 1-3 h；
- 严格队列重建、EPV 和最终建模：待 Echo 结果规模确定后约 4-8 h。
