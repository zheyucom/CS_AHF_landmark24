# 本院 DHF 研究一 G1–G5 阶段报告

日期：2026-09-24

状态：`G1_G4_completed_G5_requires_protocol_decision_before_adjusted_association`

## 1. 本轮结论

研究一已按“数据范围 → 时间轴 → 操作性表型 → 结局 → 事件预算”运行到 G5。当前没有运行死亡回归、Fine–Gray、预测模型或基于结局的变量筛选。

最重要的结论是：

1. 主操作性表型总体队列为 773 人；严格 T12 风险集为 558 人；
2. 773 人中院内死亡 62 人，558 人严格 T12 风险集中院内死亡 16 人；
3. 16 人均在离开 index ICU 后死亡，因此 T12 后 48 小时 ICU 内死亡为 0；
4. 本院现有医嘱/管路可形成 81 个短期治疗升级代理事件，但没有 eMAR/泵速，不能称执行级结局；
5. 按预先登记的每 15 个死亡事件最多 1 个有效自由度，16 个死亡只允许 1 个自由度，未达到运行调整后多变量死亡关联模型所需的最低 3 个自由度；
6. 因此 G5 已阻止过拟合。正式 G7 前必须在“保留 T12 设计，仅做描述和预先指定粗关联”与“前瞻性修订为总体 T0、仅使用基线因素的院内死亡关联”之间作一次方案决定，不能根据哪个结果更好再选择。

## 2. G1：数据范围与日历完整性

状态：`PASS_SCOPE_LOCKED_WITH_KNOWN_LIMITATIONS`

- 来源候选：8,385；
- 研究适用范围限定为“本院接受床旁心超的成人 ICU 候选人群”；
- 当前结构化心超报告可见不等于临床未实施心超；
- 2024 年固定标记为 `incomplete_calendar_period`，不作年度趋势解释；
- 不声称连续完整五年、也不计算全 ICU 患病率。

运行目录：`project_control/runs/20260923_internal_stage1_g1_scope/`

## 3. G2：index ICU 时间轴

状态：`PASS_CHRONOLOGY_STRICT_LAYER_WITH_INFERRED_SENSITIVITY`

- 8,385 行患者/就诊唯一；
- 严格直接时间证据层 586 人，历史宽松层 626 人；
- 40 人只有“后续死亡但无明确 ICU 转出时间”的推断在位证据，不冒充直接证据；
- 后续分析采用较新的 `20260916_semantic_corrected`，不回退旧时间表。

运行目录：`project_control/runs/20260924_internal_stage1_g2_chronology/`

## 4. G3：A/B/C 操作性表型

状态：`PASS_ALGORITHMIC_RULE_FROZEN_CLINICAL_CALIBRATION_PENDING`

- A 心衰锚点 + B 失代偿证据 + C 客观/治疗支持；
- 主算法支持 773 人；严格客观支持 594 人；
- 主表型 + 严格 T12 时间层 558 人；宽松时间敏感性层 601 人；
- 290 例分层临床校准包已生成；
- 临床审核尚未完成，因此算法支持不能写成临床金标准。

运行目录：`project_control/runs/20260924_internal_stage1_g3_phenotype/`

## 5. G4：院内转归与短期代理结局

状态：`PASS_PRIMARY_HOSPITAL_DISPOSITION_SHORT_OUTCOME_PROXY_ONLY`

### 5.1 院内终末转归

| 人群 | 总数 | 院内死亡 | 存活出院 | unknown |
|---|---:|---:|---:|---:|
| 主表型总体队列 | 773 | 62 | 711 | 0 |
| 严格 T12 风险集 | 558 | 16 | 542 | 0 |

病案首页对 773 人覆盖完整。同一就诊 14 例存在空白/存活类别之间的历史版本变化，选择最新版后没有死亡与非死亡冲突。

### 5.2 T12 后 48 小时代理层

