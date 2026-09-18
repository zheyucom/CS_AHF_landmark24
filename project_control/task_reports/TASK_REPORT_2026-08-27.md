# TASK_REPORT — 2026-08-27 会话工作简报

> 接续 `TASK_REPORT_2026-08-26.md`。新对话先读 08-26 报告 + 本报告 + `.workbuddy-ai/memory/2026-08-27.md`。

## 本轮背景（接续）

08-26 已完成 P0 修复：特征白名单净化（11 个 A 类资格变量 + 21 个 charlson B 类）、early sepsis 时间修复（antibiotic/culture<T12）、ahf_time_confirmed_by_t12 落实，产出 v3.1（主队列 1,126/142，全队列 4,282/411）。

用户随后引用导师/审稿反馈（5 项清单），确认新方向：**AHF ICU 患者 T12 landmark 血流动力学恶化预测，early sepsis 预设亚组，pre-T0 严格敏感性**。我逐项核对并给出整合执行顺序（结局审计前置、嵌套验证、删失、Riley 样本量、旧结果降级等 11 步）。

## 本轮做了什么

### 分析单位切换（用户选 (a)）—— 唯一完成的任务
- 决策：分析单位 = 每位患者 index hospitalization（首次符合 AHF 条件的住院）内首次 ICU stay，每 patient 一行（无相关性）。
- 实现：新建 `sql_v3_2/`（schema `study_ahf_v3_2`），010 改"每住院首次 ICU"（base 85,242），061B 加 index-adm 去重。
- **结果（比 v3.1 更好）**：
  | 口径 | 主队列(sepsis) | 事件 | 率 | 全队列 | 事件 | 率 |
  |---|---|---|---|---|---|---|
  | v3.1 subject 首次 ICU | 1,126 | 142 | 12.61% | 4,282 | 411 | 9.60% |
  | **v3.2 index admission** | **1,498** | **174** | **11.62%** | **5,564** | **511** | **9.18%** |
- 原因：index-adm 口径让"首次进 ICU 非 AHF、后续住院才是 AHF"的患者也能入组，既更正确又更大样本。

## 当前队列状态（v3.2 冻结中）

- 主队列候选：AHF by-T12 全队列 **5,564 / 511 (9.18%)**；sepsis 亚组 **1,498 / 174 (11.62%)**。
- pre-T0 敏感性队列：**尚未在 v3.2 基础上重算**。

## 遗留任务（按当前优先级）

6. 主结局标签审计（simultaneous agent count / 30-60min persistence / phenylephrine 场景）**已完成**：见 `project_control/runs/20260827_v3_2_outcome_label_audit/`。
7. **先解决删失/竞争 ICU 出科策略**：仅 45.0% 患者完整观察至 60h，直接二分类会把早期 ICU 出科混为无事件。
8. 重建无泄露建模数据集（基于 v3.2 队列 + 白名单排除 A_REMOVE/B_SENSITIVITY）。
9. 全流程嵌套验证 + 校准 + 已确定的删失/竞争事件敏感性。
10. Riley 外部验证样本量 + 2,424/334 全文档降级为历史结果。

## 新完成：任务 6 主结局标签审计（2026-08-27）

- SQL：`sql_v3_2/audits/094_create_outcome_label_audit.sql`；导出：`094_export_outcome_label_audit.sql`。
- 审计表：`study_ahf_v3_2.audit_094_outcome_label_v1`，`5,564` stay；逐 stay CSV 已归档。
- 标签时间一致性：当前主结局 `511/511` 都有对应时间，且无非事件被赋予时间。
- 支持组件 `365` 例：`21 (5.8%)` 未出现真实并用升级，`17 (4.7%)` 新增支持不足 30 分钟，phenylephrine-only `35 (9.6%)`。
- NEE >=0.05 组件 `106` 例：`12 (11.3%)` 不足 30 分钟；持续时间中位数 `5.03h`。
- 严格 30 分钟敏感性结局（真实并用 + 持续 >=30 min 支持，或持续 >=30 min NEE，或死亡）=`477/5,564 (8.57%)`；严格 60 分钟=`465 (8.36%)`。说明短暂用药不是主要性能瓶颈。
- **关键发现**：完整 60h ICU 观察 `2,504/5,564 (45.0%)`；早期出 ICU 者事件率 `4.38%` 对比完整者 `15.06%`，普通固定窗口二分类存在重大信息性删失/竞争出科风险。因此 v3.2 仍不可冻结建模，先完成删失策略。

## 新完成：任务 7 前置审计——随访/竞争 ICU 出科（2026-08-27）

