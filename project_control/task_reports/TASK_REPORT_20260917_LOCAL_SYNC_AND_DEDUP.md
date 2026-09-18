# 任务报告：本机正式目录同步与重复文件清理

日期：2026-09-17

## 1. 用户问题与本轮范围

用户要求将沙盒中的研究进展同步到本机 Codex，并指出不能保留同一内容的重复文件。本轮将本机正式目录确定为已有的 `project_control/`，合并新报告、建立本地 Codex 规则，并清理本轮误建的重复 `inbox/`。

## 2. 已验证事实

- 本机 Workspace：`CS_AHF_landmark24`。
- 本机项目根目录：`/Users/zheyu/Desktop/CS_AHF_landmark24`。
- 原有正式研究控制目录：`project_control/`。
- 原有正式总览：`project_control/RESEARCH_DASHBOARD.md`。
- 原有历史报告目录：`project_control/task_reports/`。
- 本机原先已存在大量研究合同、方法文件和历史任务报告；不能用新沙盒总览覆盖它们。

## 3. 已执行合并

新报告和规范已合并到：

```text
/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/task_reports/
```

新增：

- `README.md`
- `TASK_REPORT_TEMPLATE.md`
- `TASK_REPORT_20260917_VARIABLE_SELECTION_PROMPT_AUDIT.md`
- `TASK_REPORT_20260917_REPORTING_WORKFLOW.md`
- `TASK_REPORT_20260917_LOCAL_WORKSPACE_BRIDGE.md`

已更新：

- `project_control/RESEARCH_DASHBOARD.md`
- `project_control/README.md`
- 根目录 `AGENTS.md`

根目录 `AGENTS.md` 规定本机 Codex 以后以 `project_control/` 为唯一正式研究控制面，不另建平行 `inbox/` 或根目录 `task_reports/`。

## 4. 重复文件清理

本轮同步时误建的本机 `inbox/` 仅包含 6 个刚同步文件，已在逐项核对后删除。删除前已确认这些文件均已合并到 `project_control/`，没有删除原有研究资料。

## 5. 验证

五个新报告文件的 SHA-256 与沙盒源文件一致；本机总览和项目 README 已包含任务报告维护规则和索引；本机重复 `inbox/` 已不存在。

## 6. 后续规则

以后正式修改直接落在本机 `project_control/`；沙盒 `/workspace/inbox/` 仅作为上传附件和临时分析区。实质任务完成后，必须更新本机总览并在本机 `project_control/task_reports/` 新建报告。