| 状态/组成 | n |
|---|---:|
| 代理目标事件 | 81 |
| └ 新药物类别连续医嘱代理 | 78 |
| └ IABP 管路代理 | 2 |
| └ 成对 ECMO 管路代理 | 1 |
| └ ICU 内死亡 | 0 |
| 活着离开 index ICU | 150 |
| 行政终止 | 273 |
| outcome unknown | 54 |

54 个 unknown 中 53 个是已有同类药物但无泵速/NEE，无法判断是否强化；1 个是非泵静脉滴注。该层只能称 `order/tube proxy`，不能称实际执行。

运行目录：`project_control/runs/20260924_internal_stage1_g4_outcomes/`

## 6. G5：事件预算硬门

状态：`STOP_ADJUSTED_T12_DEATH_MODEL_DF_LT_3`

| 端点 | 事件数 | 有效自由度上限 | 当前是否允许调整后多变量模型 |
|---|---:|---:|---|
| 严格 T12 风险集院内死亡 | 16 | 1 | 否 |
| 总体 773 人院内死亡（仅情境审计） | 62 | 4 | 数学上可行，但不是当前授权的关联人群 |
| 48 小时执行级复合结局 | 81 个代理阳性 | 5 | 否，执行级端点未冻结 |

运行目录：`project_control/runs/20260924_internal_stage1_g5_event_budget/`

## 7. 对 Open Evidence 流程的执行情况

已执行：

1. 锁定操作性表型；
2. 组建总体队列和 T12 嵌套风险集；
3. 审计病例组合、转归来源和数据质量；
4. 在查看因素效应前冻结结局和事件预算；
5. 保持研究一结果不反向选择 MIMIC 特征的防火墙。

仍待完成：

1. 290 例分层临床表型校准；
2. G6 描述性病例组合、照护路径、缺失与流程图；
3. G7 关联分析方案选择后再登记候选因素；
4. eMAR/泵速若可取得，重建本院执行级短期结局；若不可取得，短期结局永久作为代理/敏感性层。

## 8. 当前必须由研究负责人决定的一项问题

### 方案 A：保留已批准的 T12 主关联设计

- 研究一以表型验证、临床负担、照护路径、数据质量为主；
- 16 个死亡只做描述和极少数预先指定粗关联；
- 不运行调整后多变量死亡关联模型；
- 方法最保守，但“死亡相关因素”部分会很弱。

### 方案 B：在任何因素效应分析之前修订为总体 T0 关联设计（推荐）

- 以 773 人总体表型队列、T0 为时间零点，研究基线因素与院内死亡的关联；
- 仅使用 T0 已存在的基线因素，不使用 T0–T12 动态值，避免早死者无法获得 T12 信息造成的选择；
- 62 个死亡允许最多 4 个有效自由度，仍需低维、先验指定、收缩方法；
- T12 风险集继续用于研究二预测问题和本院 48 小时照护路径描述；
- 这是研究问题/时间零点的正式修订，必须在查看因素效应前登记，不能以结果优劣为理由。

推荐方案 B，因为研究一的教师要求是“本院 DHF 临床现状与死亡相关因素”，而研究二才是 T12 后 48 小时动态预测。两者分开时间零点更清晰，也能避免用仅 16 个死亡强行建模。

## 9. 本轮新文件

- `project_control/INTERNAL_DHF_OUTCOME_CONTRACT_V1.md`
- `project_control/build_internal_stage1_g4_outcomes.py`
- `project_control/tests/test_internal_stage1_g4_outcomes.py`
- `project_control/audit_internal_stage1_g5_event_budget.py`
- `project_control/tests/test_internal_stage1_g5_event_budget.py`
- `project_control/runs/20260924_internal_stage1_g4_outcomes/`
- `project_control/runs/20260924_internal_stage1_g5_event_budget/`

原始数据未修改，未运行正式模型，未修改开题材料。
