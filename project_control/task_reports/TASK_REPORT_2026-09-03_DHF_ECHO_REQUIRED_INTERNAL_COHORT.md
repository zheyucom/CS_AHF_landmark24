# 任务报告：院内严格心超支持型 DHF 队列口径冻结

日期：2026-09-03  
状态：本轮规则与本地审计已完成；等待 MIMIC/院内心超结果源和样例数据后继续执行

## 1. 用户确认后的当前决定

院内外部验证主队列确定为：

> **`echo-supported DHF ICU cohort identified by T12`**

即成人 index ICU 患者，在 `T12 = ICU 入科后 12 h` 前能够被时间追溯识别为 DHF，且每例必须满足心超三级条件：

1. 实际完成 TTE、TEE、心脏 POCUS 或床旁心超；
2. 检查结果在 `T12` 前可用；
3. 结果支持至少一项心脏结构或功能异常。

心超之外仍必须有：

- HF 背景/回顾性 HF anchor；
- 肺充血或临床失代偿证据；
- 同一时间窗内实际治疗或管理强化证据。

证据窗口为 `[T0-24 h,T12)`。不要求患者在 `T0` 入 ICU 时已经完成 DHF 诊断；可以在 ICU 早期完成心超或出现其他证据，但不能使用 T12 后信息回填入组。

## 2. 心超字段必须如何解释

以下三种状态必须分开：

| 状态 | 含义 | 是否足够进入严格主队列 |
|---|---|---:|
| `echo_performed` | 检查确实完成 | 否 |
| `echo_result_available` | 在 T12 前有可读取结果 | 否 |
| `echo_abnormal_support` | 结果支持结构/功能异常 | 是，且前两项也必须为 1 |

仅有医嘱、procedure 记录、检查名称或“床旁心超已做”而没有实际结果，均不能进入严格主队列。结果阴性、缺失和无法解析必须分别记录；未做检查不能编码为阴性。

## 3. CXR、胸部 CT 与替代诊断

胸片和胸部 CT 是肺部证据域，不能替代心超，也不能单独确诊 DHF。主肺部审计使用时间合规的 `CXR OR chest CT` 明确肺水肿/肺血管充血；`CXR AND CT` 仅作敏感性分析，不把 CT 缺失当阴性。

PE、ACS/AMI、AKI/CKD/ESRD、肺炎/ARDS、COPD 和房颤不机械全部排除：它们可能是诱因或共病。需要单独记录替代解释；“孤立替代诊断且没有 HF/心超/临床失代偿证据”可作为高特异性排除敏感性层。

## 4. 当前已完成

- 已更新院内详细提数规范、最小字段清单、信息科简版申请和字段映射 CSV。
- 已将 `RESEARCH_DASHBOARD.md`、`README.md`、Study Definition 和 DHF NLP/时序协议统一到当前严格院内口径。
- 已将旧任务报告中的“不强制心超”标记为历史口径，避免继续误用。
- 已完成 5,549 个有效候选 stay 的患者级第一版审计：452 event、2,934 competing、2,163 censor。
- 已审计 462 例 TTE/TEE 操作记录，但当前结构化可用 LVEF 为 0；因此 MIMIC 当前不能称为 echo-confirmed DHF。
- 已完成 300 条第一位影像标注；60 条为同标注者重复，不能作为独立 inter-rater reliability。
- 已重新运行患者级多域审计，确认当前报告中的 `echo_procedure` 仅代表检查发生；已将“结构化 LVEF 可用”与“心超异常支持”分开，避免把一个 LVEF 数值误写成 DHF 证据。
- 已新增 `project_control/bigquery/112_echo_result_audit_template.sql`，用于在确认真实心超结果表 schema 后审计 `[T0-24 h,T12)` 的检查时间、结果可用时间和异常支持状态。

## 5. 当前真正阻塞

1. **MIMIC 心超结果源**：需要确认 BigQuery 可见数据集中是否有可连接的心超报告/结构化结果，而不是只有 procedure 记录。
2. **院内心超样例**：需要 20-50 条脱敏心超样例和字段字典，至少含检查类型、检查时间、结果可用时间、LVEF/结构功能结论和结果状态。
3. **最终模型队列**：严格队列人数和事件数未知前，不能按旧 5,555 或 650 例直接锁定最终特征数和模型。

这不是当前 DHF 规则或本地审计逻辑故障，而是心超结果数据源尚未交付/核验。Codex 环境的 BigQuery 元数据盘点未返回可用表清单；请在用户自己的已登录 Terminal 执行，避免把本地 OAuth 网络状态误认为账号授权结果：

```bash
bash project_control/bigquery/111_discover_echo_sources.sh
```

该命令只盘点当前账号可见的数据集和表名，不读取临床行。发现候选表后，再运行 `bq show --format=prettyjson PROJECT:DATASET.TABLE`，把输出中的表名和字段 schema 发回即可，不要发送 token 或原始患者文本。若仍无候选结果，应优先核对 MIMIC-IV-Note 与 MIMIC-IV core 的授权范围；不要把 `procedureevents` 当作心超结果。

## 6. 下一步与估计投入

| 顺序 | 工作 | 主动工时 | 依赖 |
|---:|---|---:|---|
| 1 | 盘点 MIMIC 心超数据源并确认 schema | 0.5-1 h | 用户 Terminal 权限 |
| 2 | 建立心超时间审计与三级 QC 查询 | 2-4 h | 表名和字段确定 |
| 3 | 院内 20-50 条样例字段/单位/时间审计 | 1-3 h | 信息科样例 |
| 4 | 形成严格主队列及宽口径桥接层计数 | 2-4 h | MIMIC/院内结果可用 |
| 5 | 按严格队列事件数冻结低维 manifest | 1-2 h | 队列冻结 |
| 6 | 重跑 Fine-Gray、person-period 和预设敏感性 | 4-8 h | manifest 冻结 |

## 7. 当前不可写成论文最终结果的内容

`5,555/454`、`650/66`、462 例心超操作记录和 `425/55/449/31` 影像审计数字，均不能写成最终 echo-supported DHF 主队列结果。它们只能作为历史开发、可行性或选择性审计数字；严格主队列计数必须来自心超结果三级 QC 后的版本化运行。

## 8. 相关入口

- 总入口：`project_control/RESEARCH_DASHBOARD.md`
- 项目 README：`project_control/README.md`
- 院内详细规格：`project_control/INTERNAL_HOSPITAL_EXTRACTION_SPEC_DHF_EXTERNAL_VALIDATION_V1.md`
- 最小字段：`project_control/EXTERNAL_VALIDATION_MINIMUM_FIELDS.md`
- 心超源盘点：`project_control/bigquery/111_discover_echo_sources.sh`
- 心超结果审计模板：`project_control/bigquery/112_echo_result_audit_template.sql`
- 当前决策记录：`project_control/reports/2026-09-03_DHF_echo_required_decision.md`

## 9. 本轮验证记录

- `build_dhf_multidomain_audit.py` 已重新运行并通过 Python 语法检查。
- 患者级输出为 5,549 个唯一 `stay_id`；结局字段仍保持 `452 event + 2,934 compete + 2,163 censor`。
- 当前 MIMIC 的 `echo_result_plus_iv_loop` 严格层为 0，不代表患者心超阴性，而是当前结果源不足以判定心超异常支持。
- Codex 环境执行 `111_discover_echo_sources.sh` 未获得可用表清单，且命令在 Google API 元数据请求阶段无结果返回；这一步需在用户已登录 Terminal 执行。
