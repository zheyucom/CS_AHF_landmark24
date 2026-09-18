# 任务报告：院内 DHF 五张工作表构建（2026-09-14）

- 成人 index ICU 主表：8,385 行；已排除 9204020。
- 文书证据表：519,556 行；检查检验表：51,372,914 行；医嘱代理表：1,410,049 行。
- DHF 文书高召回表型筛查：8,276 行进入候选排序层。
- 当前标签仍为 `candidate_recall_only`/`pending_time_gated_review`，因为文书创建时间与报告时间不能自动替代全部 T0/T12 事件时间；原始来源和代理证据等级均已保留。

## 输出

- `project_control/internal_validation/20260914_workbench/encounter_icu.csv`
- `project_control/internal_validation/20260914_workbench/icu_note_evidence.csv`
- `project_control/internal_validation/20260914_workbench/diagnostic_evidence.csv`
- `project_control/internal_validation/20260914_workbench/treatment_order_proxy.csv`
- `project_control/internal_validation/20260914_workbench/dhf_phenotype_screen.csv`
- `project_control/internal_validation/20260914_workbench/workbench_qc.json`
