# 任务报告：MIMIC 时间窗与血气/乳酸可行性审计

日期：2026-09-04  
状态：审计、特征来源修正与重建 QC 已完成；主研究窗口不修改

## 本轮完成

- 新增并运行 `114A/114B/114C` 分阶段审计 SQL；原一体化 `114` 仅保留为概念稿，避免重复扫描 1.58 亿行 `labevents`。
- 新增 `project_control/TIME_WINDOW_FEASIBILITY_AND_SENSITIVITY_PLAN_V1.md`。
- 已完成 ICU 0-12/0-24/0-48 h、住院入院至 ICU、住院入院至 T12 五个窗口的实测覆盖审计。
- 已核对 `mimiciv_derived.bg` 与原始 `mimiciv_hosp.labevents`，避免把衍生表筛选遗漏误判为临床未测。
- 将 090B 中 `lactate_max` 和 `lactate_delta` 的来源改为原始 `labevents itemid=50813`，并重建 090B、090C 和 090D QC；三表均为 5,555 个唯一 stay，黑名单扫描为空、45 项 manifest 完整匹配。

## 当前判断

- Echo 的 61/9/6 结果是覆盖与结果可用性审计，不足以单独改变主窗口。
- `[T0,T12)` 仍是主预测窗口；`[T0,T24) -> [T24,T72)` 保留为预设敏感性/可行性分析。
- 原始 `labevents` 的 0-12 h 覆盖：乳酸 52.40%、pH 55.32%、base excess 53.61%；到 24 h 分别仅升至 57.53%、60.18%、58.52%。
- 主窗内原始乳酸 2,914 个 stay，derived 乳酸 2,364 个；550 个 stay 仅原始表有记录。乳酸改源后，最终 090D 缺失率由旧版 57.44% 降至 `47.54%`（2,641/5,555）。
- pH/base excess 在主输入中仍约 46.34%/46.35% 缺失，属于后续折内缺失处理的对象，而不是改时间窗的理由。
- 115 测量机制审计显示主事件组的乳酸/pH/base excess 有效测量率为 67.84%/65.64%/65.64%，而 alive ICU discharge 组为 45.66%/46.92%/46.88%。因此 MICE + 缺失指示器是预设必做敏感性，不能只使用中位数填补。
- 完成 `094_finegray_mice_sensitivity_v33.R` 的严格嵌套 MICE 可行性运行：5 折外层、每折 `m=5`、`maxit=5`，插补器仅使用 T12 前预测变量；验证折不读取结局，只从完成的训练折 PMM 供体插补。五折均无 MICE logged event，48 h OOF 的 MICE-only AUC/Brier 为 `0.7533/0.06533`，MICE+缺失指示器为 `0.7566/0.06490`。

## 未完成与预计投入

- 未完成：按最终 DHF 表型的有效事件数冻结低维主模型变量和插补分支，约 2-4 h。
- 未完成：完整重建 `T24-T72` 风险集后才执行时间窗敏感性，约 4-8 h；不作为当前主模型替代。
- 未完成：最终 DHF 表型冻结后，以该冻结输入重跑 `m=20` 的嵌套 MICE、MICE+缺失指示、中位数及 complete-case 诊断分支，并输出最终 Fine-Gray，约 1-2 个工作日；刚完成的 `m=5` 是可行性敏感性，不能报告为最终性能。

产物：`sql_v3_2/audits/115_audit_measurement_availability_by_outcome_v33.sql` 和 `project_control/runs/20260904_lab_measurement_outcome_audit/reports/115_measurement_availability_by_final_state.csv`。
