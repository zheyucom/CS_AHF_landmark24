# project_control 文件整理记录（2026-09-24）

本轮只删除确定不属于研究证据的冗余文件，没有删除患者级提取、SQL、质量门、模型脚本或任务报告。

## 已删除

- 6 个 macOS `.DS_Store` 元数据文件；
- `RESEARCH_DASHBOARD.md.orig`；
- `RESEARCH_DASHBOARD.md.rej.orig`；
- `TASK_REPORT_20260921_MIMIC_DHF_ALGORITHMIC_COHORT_FREEZE_V1.md.orig`；
- `project_control/` 下所有 Python `__pycache__` 缓存目录。

## 保留原则

- `project_control/bigquery/` 中的 SQL、独立验证 SQL、运行日志保留；
- `project_control/runs/` 中的模型输出和质量证据保留在本机，但受 `.gitignore` 保护，不提交 GitHub；
- 患者级 CSV、eMAR 提取材料和本院数据不做删除；
- 历史任务报告保留，便于追溯研究决策，不按文件名简单判定为冗余。

清理后复核：`project_control/` 内不再存在 `.DS_Store`、`.orig`、`.rej.orig` 或 `__pycache__`。
