# DHF 放射科报告人工标注模板（中英对照）

## 你需要做什么 / What you do

你不需要翻译整份英文报告，也不需要自己编写 NLP 程序。逐条阅读 `report_text`，先填写 `final_report_scope` 和 `final_modality`，再填写 `reviewer_id`、`final_congestion_label`、`final_alternative_explanation_label` 和 `final_comments`。标准标签保留英文值，便于后续 Python/R 统计。

`final_report_available_pre_t0_label` 和 `final_report_available_by_t12_label` 可以根据时间字段自动填写；`adjudication_label` 暂时留空，供后续裁决使用。

## 使用范围

本模板用于验证 106 规则筛查，不能用于查看预测结局或训练/评估最终风险模型。标注者只看到报告文本和检查/入库时间，不看到 `final_state`、任何 T12 后治疗信息或模型预测。

## 标注表字段

从 `dhf_radiology_raw_v2` 导出被抽样报告时，建立受控工作表，至少包含：

```text
annotation_id,stay_id,note_id,charttime,storetime,report_text,
rule_positive_congestion,rule_uncertainty,rule_negation,
reviewer_id,final_report_scope,final_modality,
final_congestion_label,final_alternative_explanation_label,
final_report_available_pre_t0_label,final_report_available_by_t12_label,
final_comments,adjudication_label,review_status
```

`report_text` 仅在本地受控标注表中保存，不写入公开论文工件或普通项目报告。

本轮抽样来自放射科报告集合，可能包含胸片、胸部 CT 以及非胸部检查。所有报告都先确认检查范围；只有胸部/胸腔影像报告的 `FINDINGS` 或 `IMPRESSION` 用于肺充血判读。胸片和胸部 CT 都属于可判读的胸部影像，二者不要求同时完成。非胸部检查不应标为 `no_congestion`，应标 `indeterminate`，替代解释标 `unclear`，并在备注中写明“非胸部检查，不用于肺充血判断”。病史或检查目的中出现 CHF/pulmonary edema，不能代替胸部影像所见。

胸部 CT 还要记录是否提到肺栓塞、右心负荷、肺炎、ARDS、胸腔积液或其他并存/替代诊断。CT 未检查不能编码为 CT 阴性；“胸片 + CT 均阳性”只用于敏感性分析，不是主纳入条件。

### 先确认报告范围 / modality，再判读肺充血

`final_report_scope` 允许：

| 值 | 含义 |
|---|---|
| `chest_radiology` | 报告主体是胸片、胸部 CT 或其他明确胸部影像，可判读肺部充血 |
| `non_chest_radiology` | 下肢静脉超声、头颅/腹部/脊柱/四肢 CT 等非胸部检查，不适用肺充血标签 |
| `mixed_or_unclear` | 同一报告混合多个部位，或不能确认胸部部分是否可独立判读 |
| `unknown` | 原文不足以确认检查范围；应在备注说明 |

`final_modality` 允许：`cxr`、`chest_ct`、`other_chest`、`non_chest`、`mixed_or_unclear`、`unknown`。胸片可包括 portable AP、AP/PA 或胸部正侧位；胸部 CT 可包括 CT chest、CTA chest、CT pulmonary angiography 等明确覆盖胸部的检查。若 CT 仅检查头、腹部、骨盆、四肢或其他非胸部部位，则标 `non_chest`。

## 主标签：congestion_label

| 值 / Value | 中文判断 / English meaning |
|---|---|
| `definite_congestion` | 报告明确支持肺水肿、间质/肺泡性水肿或肺血管充血 |
| `possible_congestion` | 报告使用可能、疑似、不能排除等不确定语言 |
| `no_congestion` | 明确否定肺水肿/肺充血 / Explicitly negative for edema or congestion |
| `indeterminate` | 未提及该概念、资料不足、技术限制、术后改变、非胸部检查或无法可靠判断 / Not mentioned or not reliably classifiable |

胸腔积液、心影增大不能独立标为 `definite_congestion`；只有报告同时明确充血/水肿时才支持该主标签。报告没有提到肺充血不等于“明确无充血”，应标 `indeterminate`，除非报告有明确否定语句。

## 辅助标签

- `alternative_explanation_label`：`none_apparent`、`pneumonia_ards`、`pulmonary_embolism_or_rv_strain`、`postoperative_or_technical`、`other`、`unclear`。胸部 CT 若提示 PE 或右心负荷，使用 `pulmonary_embolism_or_rv_strain`；若同时提示肺水肿和肺炎，记录并存解释，不要因共存而自动删去充血标签。
- `report_available_pre_t0_label`：按 `storetime < intime` 独立判断；`storetime` 缺失标 `unknown`。

## 抽样和复核

先按 protocol 从 definite-positive、negated/uncertain 和 no-hit 三层各抽 100 条。至少 20% 随机双盲复核；分歧交由临床裁决者，并在 `adjudication_label` 中保留最终标签。范围和 modality 也应纳入复核。任何规则修改后，保留独立复验样本。报告级肺充血 PPV 的分母只包括 `final_report_scope=chest_radiology` 且 `final_modality` 为胸部影像的记录；非胸部报告不进入该分母。

## 最简单的判读顺序 / Decision order

```text
0. `final_report_scope` 是否为胸部影像？如果不是，肺充血标签只能为 `indeterminate`。
1. 胸部影像的所见或印象明确写 pulmonary edema / vascular congestion / interstitial edema？
   -> definite_congestion
2. 有 may / possible / cannot exclude / suspicious for？
   -> possible_congestion
3. 明确写 no edema / no congestion / lungs clear？
   -> no_congestion
4. 以上都没有，或技术/术后改变导致无法判断？
   -> indeterminate
```

遇到不确定病例，标 `indeterminate`，在 `comments` 写出卡点，不要强行判定。

## 关于 Codex 协助标注

Codex 可以帮助逐条理解英文、给出第一版建议标签、解释否定词和不确定词，并整理分歧清单；这些属于 AI-assisted pre-annotation，不能直接当作临床金标准。最省力且仍可答辩的方案是：Codex 完成第一版草标，你或导师复核不确定/冲突病例，另一位临床人员独立复核至少 60 条。若完全没有临床复核，应把影像结果降级为 weak-label/rule-based sensitivity，不称为人工确认的 DHF 表型。
