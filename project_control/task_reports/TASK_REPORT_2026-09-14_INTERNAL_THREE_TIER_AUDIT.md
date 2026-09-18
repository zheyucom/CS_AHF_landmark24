# 任务报告：院内 DHF 三级表型审计（2026-09-14）

## 本次完成

- 男女数据合并后的成人 index ICU 分母：8,385（女 2,842，男 5,543）；17 岁患者 9204020 已排除。
- 报告时间窗口 `[T0-24 h,T12)` 内床旁心超：完成 2,519，结果可用 2,517，关键词异常支持 draft 2,475。
- 三个心超状态同时满足的 `echo_supported_dhf_draft`：2,475；这不是 DHF 确诊人数。
- 45 例语义优先抽样：retain candidate 8、not supported 37、未抽审 8340。
- 事件、存活出 ICU 竞争事件和删失：尚未从现有院内文书、护理与医嘱重建；不是要求重复补提已有数据。医嘱可作为执行代理，但不能视为泵速时序。

## 交付文件

- `project_control/internal_validation/20260912/internal_dhf_three_tier_audit_20260914.csv`：逐 stay 三级审计表。
- `project_control/internal_validation/20260912/internal_dhf_three_tier_audit_qc_20260914.json`：计数、定义、文献依据和缺失原因。

## 冻结边界

本表为旧T0/床旁专项审计，不是最终DHF人数。最新全量episode时间重建和表型预审核见internal_validation/20260915_time_gated/，当前入口见RESEARCH_DASHBOARD.md。按用户确认使用现有原始资料及医嘱代理，随后对代理时间做敏感性更新。
