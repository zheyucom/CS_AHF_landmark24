# TASK_REPORT — 2026-08-26 会话工作简报

> 用途：供后续新对话恢复上下文。新会话开始时，先读 `.workbuddy-ai/memory/2026-08-26.md` 与本文档。

## 本次会话做了什么（按顺序）

### 1. 研究方案讨论：主队列口径与时间边界
- 用户提出把人群改为"首次入 ICU + 住院到入 ICU 前确诊 AHF"，用 0-12h 预测 12-60h 恶化。
- 结论（有 8-25 v4/v4.1/v4.2 实测数据支撑）：**不建议把"入 ICU 前确诊"提升为主门槛**，三个原因：
  1. MIMIC-IV `diagnoses_icd` 无时间戳，"确诊时间"不可得，只能用 IV 利尿剂/NT-proBNP/ED 诊断作代理；
  2. 急诊直入 ICU 者 pre-T0 窗口极短，被系统性排除（选择偏倚）；事件率从 13.78% 降到 7.8-10.4%；
  3. 样本塌缩：2,424 → 562（admission→T0 证据）→ 359/119（严格），事件 28-57 个，EPV 不足。
- 文献对照：DeVore 2014/2016、Rahman 2022、Hu 2024、Gao 2026、Zhang 2024 均不以"入 ICU 前确诊"为纳入条件。
- **决策：主队列保持 by-T12，pre-T0 确诊作为敏感性/分层分析**（与 v2.1/v3 设计一致）。

### 2. T_qualify（AHF 资格确认时间）审计 —— 已跑
- 新增 `sql_v3/audits/092_create_ahf_qualify_time_audit.sql`，已在 `study_ahf_v3` 上运行。
- 主队列 2,424 分层（执行证据 = eMAR/NT-proBNP 首条时间戳）：pre_t0 516 例(21.3%, 事件率10.08%) / t0_6h 358例(14.8%, 15.36%) / 6_12h 93例(3.8%, 20.43%) / **icd_only 1,457例(60.1%, 14.28%)**。
- 关键发现：**事件率随 T_qualify 后移单调上升**（10%→15%→20%），资格确认时间本身与结局相关；**60.1% 主队列无 T12 前时间戳 AHF 证据**。
- 产出：`study_ahf_v3.audit_092_ahf_qualify_time_v1` + `audit_092_ahf_qualify_summary_v1`；`project_control/runs/20260826_ahf_qualify_audit/`（SQL log + 2 CSV）。

### 3. 研究问题漏洞全景梳理（P0 排序）
| 优先级 | 漏洞 | 状态 |
|---|---|---|
| P0-1 | 特征-资格泄漏：`hf_icd_primary_seq`（频率1.00 排第1）等 11 个资格变量混入特征 | 本次已审计，待模型重跑 |
| P0-2 | early sepsis 时间泄漏：062A 旧版未加 antibiotic/culture < T12（记录 25.78% 泄漏） | **本次已修复** |
| P0-3 | `ahf_time_confirmed_by_t12_flag` 未落实，icd_only 60% | **本次已落实** |
| P1 | 结局 simultaneous agent count / 30-60min persistence | 未做 |
| P1 | 50 次重复验证非嵌套（特征选择循环外加载） | 未修 |
| P1 | 信息性删失（60h 前转出事件率 6.06% vs 完整 19.41%） | 未处理 |
| P2 | Charlson 基于本次住院 ICD、分析单位、TP/FP 盲法复核 | 待定 |

### 4. 特征白名单净化（P0-1）—— 已审计
- 新增 `scripts/audit_feature_whitelist.py`，对 `model_080g_modeling_dataset_v2` 全部 318 列分类：
  - **A_REMOVE（11 个，强制移除）**：hf_icd_primary_seq、hf_icd_seq_eq1_flag、hf_icd_seq_2_5_flag、acute_hf_icd_flag、hf_icd_seq_le5、iv_loop_rx_early12_flag、ntprobnp_ge300_early12_flag、ahf_evidence_score_primary_12h、suspected_infection_before_icu_flag、suspected_infection_icu_0_6h_flag、suspected_infection_icu_6_12h_flag
  - **B_SENSITIVITY（21 个，降级敏感性）**：early_sepsis12_max_sofa_score、early_sepsis12_suspected_infection_hour、early_sepsis12_sofa_hour、全部 charlson_*（基于本次住院最终 ICD，不可移植）
  - **C_KEEP（272 个）** 安全特征；ID_LABEL 14 个（不建模）
- 产出：`project_control/runs/20260826_ahf_qualify_audit/feature_whitelist_v3_1.csv`

### 5. early sepsis 时间修复 + v3.1 队列重跑（P0-2 + P0-3）—— 已完成
- 新建 `sql_v3_1/` 管线（独立 schema `study_ahf_v3_1`，不覆盖 v3）：
  - 061A 增加 ahf_retro_confirmed_flag / ahf_time_confirmed_by_t12_flag / ahf_pre_icu_confirmed_flag；
  - 061B 主队列门槛改为 `hf_icd_seq_le5 AND ahf_retro_confirmed AND ahf_time_confirmed_by_t12`；
  - 062A 主定义强制 `antibiotic_time < T12 AND culture_time < T12`，输出 first_antibiotic/culture_time 审计字段。
- 13 个 SQL（001→064）全部运行成功。**结果对比**：
  | 版本 | n | 事件 | 事件率 |
  |---|---|---|---|
  | v3（旧） | 2,424 | 334 | 13.78% |
  | **v3.1（时间确认）** | **1,126** | **142** | **12.61%** |
  - cohort flow：adult_first_icu 65,366 → hf_icd_candidate 14,877 → strict_ahf_time_confirmed 5,000 → landmark12_riskset 4,282 → **main_cohort 1,126**。
  - sepsis 时间泄漏影响：4,282 riskset 中 428 例（占 loose 定义的 27.5%）因 antibiotic/culture ≥ T12 被剔除。
- 产出：`sql_v3_1/executable/*.sql`、`sql_v3_1/run_v3_1.sh`、`sql_v3_1/audits/095_v3_vs_v31_cohort_compare.sql`、`project_control/runs/20260826_v3_1_time_confirmed/`（日志 + reports/v3_vs_v31_main_compare.csv）。

## 当前研究状态（v3.1 冻结中）

- 主队列 v3.1：**1,126 例、142 事件（12.61%）**——时间可用性已达标（AHF 证据 <T12 + sepsis 抗生素/培养 <T12）。
- 下一步（未执行）：
  1. **按白名单重跑建模特征**（070A/C/D2/E/F/G、080A/G 需基于 v3.1 队列重建，排除 A_REMOVE，B_SENSITIVITY 单独做敏感性）；
  2. 结局审计（simultaneous agent count、30/60min persistence、phenylephrine 场景）；
  3. 全流程嵌套验证（修 50 次重复验证非嵌套问题）；
  4. 删失/竞争事件处理；
  5. T_qualify 分层报告 + 论文方法段落（用户已确认 by-T12 口径）。

## 约定（用户要求）

- **每次任务完成后生成 TASK_REPORT**（本文档模板），放 `project_control/task_reports/TASK_REPORT_YYYY-MM-DD.md`，同时更新 `.workbuddy-ai/memory/` 日志。
- 建议新对话开头先读：`.workbuddy-ai/memory/2026-08-26.md` + 最近的 TASK_REPORT。