- SQL：`sql_v3_2/audits/095_create_followup_censoring_audit.sql`；审计表：`study_ahf_v3_2.audit_095_followup_censoring_v1`。
- 提前离开 index ICU 的 `3,060` 例中：住院出院早于 T60 `334`，T60 时仍在院但不在 ICU `2,598`，T60 前 ICU 再入 `116`（各状态优先级可能重叠），离 ICU 后 T60 内死亡 `15`。
- `2,926` 早期离 ICU无主结局事件患者不能无条件标为“48h 无事件”：取决于目标是“ICU 内恶化”还是“患者任何住院位置的恶化”。
- **需要导师/研究者确认的估计目标**：推荐主分析明确为“12h 后至 min(T60,活着离开 index ICU) 的 ICU 级血流动力学恶化累计发生”，活着离 ICU作竞争事件；另以完整 T60 ICU 二分类（`2,504/377`）做敏感性。若坚持“患者未来 48h 任意地点恶化”，必须扩展结局提取到转出 ICU 后和后续 ICU 入科，当前表不能直接支持。

## 关键决策记录

- 主队列口径：by-T12 全队列（5,564/511）作主，sepsis 作亚组，pre-T0 作敏感性（导师最终判断采纳此结构）。
- 分析单位：(a) index admission，每 patient 一行。
- 需补充：pre-T0 队列在 v3.2 上的重算（任务 3 的对应物，未做）。

## 新完成：landmark eligibility reconciliation + person-period v2（2026-08-27）

- 新增 `sql_v3_2/audits/098_reconcile_landmark_eligibility_v33.sql`，建立 `study_ahf_v3_2.audit_098_landmark_eligibility_v33_v1` 与 `study_ahf_v3_2.model_098_strict_label_v33_v1`。
- 明确排除 9 例 T12 前死亡病例；这 9 例不能进入 T12 landmark 风险集。
- 修正后风险集：5,555 例；event 454（escalation 374 + ICU death 80）；compete 2,935；censor 2,166。
- 新增 `sql_v3_2/modeling/097_create_person_period_v33_reconciled.sql`，建立 `study_ahf_v3_2.model_097_person_period_v33_v2`。
- 新增 `sql_v3_2/audits/097_export_person_period_qc_reconciled.sql`；结果归档至 `project_control/runs/20260827_v3_3_person_period_reconciled/`。
- person-period 结果：176,525 行、5,555 stays；每 stay 恰好 1 个终止行。
- 时间 QC 全通过：无 T12 前区间、无 T60 后区间、无非正区间、无超过 1h 区间、无多重终止标记。
- sepsis 分层：1,498 stays / 151 events（10.08%）；非 sepsis 4,057 stays / 303 events（7.47%）。
- 额外边界核查：无 event at/after T60、无 eligible event at/before T12、无 compete at/before T12。

### 当前状态

098 eligibility 与 097 person-period v2 已完成并通过 QC；旧版 096/097 v1 保留为历史版本，未覆盖。下一步是基于 v3.2 合格队列重建 T12 前无泄露预测变量并按 stay 连接到 v2，然后实施折内特征选择、插补、删失/竞争风险建模与验证。

## 新完成：研究总览与周报机制（2026-08-27 22:30）

用户要求明确当前研究进展、主要查看文件、实时更新方式、全局研究方案、当前阶段/卡点/预计投入，并检查每周二周报安排。

已完成：
- 新建 `project_control/RESEARCH_DASHBOARD.md` 作为日常主入口，集中维护研究方案总纲、当前状态、已完成成果、可靠关键数字、当前工作台、阻塞问题矩阵、下一步 7 天计划、待导师决定、历史结果边界和最新周报入口。
- 新建 `project_control/reports/weekly/WEEKLY_REPORT_TEMPLATE.md`，固定周报结构：一句话结论、本周完成、当前阶段、关键数字及证据路径、阻塞问题与预计投入、下周计划、导师决策问题、周三组会 3-5 分钟口头稿。
- 新建首份周报 `project_control/reports/weekly/2026-08-27_weekly_report.md`，用于本周三组会前参考。
- 更新根目录 `README.md`，顶部加入研究总览入口和当前状态快照，并把旧 `2,424/334`、`outputs/`、`outputs_v2/`、旧模型性能明确降级为历史/诊断材料。
- 更新 `project_control/README.md`，将更新时间改为 2026-08-27，阶段 2 改为进行中，主模型改为 Fine-Gray competing-risk model，并写入 v3.3 当前可靠数字与真实卡点。
- 更新已有自动化 `automation`：名称改为 `CS_AHF 每周组会周报`，时间保留每周二 16:00；prompt 已细化为读取总览、任务报告、memory、过去 7 天 run/QC，更新总览并生成不覆盖历史的周报。

