# 任务报告：DHF 表型验证准备

日期：2026-08-29  
状态：gcloud 已登录；用户已完成候选 CSV/工作数据集准备，当前等待 BigQuery 106 原始放射科报告查询结果。

## 本轮完成

1. 明确后续入组工作是 **DHF 多域表型验证**，不是直接把 `NT-proBNP >=300` 或正则命中当作确诊。
2. 补齐 BigQuery 106 导出结果的本地可重复处理脚本：`project_control/bigquery/prepare_dhf_radiology_annotation.py`。
3. 脚本将自动复核全部报告仍满足 `admittime <= charttime < intime`，并报告 `storetime < intime`、缺失和 ICU 后可见的比例。
4. 脚本按预先定义的三层筛查（definite-positive、negated/uncertain、no-hit）各随机抽样至多 100 份报告，生成第一轮盲法标注和 20% 独立双盲复核表。
5. 研究总览已将“strict AHF 主候选/待重建”的遗留表述修正为 `legacy AHF candidate` 与 `DHF 多域版待重建`。
6. 检测到 `/Users/zheyu/google-cloud-sdk/bin/gcloud` 和 `bq`；`zheyu.sy@gmail.com` 已是活动账号，默认项目 `project-9386bb9f-de39-47eb-886` 有效，access token 获取成功。
7. 发现当前 Codex 执行环境访问 `bigquery.googleapis.com:443` 和 `oauth2.googleapis.com:443` 超时；这不是 MIMIC 表权限错误，已将可直接运行的 CLI 命令补入 BigQuery README。
8. README 已补充用 `sed` 自动生成带项目 ID 的 106/107 临时 SQL，避免手动改动原始版本化 SQL。
9. 本地检查确认目前尚未出现 `dhf_radiology_raw_v2` 或 107 patient-level CSV，因此尚未开始报告覆盖率和盲法抽样。
10. 再次从 Codex 执行环境运行最小 Note 查询；gcloud 认证正常，但 BigQuery API 在 45 秒内无响应，已停止无响应进程。当前阻塞确认是执行环境网络，不是 SQL 或已返回的表权限错误。
11. 通过已登录 BigQuery 浏览器实际提交 106 后，发现 `radiology.charttime` 为 `DATETIME`、候选表时间为 `TIMESTAMP`；已修正 106 将候选边界转换为 `DATETIME`，准备重跑。

## 当前判断

- 影像报告和精确时间序列构建是入组可信度的关键；规则型 NLP 是可审计的筛查工具，不能替代临床验证。
- MIMIC-IV-Note 的放射科报告可支持 pre-T0 肺水肿/肺血管充血证据；它不能完整补齐症状、体征、肺超声或首次医生诊断时间。因此论文应写为 **operational phenotype**，不应宣称临床金标准确诊。
- `dhf_radiology_candidates.csv` 是 5,555 个 HF anchor 的候选宇宙与时间锚点，供 BigQuery 精准选取同次住院、ICU 前报告；它不是最终 DHF 入组名单，也不含预测器或结局。
- 最终主队列应在报告级人工验证后，从 `DHF candidate`、`radiology-supported DHF` 和 `multidomain DHF` 中，依据预先锁定的证据门和事件数决定。

## 立即执行步骤

1. 在本机 Terminal 按 README 的 CLI 命令上传 `project_control/bigquery/dhf_radiology_candidates.csv` 至 `ahf_work.dhf_radiology_candidates`。
2. 运行 `project_control/bigquery/106_query_pre_t0_dhf_radiology.sql`，将完整结果保存为 `ahf_work.dhf_radiology_raw_v2`，并导出为 CSV。
3. 运行 107 得到 patient-level summary；本地脚本操作和输出说明见 `project_control/bigquery/README.md`。
4. 将 106 和 107 的 CSV 放入项目受控目录后，运行本轮新增的本地脚本，完成数据 QC 与盲法标注包生成。
5. 完成盲法临床标注、20% 双盲复核和裁决后，重报每个表型层级的样本量、事件数、竞争事件、报告覆盖和 EPV；届时才冻结最终低维 Fine-Gray 模型。

## 当前阻塞与投入

| 阻塞 | 需要谁完成 | 主动投入 |
|---|---|---:|
| 106 原始报告与 107 汇总尚未导出 | 用户已完成候选表准备；需在本机 Terminal 提交 106 并保存结果表 | 约 0.5-1 h |
| 放射科报告盲法临床标注 | 临床标注者与第二标注者 | 约 4-8 h |
| 锁定规则和完成最终表型审计 | 项目侧 | 约 4-8 h |
| 最终队列建模与敏感性分析 | 项目侧 | 约 8-16 h |

## 新增文件

- `project_control/bigquery/prepare_dhf_radiology_annotation.py`
- `project_control/bigquery/test_prepare_dhf_radiology_annotation.py`
- `project_control/task_reports/TASK_REPORT_2026-08-29_DHF_PHENOTYPE_PREP.md`
