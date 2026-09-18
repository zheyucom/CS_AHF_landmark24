# CS_AHF 本地 Codex 研究维护规则

本项目正式研究资料的唯一根目录是 `project_control/`，不要在项目根目录或其他位置另建一套平行的研究总览、任务报告或变量合同。

## 每次开始工作

先读取：

1. `project_control/RESEARCH_DASHBOARD.md`
2. `project_control/task_reports/README.md`
3. 与当前任务最相关的最新任务报告
4. 当前生效的研究合同、统计方案、变量字典和运行登记

## 文件职责

- `project_control/RESEARCH_DASHBOARD.md`：唯一当前状态入口，只维护当前结论、阻塞项、下一步和报告索引。
- `project_control/task_reports/`：追加式历史任务报告，不覆盖旧报告。
- `project_control/` 下的合同、统计方案、变量字典和运行登记：正式可执行研究定义。
- `CS_AHF_hemodynamic_deterioration_ml_project/`：代码、数据、模型和输出，不复制研究总览。

## 每次实质任务结束时

涉及研究结论、队列、变量、结局、统计方法、数据处理、质量控制、模型运行或文件修改时，必须：

1. 新建 `project_control/task_reports/TASK_REPORT_YYYY-MM-DD_<TOPIC>.md`；
2. 更新 `project_control/RESEARCH_DASHBOARD.md` 的当前状态、报告索引和更新日志；
3. 不覆盖历史报告；结论改变时写明“旧结论 → 新结论 → 修正原因”；
4. 未执行、未验证或有冲突的内容标为 `pending`、`blocked`、`not_run` 或 `assumption`；
5. 结束时列出修改文件的完整相对路径、验证结果和 Git 状态。

简单确认或不改变研究状态的重复问答不必单独建报告。

## 研究结果保护

- 不把候选人数写成最终队列人数。
- 不把 AI 预审核写成临床金标准。
- 不把历史可行性模型性能写成最终结果。
- 不把医嘱代理写成实际执行记录。
- 不因结果不理想事后修改纳排标准、时间窗、变量或阈值。
- 所有论文数字必须来自同一冻结运行。

## 目录防重复

不要创建平行的 `inbox/RESEARCH_DASHBOARD.md` 或根目录 `task_reports/`。若收到上传附件，先作为临时输入处理；正式结论和报告统一归档到 `project_control/`。

