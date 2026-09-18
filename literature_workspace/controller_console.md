# CS_AHF 文献工作区 · Controller Console

更新时间：2026-07-29T22:05:02+08:00  
当前阶段：Phase 2 — LiteratureAgent 文献发现与导入准备  
当前状态：**Waiting review — Controller validation passed; Phase 3 not started**  
范围门：`user_scope_confirmed=true`

## 1. 控制原则

1. Controller Console 只维护范围、依赖、状态、审计链和 Agent 分发；不在本会话内代替后续专项 Agent 完成全部工作。
2. 在用户明确回复 `user_scope_confirmed=true` 前，禁止分发 LiteratureAgent、ZoteroAgent 或 ObsidianAgent。
3. 每个阶段只允许生成本阶段约定的工件；完成后状态必须回到 `Waiting review`。
4. 旧的 `literature_review/` 结果属于 **legacy / provisional evidence**。它们可用于构建去重基线和检索种子，但不得自动升级为本工作区的已审计证据。
5. 任何题录、DOI、URL、引文、PDF 来源和页码证据必须可追溯；无法核验时标记 `unverified`，不得补写或猜测。
6. 只获取开放获取、作者合法公开或用户已有授权访问的全文；不得绕过付费墙。
7. 不直接读取或写入 `zotero.sqlite`。Zotero 写入脚本只能由用户在 Zotero 桌面端手动运行。
8. PDF、Zotero 数据库、API 密钥、个人数据和未脱敏研究数据不得提交至 Git。

## 2. 阶段状态

| 阶段 | 专项会话 | 状态 | 进入条件 | 阶段交付物 |
|---|---|---|---|---|
| 1. 初始化与配置 | Controller Console | Approved / completed | 用户于 2026-07-29 确认范围 | `project_profile.md`、`dependency_setup.md`、`controller_state.json` |
| 2. 文献发现与导入准备 | LiteratureAgent | Waiting review | LiteratureAgent 已完成；Controller 独立机械审计通过，等待用户审核 | `candidate_table.csv`、`source_manifest.jsonl`、`download_log.csv`、`quality_report.md`、`phase2_controller_review.md` |
| 3. Zotero 接入 | ZoteroAgent | Blocked by gate | Phase 2 获批 | 只读库存快照、去重报告、linked-file mapping、用户手动运行脚本、链接验证报告 |
| 4. Obsidian 与维护 | ObsidianAgent | Blocked by gate | Phase 3 获批且 vault 路径确认 | PDF 优先页码证据笔记、`.manifest.json`、`long_term_maintenance.md`、自动化提案 |

## 3. Agent 会话登记

| 角色 | Codex task ID | 当前动作 | 状态 |
|---|---|---|---|
| Controller Console | `019faad2-9ca6-70b2-ad06-0679247decd6` | 本会话，维护阶段门与审计记录 | Active / Waiting review |
| LiteratureAgent | `019fad8c-63e2-77e2-aec8-1eef53f69e16` | 已完成检索、筛选、合法全文路径审计和文件验证 | Completed / idle / Waiting review |
| ZoteroAgent | 未创建 | Phase 2 审核通过后创建 | Not created |
| ObsidianAgent | 未创建 | Phase 3 审核通过且 vault 路径确认后创建 | Not created |

用户已确认候选 100、全文 40、核心 25、首批精读 15，语言为中英文。Obsidian vault 仍未提供有效绝对路径；该项不阻塞 Phase 2，但继续阻塞 Phase 4。

## 4. 已识别研究主题

研究问题以项目根目录 `README.md` 为主定义：

> 使用 ICU 入科后 0–12 h 可获得的结构化临床信息，预测严格 AHF 且在 12 h 内满足 early sepsis、同时在 landmark 前未发生 overt cardiogenic shock 的成人 ICU 患者，在 ICU 12–60 h 内发生 treatment-escalation–based hemodynamic deterioration 的风险；使用 MIMIC-IV 开发，并计划以本院队列外部验证。

详细范围和提议检索配额见 `project_profile.md`。

## 5. 工件与审计约定

### Phase 2：LiteratureAgent

计划目录：`02_literature_discovery/`

- `candidate_table.csv`：一行一条候选记录；必须含稳定 ID、标题、作者、年份、来源、研究设计、筛选状态、排除理由。
- `source_manifest.jsonl`：每行一个来源事件；记录数据库、检索式、检索时间、DOI/PMID/arXiv/URL、访问状态和核验状态。
- `download_log.csv`：记录 PDF 许可依据、下载 URL、时间、文件 SHA-256、成功或失败原因；不将 PDF 内容写入 Git。
- `quality_report.md`：报告检索覆盖、去重、缺失 DOI、全文不可得、需要人工访问和潜在偏倚。

### Phase 3：ZoteroAgent

计划目录：`03_zotero/`

- 只读查询 Zotero Local API，使用 DOI → PMID → 标准化标题/年份顺序去重。
- 只生成 metadata import 和 linked-file mapping 工件。
- 用户在 Zotero 桌面端手动运行脚本后，再做只读验证。
- 禁止直接访问或修改 `zotero.sqlite`。

### Phase 4：ObsidianAgent

计划目录：`04_obsidian/`

- 只对合法获得且通过完整性检查的 PDF 生成页码证据笔记。
- 每条关键判断保留 PDF 页码、图表/章节定位和来源 ID。
- 建立 `.manifest.json` 追踪笔记、PDF 哈希、题录 ID、生成时间和验证状态。
- 在 `long_term_maintenance.md` 中记录 Zotero/PubMed RSS 建议及每周重新检索、去重和审计方案。
- 用户给出的 `[citation:3][citation:6][citation:11]` 当前仅视为待解析占位符；在原始来源未提供和核验前，不把它们当作有效引文。

## 6. 已确认范围

- 候选题录目标：100 条唯一记录。
- 全文评估目标：40 篇。
- 核心证据集目标：25 篇。
- 第一批 PDF 精读目标：15 篇。
- 语言：英文 + 简体中文。
- 时间范围：建库至 2026-07-29；优先 2014 年以后，同时保留更早的奠基性研究。
- Zotero 目标 collection：`#心衰早期预测`，key `4EMWVUHV`。
- Obsidian vault：用户回复仍为占位符，尚未提供有效绝对路径。
- Supporting Information：`SI=no`；只下载合法或授权可得的论文正文，不下载任何补充材料。
- Zotero：用户报告“此前建议下载的文章已手动放入 Zotero”。这是用户陈述，Phase 2 不查询验证；Phase 3 将只读核实条目和重复项。

## 7. 当前控制点

Phase 2 已回到 `Waiting review`。Controller 对 100 条候选、40 条全文优先队列、25 条核心集、15 条首批精读集、2,210 条来源事件、40 条全文访问日志及 21 份本地正文 PDF 完成独立机械审计，未发现结构、哈希、文件集合或 SI 违规错误。21/40 份合法正文已验证；其余 11 篇需人工授权访问，8 篇未找到授权 OA 正文。详细结论见 `phase2_controller_review.md`。

用户报告既往建议文章已加入 Zotero，但该状态仍为 `verified=false`。在用户明确回复 `phase2_approved=true` 前，不创建或分发 ZoteroAgent，不查询 Zotero，也不进入 Phase 3。
