# 任务报告：Gate 3 50 例机器辅助预审核

日期：2026-09-13

## 本轮完成

- 读取男女两套全部文书、检查、用药和诊断导出，并按 `patient_id + visit_id` 与 50 例 Gate 3 样本合并；未修改 `DHF_SRR` 原始文件。
- 对每例建立 `[T0-24 h, T0+12 h)` 文书时间窗。入 ICU 时间优先使用文本中带有“入 ICU 时间/患者于某时入 ICU/进入 ICU”的明确事件时间；无法取得时保留结构化候选代理并标为不确定。
- 心超字段按三态拆分：完成、结果可用、异常支持。报告中“肺动脉显示不清”等局部受限不再自动判为整份不可解释；仅“无法评估/无法测量/各瓣膜口血流无法评估”等明确语句进入 `uninterpretable`。
- 文书语义采用规则型、可审计的否定/不确定语境过滤。模板风险告知、评分选项和回顾性出院叙述不能作为 T0 时点的心衰或失代偿金标准。
- 用药表只用于重建开嘱-停嘱区间；没有执行级给药时间时不声称实际 eMAR，也不据此填写 T12 后事件。

## 50 例预审核结果（含本轮人工裁决）

| 字段 | 结果 |
|---|---:|
| 明确 ICU 文书事件时间 | 50 |
| 结构化入区代理、需核对 | 0 |
| 多次 ICU episode 需按首段 index 处理 | 1（G3-043，已排除） |
| 心超报告完成 | 50 |
| 心超结果可用 | 50 |
| 心超异常域初筛支持 | 50（含轻微/非特异异常，不能等同 DHF） |
| 心超明确不可解释 | 0；G3-001 经人工确认保留为有效危重状态报告 |
| HF anchor 规则支持草稿 | yes 34、uncertain 1、unknown 14、no 1；仍需确认是否为本次事件、是否误命中模板 |
| 失代偿域规则支持草稿 | yes 28、uncertain 7、unknown 14、no 1 |
| 管理证据可由医嘱/文书支持 | yes 11、no 1、unknown 38；均未升级为执行级结局 |
| DHF 综合层级 | `multidomain_draft` 4、`echo_supported_draft` 30、`unknown` 15、`not_supported` 1 |

上述规则支持是定位人工核对重点的草稿，不是临床金标准；尤其需要排除“可能发生/风险告知”、评分模板、术后或感染/出血等替代解释。`dhf_tier_final` 仍只表示待核对的 draft 层级。

## 本轮人工裁决

此前清单中的项目均已由用户核实，当前 [需用户核实清单](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_need_user_check.csv) 仅保留表头（0 例待核实）。

- `G3-005`：T0=`2025-08-15 10:15`，由入院/出 ICU 文书支持。
- `G3-015`：T0=`2025-01-07 12:45`，由首次病程录、病案首页及转入记录支持。
- `G3-029`：T0=`2025-04-26 12:20`，由首次病程录及 ICU 转病房记录支持。
- `G3-050`：T0=`2025-06-03 22:15`，由首次病程录、出 ICU 记录及病案首页支持。
- `G3-043`：同一次就诊存在多段 ICU；首段 `2022-01-08 09:35` 作为 index，`2022-01-12 17:35` 为术后再入 ICU；用户确认无 DHF，标记 `not_supported` 并排除。
- `G3-001`：心脏骤停后的心超即使部分瓣膜血流无法评估，仍保留 EF 15%/心室活动减弱为有效危重状态报告。

## 分母一致性待裁决

现有 `icu_stay_master` 按“年龄≥18岁”严格执行后得到 8,385 名成人患者（女 2,842、男 5,543）；原始候选患者为 8,386 名（女 2,842、男 5,544）。差异来自患者 `9204020`（男，出生日期 2006-01-01，就诊 2023-01-09，结构化年龄 17 岁），其病案首页年龄也为 17 岁。该记录已按预设年龄标准排除，不能在未裁决前写成 8,386 名成人分母。

## NLP 与方法依据

本轮只使用可追溯规则和人工复核，不把复杂模型输出直接当作金标准。否定识别沿用 NegEx 的可解释思想（Chapman et al., 2001, doi:10.1006/jbin.2001.1029）；不确定性和报告级人工验证参考 CheXpert（Irvin et al., AAAI 2019, doi:10.1609/aaai.v33i01.3301590）。最终预测模型的报告和偏倚审计应按 TRIPOD+AI 与 PROBAST/PROBAST+AI 组织，并预先冻结时间窗、缺失处理、事件定义和外部验证方案。复杂 NLP 只有在规则层人工验证性能不足时，才进入 section-aware contextual model，并需独立保留集验证。

## 下一步

1. 对 50 例逐例确认 HF anchor、失代偿域和管理强化；优先查看入 ICU 记录、SOAP、会诊、抢救记录及 T12 前检查/检验，排除模板和回顾性内容。
2. 冻结 `DHF_candidate`、`echo_supported_draft`、`multidomain_draft` 和 `not_supported` 的判定规则，记录规则版本和分歧裁决。
3. 补充 ICU 出科、院内死亡、自动出院和最终出院的事件时间；只有取得 T12 后实际升级或 ICU 死亡时间，才重算 event/competing/censor。
4. 先裁决 `9204020` 是否确属年龄≥18岁的数据录入异常；分母锁定后，将同一规则无修改地运行至 8,385 或 8,386 名成人 ICU 患者，输出全量三级表型审计和进入 MIMIC 内部开发/院内外部验证的锁定队列。

## 交付文件

- [reviewed CSV](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_reviewed.csv)
- [reviewed XLSX](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_reviewed.xlsx)
- [需用户核实清单](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913_need_user_check.csv)
- [全 ICU 三级表型审计表](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_dhf_three_tier_audit_20260913.csv)
- [全 ICU 三级表型 QC 摘要](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_dhf_three_tier_audit_qc_20260913.json)
- [分母差异病例](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/denominator_discrepancy_9204020.csv)
- [审核脚本](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/review_internal_gate3_50.py)
