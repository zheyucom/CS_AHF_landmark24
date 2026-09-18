# 任务报告：本院外部验证数据提取规格

日期：2026-09-02  
状态：完成，可提交信息科/数据库工程师进行字段与样例对接。

## 本次完成

- 新增本院外部验证的完整原始数据提取规格：
  `project_control/INTERNAL_HOSPITAL_EXTRACTION_SPEC_DHF_EXTERNAL_VALIDATION_V1.md`。
- 新增信息科字段映射模板：
  `project_control/INTERNAL_HOSPITAL_FIELD_MAPPING_TEMPLATE.csv`。
- 新增可直接转发的信息科简版申请：
  `project_control/INTERNAL_HOSPITAL_DATA_REQUEST_BRIEF_DHF_V1.md`。
- 明确本院不应先按 BNP、心衰 ICD 或结局做窄筛选；应先提取连续成年 ICU 住院候选宇宙和原始时间序列。
- 明确基本风险集排除：未到达 T12、关键时间错误、以及 T0-T12 已有 vasoactive/inotrope 加 lactate >=2 mmol/L 的 overt shock proxy。
- 明确 ACS/AMI、AKI/CKD、AF、COPD、肺炎/ARDS、感染/脓毒症、术后状态不作机械排除；PE、BNP-only 和替代诊断进入预设敏感性/审计。
- 补全影像、心超和 ICU 前临床病历所需的发生/可见时间、文本、版本和审计字段。
- 明确药物必须同时保留医嘱与实际执行记录、每次连续泵入速率变化和剂量单位，以重建 NEE、并发药物数和持续 30 min 的结局。

## 仍未冻结的事项

- 最终主 DHF 层级（radiology-supported 或 multidomain）仍等待 MIMIC 的 300/60 报告临床标注、规则 PPV/kappa 和导师确认。
- 因此本院数据提取按“宽原始宇宙”启动；最终纳入代码必须在 MIMIC 表型规则完成后、且查看本院结局前锁定。

## 给本院的下一动作

1. 确认连续研究起止时间、EHR 迁移节点和数据审批范围。
2. 先按字段映射模板提供每张表 20-50 条脱敏样例、字段字典、单位和时间说明。
3. 通过链接键、药物执行记录、影像/病历可用时间和 ICU 出科/死亡时间 QC 后，再导出全量阶段 A 包。
4. 结局长表作为阶段 B 密封包，在本院映射和 MIMIC 表型冻结后才合并分析。
