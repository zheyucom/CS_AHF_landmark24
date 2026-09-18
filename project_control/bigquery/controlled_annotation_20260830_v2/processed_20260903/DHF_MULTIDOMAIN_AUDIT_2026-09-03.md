# DHF 多域证据患者级审计

日期：2026-09-03

## 当前入组口径

成人 ICU 患者在 `[T0-24 h, T12)` 内具备可追溯 DHF 操作性表型；不要求 T0 入 ICU 时已经完成 DHF 诊断。所有证据必须早于 T12，T12 后信息不得回填入组。

院内严格主队列要求每例满足心超三级 QC：实际完成 TTE/TEE/心脏 POCUS 或床旁心超、结果在 T12 前可用、且结果支持心脏结构或功能异常；未检查/结果不可用者保留在全 ICU 选择性审计层，不能判为阴性。当前 MIMIC 本地结构化表仅能审计 TTE/TEE 检查发生；没有可用的完整心超结果或异常判定来源，因此当前 MIMIC 不能称为 `echo-confirmed`。

CXR 与胸部 CT 是互补肺部证据，主规则为 OR；`CXR AND CT` 仅作为极严格敏感性分析，不作为主纳入门槛，因为临床上并非每位患者都需要两种检查。模态分类只读取报告开头的检查名称/技术段；腹部、头部、脊柱等 CT，以及比较段中提到的 CT 不进入胸部 CT 层。

## 抽取覆盖与全量结果

106/107 原始报告按可解释检查类型初步分为：CXR 1434、胸部 CT 262、其他/未分类 2607。这只是模态规则审计，尚未等同人工影像诊断。

| 表型层 | stays | event | compete | censor | EPV/45 |
|---|---:|---:|---:|---:|---:|
| `broad_hf_anchor` | 5549 | 452 | 2934 | 2163 | 10.0444 |
| `radiology_cxr_available` | 425 | 53 | 217 | 155 | 1.1778 |
| `radiology_ct_available` | 55 | 9 | 23 | 23 | 0.2 |
| `radiology_cxr_or_ct_available` | 449 | 57 | 225 | 167 | 1.2667 |
| `radiology_cxr_and_ct_available` | 31 | 5 | 15 | 11 | 0.1111 |
| `radiology_cxr_or_ct_plus_iv_loop` | 20 | 5 | 6 | 9 | 0.1111 |
| `radiology_cxr_or_ct_plus_iv_loop_or_ntprobnp` | 189 | 28 | 97 | 64 | 0.6222 |
| `echo_result_plus_iv_loop` | 0 | 0 | 0 | 0 | None |
| `echo_or_lung_objective_plus_iv_loop` | 20 | 5 | 6 | 9 | 0.1111 |

所有层均为规则支持的 operational phenotype，不是全量人工确诊 DHF。

## 解释边界

1. BNP/NT-proBNP 只能作支持证据，不能单独 rule-in DHF；肾功能、年龄、房颤、肺部疾病、PE 和脓毒症均可影响数值。
2. HF ICD anchor 来自候选导出的 `hf_icd_any=1`；acute/acute-on-chronic 编码只作描述性审计，不等于 T12 前实际失代偿。最终表型需要临床/客观证据和管理/治疗域。
3. 影像文本 regex 仅经报告级分层人工验证，不能替代患者级金标准。
4. `echo_procedure_pre12_flag=1` 只说明做过 TTE/TEE；单独的结构化 LVEF 数值只能说明部分结果可用，不能直接说明存在异常。必须有可解析报告/结构化结果并单独完成 `echo_abnormal_support_pre12_flag` 判定。当前字段 `echo_result_available_pre12_flag` 与 `echo_abnormal_support_pre12_flag` 均不应由 procedure flag 推导。
5. 院内严格主队列为 `echo-supported DHF`；宽口径多域层仅作桥接/敏感性分析。应先冻结最终表型，再按事件数重新冻结低维预测器；当前 45 个预测器不可直接用于低事件层。
