---
project_id: CS_AHF_landmark24_literature
profile_version: "1.0"
updated_at: "2026-07-29T22:05:02+08:00"
controller_status: "Phase 2 Waiting review"
user_scope_confirmed: true
source_project_root: "/Users/zheyu/Desktop/CS_AHF_landmark24"
literature_workspace_root: "/Users/zheyu/Desktop/CS_AHF_landmark24/literature_workspace"
---

# Project Profile

## 1. 研究方向

中文工作题目：

> 急性心力衰竭合并早期脓毒症 ICU 患者未来 48 h 血流动力学恶化风险预测模型研究：基于 MIMIC-IV 的模型开发及本院外部验证

英文工作题目：

> Early prediction of hemodynamic deterioration in ICU patients with acute heart failure and early sepsis: model development using MIMIC-IV and external validation in a local hospital cohort

本配置以项目根目录 `README.md` 的当前主线为准，而不是沿用文件夹名中的历史 `landmark24`：

| 维度 | 当前定义 |
|---|---|
| 人群 | 成人首次 ICU stay；strict AHF；12 h 前存在 early sepsis12；12 h 前无 overt cardiogenic shock proxy |
| 数据源 | MIMIC-IV / MIMIC-IV derived；后续本院 ICU/住院数据库外部验证 |
| Index time | ICU `intime` |
| Landmark | ICU 入科后 12 h |
| Predictor window | ICU 0–12 h |
| Prediction window | ICU 12–60 h，即 landmark 后 48 h |
| 主结局 | treatment-escalation–based hemodynamic deterioration |
| 当前主队列 | n = 2,424 |
| 当前主结局 | 334 events，13.78% |
| 主要方法 | 惩罚 logistic regression / elastic-net；校准；树模型作为补充比较 |

## 2. 文献问题簇

LiteratureAgent 应分别检索、标记并最终汇合以下证据流：

1. AHF/ADHF 的 worsening heart failure 与治疗升级型结局定义。
2. AHF/ADHF 患者新发 cardiogenic shock 或 mixed shock 的早期预测。
3. Heart failure + sepsis / infection 交叉人群的近期循环恶化、休克和短期结局。
4. ICU/CICU hemodynamic deterioration、circulatory failure 与动态早期预警模型。
5. Landmark prediction、时间窗设计、标签泄漏、动态 EHR 与临床可行动性。
6. 预测模型报告与偏倚：TRIPOD+AI、PROBAST+AI、校准、决策曲线、外部验证样本量。
7. MIMIC-IV 到中国本院数据的变量映射、可迁移性、dataset shift 和外部验证。

## 3. 用户确认范围

| 项目 | 确认值 | 状态 |
|---|---:|---|
| 候选题录 | 100 条唯一记录 | Confirmed |
| 全文评估 | 40 篇 | Confirmed |
| 核心证据集 | 25 篇 | Confirmed |
| 第一批 PDF 精读 | 15 篇 | Confirmed |
| 语言 | 英文 + 简体中文 | Confirmed |
| 时间范围 | 建库至 2026-07-29；优先 2014 年以后 | Confirmed with profile |
| 文献类型 | 原始研究、系统综述/高质量综述、指南/共识、方法学规范 | Confirmed with profile |

建议保留更早的奠基性文献，不因年份阈值机械排除。中国文献只在真实数据库检索和合法访问条件下纳入；无法访问 CNKI 等机构资源时必须记录为人工介入项。

## 4. 纳入与排除原则

### 优先纳入

- 人群、结局或时间设计至少有一项直接对应当前研究。
- 研究设计、事件率、预测时点、验证类型和性能指标可核验。
- 具有 DOI、PMID、arXiv ID、出版社 URL 或其他稳定来源标识。
- 原始研究优先；结局定义、指南和预测模型方法学文件可作为框架证据。
- 2024–2026 年直接竞争研究优先核验。

### 排除或降级

- 仅预测已发生休克后的死亡，且不能支持早期风险识别。
- 只报告 accuracy、缺少事件率或时间锚点。
- 明显使用 post-landmark 信息却声称早期预测。
- 摘要、题录或 DOI 无法交叉核验。
- 非法镜像、绕过付费墙或来源不明 PDF。
- 同数据库、同任务、低质量重复建模，仅保留代表性研究。

