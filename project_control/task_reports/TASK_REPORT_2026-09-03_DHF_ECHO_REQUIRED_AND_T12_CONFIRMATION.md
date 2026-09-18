# 任务报告：严格 DHF 必须有心超证据与 T12 入组口径冻结

日期：2026-09-03  
状态：已完成本轮方案更新；最终模型仍受 MIMIC 心超结果源阻塞

## 本轮结论

严格研究对象冻结为：

> 成人首次 index ICU stay 中，在 `T12 = ICU 入科后 12 h` 前，具有可追溯 `echo-supported DHF` 操作性表型的患者。

严格入组必须同时满足：

```text
adult index ICU stay
AND reached T12
AND HF retrospective anchor
AND T12 前实际完成 TTE / TEE / cardiac POCUS / bedside cardiac ultrasound
AND 心超结果在 T12 前可获得
AND 心超结果支持至少一项心脏结构或功能异常
AND T12 前有肺充血或临床失代偿证据
AND T12 前有紧急治疗/管理强化证据
AND T0-T12 尚无预设 overt shock proxy
```

“完成心超”不是二元的简单操作记录，而是三级证据链：

1. `echo_performed`：实际检查完成，不接受单独医嘱；
2. `echo_result_available`：报告/结构化结果在 T12 前可用；
3. `echo_abnormal_support`：原始结果支持心脏结构或功能异常。

仅有 TTE/TEE/床旁心超操作记录、没有结果，不能进入严格队列。未做、结果缺失、结果不可解析、明确正常必须分别编码；未找到记录不等于心超阴性，也不等于临床排除 DHF。

## 对“ICU-DHF 肯定做心超”的校准

临床上，疑似急性/失代偿性心衰通常应尽早进行超声评估，重症患者也常使用床旁心超。但“指南建议尽早评估”不能被改写成“MIMIC 中每位 ICU-DHF 患者必然完成并留下可用心超结果”。检查可能未执行、未进入可查询结构化表、只有图像无报告、报告时间无法回溯，或患者因其他原因进入 ICU 后才接受心超。

因此，本研究采取两个同时成立的原则：

- **严格确证层**：没有 T12 前可解析且支持异常的心超，不称为 `echo-supported DHF`，也不进入严格主模型；
- **选择性审计层**：仍提取完整成年 ICU 候选宇宙，报告心超完成率、结果可用率、异常支持率及严格队列与未入组者的差异，避免把检查选择偏倚隐藏起来。

这会使研究对象更窄，但诊断表型更可信；代价是样本量和事件数可能明显下降，最终必须重新计算事件数、缺失率、有效参数数和 EPV。

## T0 与 T12 的最终关系

不要求患者在 `T0` 入 ICU 的瞬间已经完成 DHF 诊断。允许心超、影像、病历和治疗证据在 ICU 早期逐步形成，但所有入组证据必须满足：

```text
T0 - 24 h <= evidence_time < T12
```

患者必须活着且仍在 index ICU 到达 T12。`pre-T0 DHF`（全部证据发生在 T0 前）继续作为敏感性分析，而不是主队列。这个设计保留了“ICU 早期识别 DHF”的研究问题，同时避免把 T12 后信息回填到入组。

## HFpEF 判定补充

心超异常不能只看 LVEF。LVEF >=50% 不代表没有 HFpEF；应保留并审计舒张功能/充盈压、左房扩大、左室肥厚、肺动脉压、右心功能、显著瓣膜病等结果。若这些结果均明确正常且没有其他心脏结构/功能异常支持，则不进入严格 `echo-supported` 层；若结果缺失，则标记为 `unknown/not assessable`，不能编码为阴性。

## 当前数据状态与阻塞

- 本地 MIMIC 审计：5,549 个有效候选，462 个 TTE/TEE 操作记录，结构化 LVEF 可用 0；这只能证明部分检查发生，不能证明 DHF 或异常心超。
- 当前 MIMIC-Note/本地已安装表中尚未获得可用心超报告结果源；因此不能报告 MIMIC 严格 `echo-supported DHF` 队列人数，也不能把现有 5,555/650 模型结果称为最终模型结果。
- 院内提取规格已要求 ICU 候选宇宙、TTE/TEE/POCUS/床旁心超、检查时间、结果可见时间、原始结果和三级 flag；字段规格已更新为 v1.2。

## 下一步

1. 在用户已登录的 Terminal 运行 `project_control/bigquery/111_discover_echo_sources.sh`，确认 MIMIC 是否存在可用心超结果表；只反馈候选表名与 schema，不上传凭据或原始文本。
2. 若找到结果源，按 `project_control/bigquery/112_echo_result_audit_template.sql` 映射并审计 `[T0-24 h,T12)` 的检查时间、结果可用时间和异常支持。
3. 若 MIMIC 只有 procedure-level 记录，停止使用“echo-confirmed”表述；将开发与院内验证口径重新决策为同一可实现层级，不能宽口径开发后直接声称严格外部验证。
4. 严格表型冻结后，重新计算事件数与 EPV，再冻结低维特征 manifest，运行 Fine-Gray 主模型和 1 h person-period 补充模型。

## 方案依据

- McDonagh TA, et al. 2021 ESC Guidelines for the diagnosis and treatment of acute and chronic heart failure. *Eur Heart J*. 2021;42:3599-3726. doi:10.1093/eurheartj/ehab368.
- Kober L, Adamo M, et al. *2026 ESC Guidelines for the management of heart failure*. *Eur Heart J*. 2026. doi:10.1093/eurheartj/ehag100.
- Bozkurt B, et al. Universal Definition and Classification of Heart Failure. *J Card Fail*. 2021;27:387-413. doi:10.1016/j.cardfail.2021.02.029.

这些文献支持“症状/体征、客观心脏异常、充血证据和临床管理整合”的原则；本项目的时间窗、字段和三级心超 flag 是针对 MIMIC/院内数据可追溯性的预先操作化，不应表述为某一篇文献原样规定的筛选公式。
