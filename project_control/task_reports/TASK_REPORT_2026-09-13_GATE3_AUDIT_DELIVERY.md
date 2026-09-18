# 任务报告：Gate 3 人工核对包与院内 DHF 三级审计交付

日期：2026-09-13

## 本轮完成

- 将男女数据按 `patient_id + visit_id` 合并，并以每位患者首次成人候选 ICU 就诊作为 index stay。
- 完成院内全量三层审计底表：全 ICU 成人分母、报告时间代理窗口 `[T0-24 h, T0+12 h)`、心超结果可用、关键词异常支持 draft 和 echo-supported DHF draft 均已编码。
- 完成 50 例人工核对样本，男女各 25 例；提供 CSV 和带下拉选项、冻结窗格、人工字段高亮及填写说明的 XLSX。用户已裁决 T0/多 ICU episode 边界；已生成 45 例 DHF 语义优先队列供下一步临床确认。
- 已按用户确认的语义冻结当前规则：护理记录明确入监护室事件优先；普通病程录入病房时间及出 ICU 记录中的“入院时间”不直接作为 ICU T0；检查/检验日期当前按报告时间；尿量按区间累计理解；氧浓度与给氧方式联读；气插、气切、吸痰和其他管路分开；用药按开嘱-停嘱区间解释，不能声称执行级 eMAR。

## 当前计数

- 原始候选患者：8,386（男 5,544、女 2,842）。
- 排除 1 名未成年人（男性 17 岁）后，成人 ICU index 分母：8,385（男 5,543、女 2,842）。
- 报告时间代理窗口内床旁心超：2,519；结果可用：2,517；关键词异常支持 draft：2,475。
- 2,475 例仍是规则草稿，不能直接作为最终 DHF 或 echo-supported DHF 标签。
- event、competing event、censor 当前导出无法可靠计算，已在 QC JSON 中标记为 unavailable；需要回填 ICU 结局、实际治疗执行或明确的代理定义后再重算。

## 交付文件

- [人工核对 XLSX](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913.xlsx)
- [人工核对 CSV](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_gate3_manual_review_50_20260913.csv)
- [人工核对填写说明](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/INTERNAL_GATE3_MANUAL_REVIEW_INSTRUCTIONS_20260913.md)
- [全量 DHF 三级审计 CSV](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_dhf_three_tier_audit_20260913.csv)
- [三级审计 QC JSON](/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/internal_validation/20260912/internal_dhf_three_tier_audit_qc_20260913.json)

## 质量检查

- 5 个 Python 构建/审计脚本通过 `py_compile`。
- XLSX 重新导入后包含 `人工核对`（51 行含表头、39 列）和 `填写说明` 两个工作表。
- 三层审计 CSV 为 8,385 行、19 列（含 `manual_reviewed_flag` 和 `outcome_status_reviewed`），`patient_id + visit_id` 唯一性通过。
- 原始 `DHF_SRR` 数据未修改。

## 下一步闸门

1. 完成 45 例语义优先队列的 HF anchor、失代偿域、管理证据和替代解释确认；已确认的 T0、G3-001、G3-043 及四例 ICU 时间不再重复核对。
2. 依据核对结果冻结三层表型判定规则，并记录规则版本和任何边界修订。
3. 补提或确认检查完成时间、检验采样时间、结果可见时间及执行级 eMAR；在数据不足时预先定义代理结局和敏感性分析。
4. 回填全量 event/competing/censor 后，再按事件数确定 MIMIC 内部开发模型的参数数、校准方法和院内外部验证 manifest。
