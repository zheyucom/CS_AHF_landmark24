# 任务报告：Gate 3 与影像边界行预审核更新

日期：2026-09-14

## 本次完成

1. 重新审阅 45 例 Gate 3 语义优先队列。基于患者特异性文书、体征、检验和治疗证据，6 例由 `unknown` 保守回填为 `not_supported`：G3-009、G3-010、G3-024、G3-026、G3-030、G3-047。
2. 45 例当前分布：8 例 `echo_supported_draft` 候选、37 例 `not_supported`、0 例保留为未决。G3-014 与 G3-040 已依据其完整文书证据保守排除：前者为感染/肾功能不全主导且心超未支持，后者为脑出血/肺炎主导且缺乏患者特异性 HF 锚点。
3. 对 31 条 MIMIC 影像边界行逐条完成报告范围、模态、肺充血和替代解释的可追溯草案，生成：
   - `project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_adjudicated_20260914.csv`
   - `project_control/bigquery/controlled_annotation_20260904_landmark12_complete_v2/dhf_radiology_annotation_round1_codex_adjudication_user_check_20260914.csv`
4. 31 条影像草案分布：胸部 20、非胸部 6、混合/不清 5；明确充血 7、可能充血 8、无充血 4、不确定 12。非胸部或仅部分显示胸部的报告不进入肺充血阳性/阴性分母。
5. 新增可重复运行脚本：
   - `project_control/adjudicate_gate3_semantic_queue.py`
   - `project_control/bigquery/adjudicate_radiology_boundary_20260914.py`

## 仍需人工裁决的最小集合

- Gate 3：无新增必答病例。45 例均已完成保守预审核，输出仍是 draft/weak label，不替代临床金标准。
- 影像：7 条技术范围或混合报告（DHF-RAD-0003、0060、0064、0069、0220、0264、0280）。若不追求正式标注者一致性，可暂接受 Codex 草案；若用于正式验证，仍需临床人员盲法确认。

## 队列冻结边界

45 例预审核现已完成，可作为人工抽样审计记录并入流程日志；所有 `draft` 标签仍不能替代临床金标准。全院成人 ICU 分母仍为 8,385（男 5,543、女 2,842），不因本次抽样预审核改变。最终 confirmed/probable/not-supported/unknown、事件/竞争事件/删失和模型重跑必须在全量人工规则与执行级结局完成后计算。

## 方法学与文献记录

本次继续采用 Universal Definition/ESC HF 的 A+B 组合、NegEx 式否定/模板过滤、CheXpert 式不确定影像标签；最终预测模型仍按 TRIPOD+AI、PROBAST+AI、Riley 样本量原则、Fine–Gray 竞争风险和 decision-curve analysis 方案执行。以上文献和具体用途已集中记录在 `project_control/DHF_OPERATIONAL_PHENOTYPE_v20260914.md`。
