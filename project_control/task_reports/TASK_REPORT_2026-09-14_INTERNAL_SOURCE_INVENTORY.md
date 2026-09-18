# 任务报告：院内 DHF 原始源数据库存审计（2026-09-14）

## 审计范围

对 `DHF_SRR` 中所有 `02_*.csv` 做只读流式清点，仅输出文件/行数/就诊覆盖和聚合关键词计数，不输出患者 ID、文书正文或原始检验值。

## 结果

- CSV 文件数：25。
- 各类别行数与就诊覆盖见 `project_control/internal_dhf_source_inventory_20260914.json`。
- 全部文书非空正文行：775,837。
- 文书中的 ICU/HF/充血/替代诊断关键词仅作高召回候选，不能直接生成 DHF 纳入人数。

## 对研究的影响

院内原始导出已经具备用 NLP/规则进行全量 A+B+C 证据抽取的材料基础。下一步可在本地按 episode 和 T0/T12 时间门控生成候选证据表，再对抽样和边界病例人工裁决；但 ICU 出入 episode、实际给药/治疗升级和结局时间若缺失，仍不能计算最终 event/competing/censor。

## 可复现命令

`python3 project_control/audit_internal_dhf_source_inventory_v20260914.py`
