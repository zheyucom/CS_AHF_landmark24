# 任务报告：DHF来源复核与风险集准备

日期：2026-09-16（CST）

## 本次完成

1. 收集并验证修正后的全量运行 `internal_validation/20260916_semantic_corrected/`：8,385名候选、9,360个 episode 候选；同次住院重复进出 ICU 按 episode 分开，803例存在出 ICU 后再入 ICU。
2. 修正 ICU 科室识别规则：普通“呼吸与危重症医学科”不再自动视为 ICU；仅在文本明确 ICU/监护室时认定 ICU。
3. 修正表型模板误识别：病危/病重通知、麻醉前未勾选选项、作废文书不再作为 HF 锚点。修正后规则层为 865 probable、1 confirmed（旧技术标签）、7,387 not supported、132 unknown；均为工作标签。
4. 将 11 例已完成原文阅读的病例保存为 `AI_semantic_review_11.csv`，共引用 28 条文书、心超和医嘱来源行；6例支持当前DHF、2例不足、3例心源性归因未定。所有标签均标注为 AI 预审，不是独立临床金标准。
5. 扫描男女全量检验表（约5,347万行），生成报告时间门控的乳酸、BNP和前12小时血管活性医嘱代理表：6,432/8,385例有同窗可解析乳酸；单位字段未导出，因此暂不用于最终休克阈值裁决。
6. 将新计数和工作状态写回 `RESEARCH_DASHBOARD.md`，并使工作清单脚本支持指定运行目录，避免把旧 T0 复核结果误套到新 episode。

## 当前队列状态

- 同窗床旁/床边心超结果可用：2,599名候选（修正后运行）。
- 修正后工作队列：优先DHF语义/风险集235例；T12观察链91例；HF锚点42例；规则阴性抽样2,146例；AI已支持但待风险集8例；AI心源性归因未定3例。
- 8,385仍是“按导出条件选择后的成人候选分母”，不是全院成人 ICU 分母，也不是最终 DHF 人数。
- `final_cohort_frozen=false`、`final_riskset_frozen=false`；尚未生成正式 `cohort_freeze.csv`、`outcomes_frozen.csv` 或最终模型性能。

## 仍需外部数据或临床裁决的事项

1. 技术人员补充检查执行时间和检验采样时间；当前报告时间只能作为可重复代理，并需敏感性分析。
2. 核实乳酸单位及前12小时真实采样值，尤其是血管活性药+乳酸≥2的基线休克代理；缺乳酸保持 unknown，不按阴性处理。
3. 完成235例优先队列、91例T12观察链及42例HF锚点的病例级裁决，再冻结DHF纳排表。
4. 以同一冻结 episode 口径重建 T12 后恶化、ICU死亡、活着出 ICU 竞争事件和删失，随后才进入 Fine–Gray、person-period、内部验证和本院外部验证。

## 复现入口

- `python3 project_control/advance_internal_dhf_v20260915.py --out project_control/internal_validation/20260916_semantic_corrected --review-dir project_control/internal_validation/20260915_source_review`
- `python3 project_control/extract_landmark_lactate_20260916.py`
- `python3 project_control/persist_semantic_reviews_20260916.py`
- `python3 project_control/build_cohort_worklist_20260915.py --base project_control/internal_validation/20260916_semantic_corrected --previous project_control/internal_validation/20260915_source_review --review-source project_control/internal_validation/20260915_source_review`
- `python3 -m unittest discover -s project_control -p test_internal_dhf_semantics_20260915.py`（11 tests passed）
