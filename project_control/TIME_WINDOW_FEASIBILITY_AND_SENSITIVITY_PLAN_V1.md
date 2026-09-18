# 时间窗可行性与敏感性分析方案 v1.1

更新时间：2026-09-04 Asia/Shanghai  
适用范围：MIMIC 实验室/血气覆盖诊断、主研究时间窗冻结和预设敏感性分析

## 1. 当前结论

主分析暂不改窗：

- `T0 = ICU intime`；
- 主要预测窗口为 `[T0,T12)`；
- 主要结局窗口为 `[T12,T60)`，或更早的 alive index-ICU discharge；
- Fine-Gray 为主模型，1 h person-period 为补充。

心超在 `[T0-24 h,T12)` 的 61 个可链接 study、9 个 T12 前 note 和 6 个 strict draft 只能说明 MIMIC-Echo 的链接/结果覆盖有限，不能证明 ICU 患者实际很少做心超，也不能单独支持把主窗口改为 24 h。:codex-annotation{index="1"}

`T0-T24 -> T24-T72` 预先保留为可行性/敏感性分析。它回答的是另一个问题：在获得更长的早期信息后，预测更晚的 48 h 风险是否改善；不能把它事后替换为主问题。

## 2. 审计窗口

已运行的分阶段 SQL：

- `sql_v3_2/audits/114A_audit_derived_bg_window_summary.sql`
- `sql_v3_2/audits/114B_audit_raw_labevents_bg_window_summary.sql`
- `sql_v3_2/audits/114C_audit_raw_vs_derived_discordance.sql`

同一批 5,555 个 modeling-base stay 并列审计：

| 窗口 | 解释 | 用途 |
|---|---|---|
| `icu_0_12` | `[intime, intime+12h)` | 主预测窗口 |
| `icu_0_24` | `[intime, intime+24h)` | 24 h 可行性/敏感性 |
| `icu_0_48` | `[intime, intime+48h)` | 覆盖上限诊断，不作为主预测方案 |
| `hospital_to_icu` | `[admittime, intime)` | ICU 前检验覆盖与时间定位 |
| `hospital_to_t12` | `[admittime, intime+12h)` | 入院至 T12 的总体覆盖 |

每个窗口同时比较：

1. `mimiciv_derived.bg` 的 blood-gas、lactate、pH、base excess；
2. 原始 `mimiciv_hosp.labevents` 对应项目（50802/50813/50820）和 Blood Gas 类别；
3. 首次记录时间；
4. 原始项目存在但 `derived.bg` 无记录的桥接异常标记。

## 3. 实测结果与设计决定

审计基数为 5,555 个 landmark-eligible stay。原始 `labevents` 在 ICU 0-12/0-24/0-48 h 的覆盖率分别为：乳酸 `52.40% / 57.53% / 61.48%`，pH `55.32% / 60.18% / 64.63%`，base excess `53.61% / 58.52% / 62.83%`。

`derived.bg` 在 ICU 0-12 h 的乳酸覆盖仅 42.50%，而原始表为 52.40%。逐 stay 对照显示 550 个 stay 只在原始表中有乳酸，derived-only 为 0；pH only 为 95，base excess only 为 1。主特征表已据此把乳酸改为原始 `itemid=50813`，重建后的有效乳酸比例为 `52.46%`。

**设计决定：主窗口维持 `[T0,T12)`。** 延长至 24 h 对三项关键检验的真实覆盖仅增加约 4.9-5.1 个百分点，不能抵消更晚的临床预警、T24 前死亡/出 ICU 所造成的 survivor/selection bias，以及必须重建 landmark 和竞争风险标签的代价。`[T0,T24) -> [T24,T72)` 仍是预设敏感性分析，只有在完整重建其风险集和结局后才能运行。

## 4. 如何解释审计结果

### A. 24/48 h 明显增加覆盖

说明早期检测并非人人在 ICU 入科后 12 h 内完成。主窗口仍保留，因为它提供更早的预警；24 h 作为预先规定的敏感性分析，并报告提前量损失。

### B. 原始 labevents 有记录，derived.bg 无记录

优先检查 itemid 映射、hadm_id/subject_id 连接、derived view 生成逻辑和 `charttime` 语义。此类记录不能直接归类为“临床未测”。

### C. 原始和 derived 都无记录

更符合真实未测或该患者未需要血气/乳酸检测。缺失可能是信息性测量缺失，不能简单解释为正常。

### D. hospital-to-ICU 有记录但 ICU 0-12 无记录

说明检查在急诊/病房阶段完成。它可用于描述和预设时间策略，但是否纳入主预测器必须遵守预测时点：若目标是 ICU 入科后实时预测，不能把 ICU 入科前结果静默混入 0-12h 变量；可另做“入院至 T12”敏感性模型。

## 5. 时间窗方案的统计边界

- 所有窗口的 landmark eligibility、死亡、alive ICU discharge 和行政删失规则必须分别重算；不能把 12 h 的结局表直接套到 24 h。
- 24 h 方案会排除 T24 前死亡/出 ICU 者，降低可预测性并可能引入 survivor/selection bias。
- 24 h 方案还可能纳入早期病程演变和治疗反应，临床上不再是最早期预警。
- 不得根据哪个窗口 AUC 更高再选择主窗口；主窗口在查看性能前固定。
- 若窗口延长，新的预测窗口应明确为 `[T24,T72)`，而非把 `[T12,T60)` 改名。

## 6. 变量层面的处理

- 生命体征覆盖高者保留并做常规 QC。
- 乳酸、pH、base excess 等测量性缺失先按 SQL 审计结果判断是否存在源表/连接问题。
- 真正缺测者若进入模型，主方案为训练折内多重插补；同时预设缺失指示器和删除高缺失生理域的敏感性分析。
- 心超不进入普通数值插补。它是选择性检查和表型验证层，保存 performed/result-available/abnormal-support 三层状态。

## 7. 本阶段通过条件

1. 114A-C 已成功运行，输出五个窗口的 stay-level 覆盖汇总；
2. 原始 `labevents` 与 `derived.bg` 的差异类别已计数，乳酸来源问题已在 090B 修复；
3. `[T0,T12)` 主窗口已保留；
4. `T0-T24 -> T24-T72` 已预设为完整重建风险集后的敏感性分析；
5. 下一步是最终 DHF 表型和事件数约束下的低维变量冻结，而不是继续追逐更长窗口。
