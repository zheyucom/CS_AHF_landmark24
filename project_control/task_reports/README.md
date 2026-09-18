# DHF 任务报告归档规范

## 目的

`task_reports/` 保存每次有实质研究结论、方法决策、文件变更或阶段交付的任务报告，避免研究进展依赖聊天上下文。任务报告是过程记录；`RESEARCH_DASHBOARD.md` 只维护当前状态、阻塞项、下一步和报告索引。

## 文件命名

```text
TASK_REPORT_YYYYMMDD_<TOPIC>.md
```

文件名使用英文大写和下划线，日期使用 UTC/项目记录日期。报告生成后原则上不覆盖；若结论被修正，在新报告中写明“旧结论 → 新结论 → 修正原因”。

## 何时生成

以下情况生成独立报告：

- 用户提出新的研究问题或要求方法审计；
- 形成、修改或确认研究定义、队列、变量、结局或统计方法；
- 完成一次数据处理、质量控制、复核或模型运行；
- 修改研究文件、合同、字典、运行登记或总览；
- 发现旧数字、旧口径或旧结论需要纠正。

仅有礼貌确认或不改变研究状态的重复问答，不单独生成报告，可并入最近一份报告。

## 固定报告结构

1. 用户问题与本轮范围
2. 使用的文件、版本和数据状态
3. 已验证事实与证据
4. 判断与影响
5. 新增或确认的研究决策
6. 未决问题、阻塞项和假设
7. 下一步动作
8. 本轮修改文件
9. 可重复性信息（脚本、版本、seed、输入指纹；适用时填写）

可直接复制的空白模板见 [TASK_REPORT_TEMPLATE.md](TASK_REPORT_TEMPLATE.md)。

## 当前归档

- [2026-09-17 变量筛选与 Prompt 审计](TASK_REPORT_20260917_VARIABLE_SELECTION_PROMPT_AUDIT.md)
- [2026-09-17 任务报告机制与文件整理](TASK_REPORT_20260917_REPORTING_WORKFLOW.md)
- [2026-09-17 沙盒与本机 Workspace 桥接确认](TASK_REPORT_20260917_LOCAL_WORKSPACE_BRIDGE.md)
- [2026-09-17 本机正式目录同步与重复文件清理](TASK_REPORT_20260917_LOCAL_SYNC_AND_DEDUP.md)
- [2026-09-17 近期文献与 MIMIC 清洗方法复核](TASK_REPORT_20260917_RECENT_LITERATURE_AND_MIMIC_CLEANING.md)
- [空白任务报告模板](TASK_REPORT_TEMPLATE.md)
- [2026-09-18 本机 Git 初始化与安全边界配置](TASK_REPORT_20260918_GIT_SETUP.md)
- [2026-09-18 本地 Git 优先决策说明](TASK_REPORT_20260918_GIT_LOCAL_ONLY_DECISION.md)
- [2026-09-18 本地 Git 初始提交收尾](TASK_REPORT_20260918_GIT_BASELINE_COMMIT.md)
