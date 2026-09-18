# DHF 主窗口多域证据审计

## 设计边界

候选集为 5,549 名 HF ICD anchor ICU stays。入组证据窗口为 `[T0-24 h, T12)`；预测变量严格为 `[T0, T12)`；结局窗口为 `[T12, T60)`。影像、ICD、BNP 和利尿剂字段均不可作为预测器。

本审计用 CXR/胸部 CT 明确肺淤血规则、T12 前报告可见性及治疗支持生成操作性表型。它不是人工 adjudication，也不能将单项 BNP、单张影像、ICD 或心超检查流程记录称作 DHF 确诊。

## 数据完整性

患者级汇总显示窗口内应有 7,828 份报告；当前审计得到 7,828 份，缺 0 份，完整导出标志为 `1`。完整导出已通过行数与键唯一性校验。模态规则计数：CXR 1,534，胸部 CT 315，其他/未分类 5,979；影像阳性仍是自动筛查层，不能替代人工临床 adjudication。

## 结局与 EPV

| 表型层 | stays | event | compete | censor | EPV/45 |
|---|---:|---:|---:|---:|---:|
| `all_hf_icd_candidates` | 5549 | 452 | 2934 | 2163 | 10.0444 |
| `any_radiology_available_by_t12` | 3542 | 315 | 1884 | 1343 | 7.0 |
| `definite_cxr_or_ct_congestion_available_by_t12` | 625 | 78 | 303 | 244 | 1.7333 |
| `definite_cxr_or_ct_congestion_plus_iv_loop` | 4 | 1 | 2 | 1 | 0.0222 |
| `definite_cxr_or_ct_congestion_plus_iv_loop_or_ntprobnp` | 83 | 15 | 46 | 22 | 0.3333 |

## Echo 边界

MIMIC 结构化 echo 可表明检查流程或 LVEF 数值是否存在，但当前没有足以稳定判断心超异常的完整结果层。因此开发队列不能强制 echo-confirmed；院内外部验证仍应实行 `performed + result available + abnormal support` 三级 QC。
