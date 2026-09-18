# Phase 2 可复跑检索策略

检索日期：2026-07-29  
截止日期：2026-07-29  
语言：English + Chinese  
人群：成人 ICU/住院 strict AHF、HF+early sepsis、CICU/混合休克邻近人群  
时间框架：以 12 h landmark 和未来 48 h treatment-escalation–based HD 为目标任务；邻近证据允许不同时间窗，但须在候选表标记

## 来源路由

1. T1：PubMed + Crossref；
2. T2：Europe PMC 元数据补充 + OpenAlex 覆盖检查；
3. T3/中文：中华医学会期刊网、期刊官网、万方；
4. arXiv 仅在发现相关方法学预印本且无正式版时使用；本轮无 arXiv-only 保留项；
5. Scopus、Web of Science、CNKI 需机构环境人工补查。

## 检索式

完整 PubMed、Crossref 和 OpenAlex 检索式、命中与截断数见 `quality_report.md` 第 3 节；逐次查询 URL、时间戳、原始标识符和规范标识符见 `source_manifest.jsonl`。

## 纳入标准

- 成人 ICU、CICU 或住院 AHF/ADHF；
- HF+sepsis、septic shock 或 mixed septic-cardiogenic physiology；
- 结局涉及 WHF、治疗强化、血流动力学/循环恶化、incident/progressive CS；
- 为 landmark、动态 EHR、信息泄漏、校准、外部验证或报告规范提供直接方法支持；
- 英文或简体中文；
- 2014 年以后优先，奠基性方法或定义可早于 2014。

## 排除标准

- 儿童、妊娠、动物研究；
- 纯围术期、器械/瓣膜结构退化或其他低可迁移场景；
- 已发生 CS 后仅预测死亡且不提供恶化前信息；
- 无时间锚点或无法区分预测变量与结局后治疗；
- 题录无法由 PubMed、Crossref、正式预印本平台或中文权威记录确认；
- 预印本已有正式发表版时，仅保留正式版主记录。

## 去重

```text
DOI
  > PMID / PMCID / arXiv ID
  > 标准化题名 + 第一作者 + 年份
```

无 DOI 时，标准化题名词元 Jaccard ≥0.90 且第一作者姓一致视为重复。正式期刊版优先于预印本，元数据更完整的记录优先。

## 筛选与优先级

- Pass 1：题名/元数据；
- Pass 2：摘要/元数据优先级；
- 40 篇为待全文评估队列，不是完成全文纳入；
- 25 篇为临时核心集；
- 15 篇为后续首批 PDF 精读集；
- SI 选择确定前停止于元数据和访问路径预判。

