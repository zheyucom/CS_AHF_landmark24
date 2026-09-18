# 任务报告：DHF 心超、胸片/CT 与 T12 入组口径统一

日期：2026-09-03  
状态：本轮方案已被用户后续决定更新；本文件中的“多域主队列、不强制心超”表述已被严格 `echo-supported DHF ICU cohort` 口径取代。请以 `TASK_REPORT_2026-09-03_DHF_ECHO_REQUIRED_INTERNAL_COHORT.md` 为当前版本。

## 本轮完成

1. 统一研究对象：成人首次 index ICU stay 中，在 `[T0-24 h,T12)` 内具有可时间追溯 DHF 操作性表型、能够到达 T12、且无 T12 前 overt shock proxy 的患者。
2. 明确不要求患者在 T0 入 ICU 时已经完成 DHF 诊断。`pre-T0 DHF` 仅作为严格敏感性分析，即全部入组证据都在 ICU 入科前发生。
3. 将心超分成三个不可混淆的状态：做过检查、结果可用、结果支持 DHF。只有第三种可支持严格 `echo-supported DHF` 亚组；procedure flag 不能代替异常结果。
4. 统一影像规则：主影像域为时间合规的 `CXR OR chest CT`；`CXR AND chest CT` 仅为严格敏感性分析；CT 未检查不判阴性。
5. 明确 ACS、CKD/AKI/ESRD、PE、肺炎/ARDS、COPD 不机械性全排。它们既可能是诱因/共病，也可能是替代解释；孤立替代诊断且无独立心衰证据进入排除敏感性分析。
6. 更新 study definition、项目 README、实时研究总览，并新增决策记录：
   `project_control/reports/2026-09-03_DHF_echo_required_decision.md`
7. 新增心超数据源盘点工具：
   `project_control/bigquery/111_discover_echo_sources.sh`
   `project_control/bigquery/111_echo_source_inventory.sql`

## 当前最重要的研究结论（历史版本，已被后续决定取代）

心超在临床证据等级上重于单独胸片，但“主队列必须人人完成心超”并不自动等于更科学。心超检查具有临床选择性；强制检查会选择出被医生认为需要心超的人群，并改变研究问题。当前本地 108 审计只有 462 例 TTE/TEE 操作记录、结构化 LVEF 为 0，因此暂不能声称已有全量心超异常结果。

本段是用户确认心超为严格主队列必要证据之前的历史双层设计，不再作为当前执行口径：

- 原主队列：多域 DHF 操作性表型；心超结果可用时优先采用；
- 原严格亚组：`echo-supported DHF`，必须有 T12 前异常心超结果。

当前执行口径已更新为：院内主队列必须满足心超三级 QC，并结合肺充血/临床失代偿和管理强化证据；全 ICU 候选宇宙仅用于选择性审计和桥接敏感性分析。

该建议已由用户确认并已经执行：研究对象命名为 `echo-supported DHF ICU cohort`，并报告心超完成率、结果可用率、异常支持率、检查选择性和未进入严格队列者的差异。

## 入组公式

```text
HF retrospective anchor
+ time-compliant clinical/objective decompensation evidence
+ time-compliant urgent management/treatment evidence
+ reached T12
+ no pre-T12 overt shock proxy
```

NT-proBNP、IV loop、最终 HF ICD 均不能单独确诊 DHF。NT-proBNP 只能是支持证据；IV loop 是管理证据而非病因证据；最终 HF ICD 是回顾性 anchor，不是实时诊断时间，也不能进入预测器。

## 数据与分析边界

- 入组证据可发生在 `[T0-24 h,T12)`；不要求全部发生在 ICU 入科前。
- 预测器只使用 `[T0,T12)` 信息。
- 结局只使用 `[T12,T60)` 的新循环支持升级/NEE 持续升高/ICU 内死亡。
- 主模型 Fine-Gray；1 h person-period 为补充。
- broad v3.3 的 `5,555/454` 和 legacy strict candidate 的 `650/66` 暂不作为新的 DHF 最终模型结果。

## 下一步

1. 用户在自己已登录的 Terminal 运行 `bash project_control/bigquery/111_discover_echo_sources.sh`，仅返回可见数据集/表名即可，不上传账号令牌。
2. 对发现的候选心超表执行 metadata schema 检查，确认 `subject_id/hadm_id/stay_id`、检查/采集时间、报告可用时间及 LVEF/RV/瓣膜/舒张功能字段。
3. 若存在可连接的心超结果，建立 `112` 时间审计查询并只抽取 `[T0-24 h,T12)` 结果；若不存在，保留主队列和 `echo-supported` 未形成状态，不伪造心超计数。
4. 在主窗口 109/110 结果完成后，按最终表型计数重算事件数和 EPV；主队列冻结后再锁定低维预测器和最终模型。

## 本轮未完成及原因

心超严格亚组尚未真正建立，不是因为 SQL 或分析流程未完成，而是当前工作区尚未核验到“心超结果内容 + 时间戳 + ICU 连接键”三项同时存在的数据源。该外部依赖需先由用户 Terminal 盘点 BigQuery 可见表；之后才能写出不会臆测表名/字段名的抽取 SQL。
