# 任务报告：DHF 心超优先与 T12 入组口径确认

日期：2026-09-03

## 本轮完成

1. 将研究定义更新为 v5.5，明确主研究对象为成人首次 index ICU stay 中，至 `T12 = ICU intime + 12 h` 时已可时间追溯识别的 DHF 操作性表型患者。
2. 入组证据窗口固定为 `[T0-24 h, T12)`；患者不必在 `T0` 入 ICU 时已经确诊 DHF。全部证据发生于 `T0` 前的 `pre-T0 DHF` 仅作严格敏感性分析。
3. 明确心超为最高优先级的客观心脏证据。最终表型须提取和时间审计心超结果内容，不能以 TTE/TEE 操作记录代替异常结果。
4. 收紧影像规则：单独 CXR、单独胸部 CT、单独 BNP/NT-proBNP 或单独利尿剂均不能确诊 DHF 或进入最终 DHF 主模型。CXR 或 CT 只构成肺充血证据域，必须与 HF anchor、可时间定位的失代偿佐证和治疗/管理强化组合使用。
5. 保留 `CXR OR CT` 作为肺部影像域，而不要求 CXR 与 CT 同时阳性。双检查属于受诊断不确定性和共病驱动的选择性检查；当前严格 pre-T0 审计中 CXR AND CT 仅 31 stays、5 events，不能支持预测模型。它是高特异性敏感性分析，不是主队列门槛。
6. 建立 `echo-supported DHF` 严格确证层：T12 前异常心超结果，加肺充血/临床失代偿，加治疗强化。若最终主队列也被导师要求人人具备异常心超，研究对象必须重命名为 `echo-supported DHF ICU cohort`，并报告检查选择性和样本损失。

## BigQuery 执行状态

- 已核验本机存在 `gcloud`/`bq`，当前活动账户为 `zheyu.sy@gmail.com`，默认 billing project 为 `project-9386bb9f-de39-47eb-886`。
- 已实际运行只读元数据脚本 `project_control/bigquery/111_discover_echo_sources.sh`。命令在刷新 Google OAuth access token 时无响应约 132 秒后被中止；堆栈定位于对 Google token endpoint 的网络连接。
- 因此，本轮未查询、导出或修改任何 BigQuery 临床行数据。该阻塞是 Codex 执行环境到 Google API 的网络连接，不能通过扩大数据集权限或提供账号凭据解决。

## 当前不能跳过的门槛

在最终 DHF 队列、事件数/EPV 和预测器 manifest 冻结前，必须完成：

1. 在可连通 Google API 的终端盘点可访问的独立心超结果源，确认连接键、检查时间、报告可用时间及 LVEF/左右室功能/瓣膜/舒张功能字段。
2. 运行心超时间审计，仅接受 `[T0-24 h, T12)` 内已可用的结果；缺失结果保留 `unknown`，不能当阴性。
3. 运行 109/110 主窗口放射科查询，获得同一窗口的 CXR/CT 证据与报告可见时间。
4. 以 HF anchor + 失代偿佐证组合 + 管理强化重建队列，分别报告 `echo-supported`、`echo + lung imaging`、radiology/clinical operational phenotype 的人数、事件数和 EPV。

## 文件更新

- `study_definition/study_definition_v5_pre_t0_dhf_landmark12.md`：升级为 v5.5。
- `project_control/RESEARCH_DASHBOARD.md`：更新最终冻结门槛与队列证据边界。
- `project_control/reports/2026-09-03_DHF_echo_required_decision.md`：补充“心超必要”与“对每位患者强制检查”之间的区别。

