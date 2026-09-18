# CS_AHF 周报

周报日期：2026-08-27
覆盖周期：2026-08-21 至 2026-08-27
下次组会：2026-09-02

## 一句话结论

本周最重要的进展是把研究主线从旧的固定 48 h 二分类预测，修正为带 alive ICU discharge 竞争事件的 T12 landmark 竞争风险预测；v3.3 结局和 person-period QC 已完成，下一步进入无泄露预测变量重建与最终建模。

## 追加审计（2026-08-28）

099 AHF 表型审计发现，当前 5,555 例不能整体表述为临床确诊 AHF：严格 pre-T0 口径为 `650/66`，最近 24 h 口径为 `378/34`。因此最终论文若保留“AHF”命名，应先在 650 例队列上重建低维模型；5,555 例暂作为 broad operational comparison，不把原有 45-feature 性能直接当作严格 AHF 最终结果。

审计报告：`project_control/reports/2026-08-28_ahf_screening_and_literature_review.md`

## 本周完成

| 完成项 | 证据路径 | 是否可写入论文最终结果 |
|---|---|---|
| 分析单位切换为每 patient index hospitalization 内首次 ICU stay | `project_control/runs/20260827_v3_2_index_adm/` | 待冻结后可写 |
| v3.2 AHF-by-T12 候选队列重建 | `project_control/runs/20260827_v3_2_index_adm/reports/` | 待冻结后可写 |
| 主结局标签审计 | `project_control/runs/20260827_v3_2_outcome_label_audit/` | 可作为方法学审计证据 |
| 随访/竞争 ICU 出科审计 | `project_control/runs/20260827_v3_2_outcome_label_audit/` | 可作为 estimand 修正证据 |
| v3.3 strict 主标签重写 | `sql_v3_2/audits/096_create_strict_main_label_v33.sql` | 待冻结后可写 |
| landmark eligibility reconciliation | `project_control/runs/20260827_v3_3_person_period_reconciled/` | 待冻结后可写 |
| 1 h person-period v2 构建和 QC | `project_control/runs/20260827_v3_3_person_period_reconciled/` | 待冻结后可写 |

## 当前阶段

当前位于：队列与结局定义完成后、最终建模前。

- 阶段：v3.3 eligible cohort + competing-risk outcome 已完成 QC。
- 本周状态：已明确不能把 early ICU discharge 当作无事件；主分析应使用竞争风险。
- 下一阶段入口条件：重建 0-12 h 无泄露预测变量表，并完成与三态标签/person-period 的连接 QC。

## 关键数字

| 指标 | 数值 | 来源 |
|---|---:|---|
| v3.2 候选队列 | 5,564 stays | `20260827_v3_2_index_adm` |
| v3.2 旧定义事件 | 511 | `20260827_v3_2_index_adm` |
| T12 前/时死亡排除 | 9 | `20260827_v3_3_person_period_reconciled` |
| v3.3 eligible stays | 5,555 | `098 landmark reconciliation` |
| v3.3 主事件 | 454 | `098 landmark reconciliation` |
| alive ICU discharge 竞争事件 | 2,935 | `098 landmark reconciliation` |
| T60 行政删失 | 2,166 | `098 landmark reconciliation` |
| person-period 行数 | 176,525 | `097 person-period v2` |
| early sepsis stays/events | 1,498 / 151 | `097 QC6 sepsis stratum` |
| non-sepsis stays/events | 4,057 / 303 | `097 QC6 sepsis stratum` |

## 阻塞问题与预计投入

| 问题 | 为什么卡住 | 下一动作 | 主动工时 | 计算/等待 | 风险 |
|---|---|---|---:|---:|---|
| 无泄露预测变量表未重建 | 没有最终建模输入 | 重建 v3.3 eligible cohort 的 0-12 h features，排除资格和结局变量 | 4-8 h | 数十分钟到数小时 | 中 |
| Fine-Gray 嵌套验证未实现 | 主模型还没有可报告性能 | R 中完成分层折、折内预处理、CIF 48h AUC/Brier/校准 | 8-16 h | 数小时至过夜 | 中高 |
| IPCW/complete60 敏感性未跑 | 还不能说明固定窗口结论是否稳健 | 折内 IPCW + complete60 对照 | 6-12 h | 数小时 | 中 |
| pre-T0 AHF v3.2 敏感性未重算 | 严格入 ICU 前 AHF 方案缺少最终数字 | 重跑 pre-T0 队列并接 v3.3 标签 | 2-4 h | 中 | 中 |
| Riley 外部验证样本量未估计 | 本院数据量需求不清 | 按最终参数数和事件数估算 | 2-4 h | 低 | 低中 |

## 下周计划

1. 完成 v3.3 eligible cohort 的无泄露预测变量表。
2. 完成 stay-level 标签、person-period、预测变量三者连接 QC。
3. 跑通 Fine-Gray 主模型最小闭环，先拿到 baseline CIF、AUC/Brier/校准。
4. 准备 IPCW 和 complete60 敏感性分析脚本。
5. 清理旧文档，把 `2,424/334` 和旧模型结果明确降级为历史探索。
6. 与导师确认严格 pre-T0 AHF（650/66）是否作为论文主队列。

## 需要导师决策

1. 主文是否采用 Fine-Gray 作为唯一主模型，1 h person-period 模型作为补充。
2. ICU 内死亡是否继续放入 composite 主事件，还是单独作为 secondary/competing 结构展示。
3. pre-T0 AHF 是否作为敏感性分析已足够，还是导师希望它成为主队列。
4. 本院外部验证最少需要准备哪些时间字段和药物剂量字段。

## 周三组会 3-5 分钟口头稿

老师好，本周我主要完成了队列和结局定义的关键修正。原来直接把 T12 后 48 小时是否恶化做二分类，会把很多提前活着离开 ICU 的患者当作无事件，但审计发现完整观察到 T60 的患者只有约 45%，因此这会造成明显的观察偏倚。

我现在把主估计目标改为：T12 到 T60，或更早活着离开 index ICU 之前，在 ICU 内发生血流动力学恶化的累计发生风险；活着离开 ICU 作为竞争事件。新的 v3.3 eligible cohort 是 5,555 例，其中主事件 454 例，竞争出 ICU 2,935 例，T60 仍在 ICU 且无事件 2,166 例。person-period 表也已经建好，共 176,525 行，并通过时间和终止状态 QC。

当前还没有进入最终模型结果，因为下一步必须重建 T12 前无泄露预测变量表，不能沿用旧的 2,424/334 模型结果。下周计划是先完成预测变量表和连接 QC，再跑 Fine-Gray 竞争风险模型的嵌套验证，并准备 IPCW 和 complete60 敏感性分析。

需要请老师判断的是：主文是否以 Fine-Gray 作为唯一主模型，person-period 模型作为补充；以及 ICU 内死亡是否继续放入 composite 主事件。

## 更新动作

- [x] 已同步 `project_control/RESEARCH_DASHBOARD.md`
- [x] 已追加 2026-08-27 任务报告
- [x] 已确认旧结果没有被写成最终结果
