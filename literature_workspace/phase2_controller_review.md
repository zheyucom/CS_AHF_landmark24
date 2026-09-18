# Phase 2 Controller Review

审核时间：2026-07-29T22:05:02+08:00  
阶段状态：`Waiting review`  
Controller 结论：`PASS — ready for user review`

## 1. 范围完成情况

| 项目 | 目标 | 实际 | 审核 |
|---|---:|---:|---|
| 唯一候选题录 | 100 | 100 | Pass |
| 全文评估优先队列 | 40 | 40 | Pass |
| 核心证据集 | 25 | 25 | Pass |
| 首批 PDF 精读队列 | 15 | 15 | Pass |
| 语言范围 | 中英文 | 英文 96；中文 4 | Pass with coverage limitation |

## 2. 来源与全文审计

- `candidate_table.csv`：100 行、100 个唯一稳定 ID；全部具有 DOI、PMID、PMCID、arXiv ID 或稳定落地 URL。
- `source_manifest.jsonl`：2,210 个可解析来源事件。
- 题录核验：94 条 PubMed + Crossref 双 T1；4 条 PubMed + 中文官方期刊/万方记录；2 条 Crossref T1；未核验记录 0。
- `download_log.csv`：40 行，覆盖全部全文优先队列。
- 21 篇状态为 `verified_main_pdf`；11 篇为 `manual_authorized_retrieval_required`；8 篇为 `no_authorized_pdf_found`。
- 21/21 本地正文均复核 `%PDF`、MIME、正页数、可提取文本、题名词元、前 5 页 DOI、bytes 与 SHA-256。
- 磁盘 PDF 集合与日志中的 21 条验证记录完全一致；Supporting Information 文件为 0。

## 3. 首批精读可用性

首批 15 篇中已有 11 篇验证正文。当前缺少：

- `R004`：ADHERE 风险模型。
- `R020`：动态心源性休克风险预测。
- `R056`：早期循环衰竭机器学习预测。
- `R071`：landmark method 方法学文献。

这些条目可能已存在于用户手动维护的 Zotero 文库中；Phase 3 只能通过 Zotero Local API 做只读核验，不得直接读取或写入 `zotero.sqlite`。

## 4. 已知限制

- 中文候选仅 4 篇，尚未做 CNKI 系统检索。
- 本阶段未接入 Scopus 或 Web of Science。
- 40 篇是全文评估优先队列；当前只有 21 篇完成文件级正文验证，不能表述为 40 篇均已完成内容级全文纳排。
- 尚未执行全文级风险偏倚、利益冲突、撤稿状态、样本重叠或证据综合。
- 用户报告既往建议文章已加入 Zotero，记录为 `reported=true, verified=false`。

## 5. 安全边界

- 未绕过付费墙。
- 未下载 Supporting Information。
- 未查询或修改 Zotero。
- 未访问 Obsidian。
- 未访问或上传患者级数据。
- 未将 PDF、Zotero 数据库或凭据提交至 Git。

## 6. 阶段门建议

Controller 建议批准 Phase 2。只有用户明确回复 `phase2_approved=true` 后，才进入 Phase 3，创建或复用 ZoteroAgent，并执行只读库存、重复项和附件核验。