## 5. 本地路径

| 用途 | 路径 | 写入策略 |
|---|---|---|
| 源项目 | `/Users/zheyu/Desktop/CS_AHF_landmark24` | 保留现有内容 |
| 新文献工作区 | `/Users/zheyu/Desktop/CS_AHF_landmark24/literature_workspace` | Controller 管理 |
| 既有文献结果 | `/Users/zheyu/Desktop/CS_AHF_landmark24/literature_review` | 只作 legacy 输入，不覆盖 |
| 后续合法 PDF | `/Users/zheyu/Desktop/CS_AHF_landmark24/literature_workspace/02_literature_discovery/pdfs` | 不提交 Git |
| 后续 Obsidian 笔记 | 待确认 vault 后确定 | 未确认前禁止写入 |

## 6. Zotero 配置

| 项目 | 当前值 |
|---|---|
| Zotero Desktop | 9.0.4 |
| Local API | `http://127.0.0.1:23119`，状态 200 |
| Connector | 状态 200 |
| Library | `我的文库`，libraryID 1 |
| 当前选中 collection | `#心衰早期预测` |
| collection key | `4EMWVUHV` |
| Phase 1 权限 | 仅连接和 collection 核验 |
| Phase 3 权限 | 只读库存/去重；写入脚本由用户手动执行 |

用户于 2026-07-29 报告此前建议的文章已手动加入 Zotero。该状态尚未由 API 核验；Phase 3 将把它作为只读去重基线，不在 Phase 2 查询或修改。

不读取或写入 `zotero.sqlite`。任何创建条目或链接附件的动作都必须在 Phase 3 审核通过后，以用户可检查、可手动运行的脚本交付。

## 7. Obsidian 配置

截至 2026-07-29：

- `/Applications/Obsidian.app` 未检测到。
- Documents、Desktop、常见 iCloud Obsidian 路径及 Spotlight 中均未检测到 `.obsidian` vault。
- `obsidian_vault_path` 暂为 `null`。

Phase 4 前用户必须提供一个绝对路径，或明确选择“暂不接入 Obsidian，仅在文献工作区生成 Markdown”。

## 8. 后续自动化意图（尚未启用）

### 方案 A：RSS

计划在 Phase 4 的长期维护文档中给出：

- Zotero 中配置重点期刊 RSS。
- 为 PubMed 保存检索建立 RSS。
- 建议抓取间隔、人工筛选规则和归档流程。

用户消息中的 `[citation:3][citation:6][citation:11]` 尚无可解析来源，当前不作为有效引用；Phase 4 必须以真实官方文档或数据库说明替换。

### 方案 B：定期检索

计划每周由 LiteratureAgent 重跑经批准的检索式，按 DOI → PMID → arXiv ID → 标准化标题/年份与现有 `source_manifest` 去重，并仅输出新增/变更记录。当前没有创建自动任务；只有 Phase 4 审核通过后才可启用。

## 9. 安全与数据治理

- 不绕过付费墙；只保存合法或授权获取的全文。
- 不凭空创建题录、DOI、结果或页码。
- 不向外部模型/API发送未发表手稿、私有笔记、MIMIC 原始数据或本院患者数据。
- PDF、数据库、凭据、API 密钥、患者级数据不得进入 Git。
- 当前源项目不是 Git 仓库，因此没有创建 checkpoint 或 commit。

## 10. 审核状态

`user_scope_confirmed=true`

Phase 2 已完成并通过 Controller 独立机械审计，当前为 `Waiting review`。候选/全文优先/核心/首批精读数量分别为 100/40/25/15；21/40 份合法正文 PDF 已验证，11/40 需人工授权访问，8/40 未找到授权 OA 正文，SI 下载数为 0。用户提交的 Obsidian 值仍是模板占位符，因此 `obsidian_vault_path=null`；该项只阻塞 Phase 4。在用户明确批准 Phase 2 前，不进入 Zotero 阶段。