当前给用户的核心回答：
- 最主要看 `project_control/RESEARCH_DASHBOARD.md`。
- 它会在每次实质研究任务结束后同步更新，并由每周二 16:00 自动周报兜底更新。
- “实时”指任务完成和周报时更新，不是每条 SQL 或模型运行过程逐秒更新。
- 当前研究位于：v3.3 结局/person-period QC 完成后，最终无泄露预测变量重建和主模型嵌套验证前。

下一步研究任务：
1. 重建 v3.3 eligible cohort 的 ICU 入科 0-12 h 无泄露预测变量表。
2. 与 stay-level 三态标签和 person-period v2 连接并完成 QC。
3. 实现 Fine-Gray 嵌套验证和 48 h CIF AUC/Brier/校准。
4. 完成 IPCW、complete60、phenylephrine、60min 和 pre-T0 AHF 敏感性分析。

## 新完成：特征冻结与外部验证字段清单（2026-08-27 22:55）

用户补充了 4 个坑并确认：
- 主文采用 Fine-Gray 作为唯一主模型；
- 1 h person-period 模型作为补充；
- ICU 内死亡放入 composite 主事件；
- pre-T0 AHF 作为严格敏感性分析。

我进一步把剩余问题收束成可执行合同：
- 新建 `project_control/FEATURE_FREEZE_V33.md`，明确 AHF 资格变量、pre12 overt CS 变量、outcome-derived support 聚合、ID/time/label columns 进黑名单；主模型采用约 30-45 个预设候选特征，宽特征 elastic-net 只做敏感性。
- 新建 `project_control/EXTERNAL_VALIDATION_MINIMUM_FIELDS.md`，把院内外部验证最少需要的字段分成 cohort/time anchor、AHF 复刻、0-12 h predictors、结局字段和 early sepsis 亚组字段五类。

外部验证第 4 点的简明答案：
- 不是要求院内一开始给齐所有 070/080/081 特征；
- 而是先保证能复刻 `cohort -> predictor window -> outcome window -> competing event` 的时间逻辑；
- 最少要有 `admittime/intime/outtime/dischtime/deathtime`、药物给药开始/结束时间与剂量、NT-proBNP 与关键实验室时间戳和数值、以及 ICU 死亡/出科/再入 ICU 结构；
- 如果先只能给样例，优先给 20-50 行脱敏样例 + 字段字典 + 时间/剂量单位说明。

当前尚未解决：
- 还没有真正开始重建 v3.3 的无泄露预测变量表；
- 外部验证的院内字段映射尚未拿到。

## 新完成：090 compact feature pipeline（本次接续任务）

新增并执行：

- `sql_v3_2/modeling/090A_create_modeling_base_v33.sql`
- `sql_v3_2/modeling/090B_create_compact_predictors_v33.sql`
- `sql_v3_2/modeling/090C_create_modeling_input_v33.sql`
- `sql_v3_2/audits/090D_export_compact_feature_qc_v33.sql`
- `sql_v3_2/run_090_compact_features_v33.sh`

归档：`project_control/runs/20260828_v3_3_compact_features/`（目录名沿用既有 run 标签）。

结果：

- 090A base、090B predictors、090C Fine-Gray input 均为 5,555 行、5,555 个唯一 stay，无重复 stay。
- 主事件 454；alive ICU discharge 竞争事件 2,935；T60 行政删失 2,166；与 098/097 三态结构一致。
- 45 个预设预测器与 manifest 一致；列级黑名单扫描未发现 outcome、时间锚点、资格变量或随访变量混入。
- 标签、预测器和 person-period 三表每一个 stay 都成功连接；每 stay 恰有一个 terminal person-period row。
- 初版 `bg_bicarbonate_min`（99.28% 缺失）和 `pf_ratio_min`（72.31% 缺失）已从紧凑集移除，改用 `dbp_min` 和 `modified_shock_index_max`。
- 当前主要缺失：lactate 57.44%，pH/base excess 约46%，INR 29.36%；主模型将折内中位数插补，缺失指示器仅作为预设敏感性，避免主模型从 45 个自由度无声扩张。

当前下一步：

1. 运行 `analysis_r/090_finegray_baseline_v33.R`，完成 5 折 event×sepsis 分层 OOF 预测。
2. 输出并审阅 48 h CIF AUC、Brier、十分位校准和变量方向。
3. 再实现 1 h person-period landmark survival 补充模型及既定敏感性分析。
