# DHF 影像标注中文快速开始

当前 CSV 中的放射科报告是 MIMIC-IV 原始英文。你不需要翻译报告，也不需要学习 NLP；只需按固定规则填写标签。标准标签保留英文值，因为后续 Python/R 程序按这些值读取。

注意：这批“放射科报告”不全是胸片，可能包含胸部 CT、头颅 CT、腹部/肾脏/血管超声等。先确认检查范围，再判读肺充血。只有胸部/胸腔影像的 `FINDINGS` 或 `IMPRESSION` 可以用于肺充血判断；胸片和胸部 CT/CTA 均可作为肺部充血候选证据，二者不要求同时完成。非胸部检查在 `final_comments` 写“非胸部检查，不用于肺充血判断”，主标签填 `indeterminate`，替代解释填 `unclear`，绝不能填 `no_congestion`。

## 每行填写什么

填写 `reviewer_id`、`final_report_scope`、`final_modality`、`final_congestion_label`、`final_alternative_explanation_label` 和 `final_comments`。建议 `reviewer_id` 使用 `human_1`。时间可用性字段由时间字段自动判断，`adjudication_label` 先留空。

| 检查类型 | `final_report_scope` | `final_modality` |
|---|---|---|
| 胸片（portable AP、AP/PA、正侧位） | `chest_radiology` | `cxr` |
| 胸部 CT、CTA chest、CTPA | `chest_radiology` | `chest_ct` |
| 其他明确胸部影像 | `chest_radiology` | `other_chest` |
| 非胸部 CT/超声/介入导管定位等 | `non_chest_radiology` | `non_chest` |
| 检查范围混合或无法确认 | `mixed_or_unclear` 或 `unknown` | 对应 `mixed_or_unclear` 或 `unknown` |

## 肺充血标签

| 报告核心意思 | 填写值 |
|---|---|
| `pulmonary edema`、`interstitial edema`、`vascular congestion`，且为肯定描述 | `definite_congestion` |
| `may represent edema`、`possible edema`、`cannot exclude congestion`、`suspicious for edema` | `possible_congestion` |
| `no pulmonary edema`、`no vascular congestion`、`lungs are clear` | `no_congestion` |
| 只提到胸腔积液/心影增大；未提及肺充血；技术差；术后改变难以判断 | `indeterminate` |

胸腔积液、心影增大、肺不张或双肺底模糊影，不能单独证明肺充血。

## 替代解释

`none_apparent` = 无明显替代解释；`pneumonia_ards` = 肺炎或 ARDS；`pulmonary_embolism_or_rv_strain` = PE 或右心负荷；`postoperative_or_technical` = 术后或技术因素；`other` = 其他；`unclear` = 无法判断。

有替代解释不等于一定排除 DHF，只是单独记录供后续分层和裁决。胸部 CT 若提示 PE/右心负荷，填 `pulmonary_embolism_or_rv_strain`；若提示肺炎/ARDS，填 `pneumonia_ards`。这些可以与肺充血并存，不能因共存而自动排除 DHF。

## 三个例子

| 英文报告意思 | 主标签 | comments 示例 |
|---|---|---|
| `Mild pulmonary vascular congestion and interstitial edema.` | `definite_congestion` | 明确写肺血管充血和间质性水肿 |
| `Opacities may represent atelectasis or edema.` | `possible_congestion` | 水肿为可能解释，同时有肺不张替代解释 |
| `Small bilateral pleural effusions. No pulmonary edema.` | `no_congestion` | 有胸腔积液，但明确否定肺水肿 |

## 是否必须由你独自完成

不必由你独自完成 300 条。Codex 可以先给出 AI-assisted 草标和理由，你复核无法判断或有争议的报告；但最终论文若声称“影像支持的 DHF 表型”，仍应保留临床人员复核和一部分独立复核。完全跳过人工复核时，只能将影像部分写成规则筛查/弱标签敏感性分析。
