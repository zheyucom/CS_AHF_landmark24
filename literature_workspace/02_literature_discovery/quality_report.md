# Phase 2 文献发现与来源核验质量报告

生成日期：2026-07-29  
检索截止：建库至 2026-07-29  
当前状态：`Waiting review`  
SI 选择：`no`

## 1. 阶段边界与当前完成度

本报告仅覆盖 Phase 2：文献发现、去重、题名/元数据筛选、候选题录核验、全文合法访问路径预判。没有查询或写入 Zotero，没有读取 `zotero.sqlite`，没有读取或上传 MIMIC-IV/本院患者级数据，没有生成 Obsidian 笔记，也没有撰写综合综述或论文段落。

Controller 已在 2026-07-29 明确发送 `SI=no`。所有正文下载命令均使用 `--no-si`，只处理已确定清单中的合法开放获取论文正文；没有下载 Supporting Information、补充附件、数据包或其他 SI。40 篇仍表示“全文评估优先队列”，不表示已完成全文纳入；25 篇核心集和 15 篇首批精读集仍是 Phase 2 的优先级集合。

合法正文准备结果：

- 40/40 条均完成 OA/授权路径审计；
- 21/40 取得并验证主文 PDF；
- 11/40 存在 OA/全文落地证据，但自动获取受 403、挑战页、端点不可用或“无主文 PDF 对象”影响，标记 `manual_authorized_retrieval_required`；
- 8/40 在审计路径中未发现授权 OA 主文 PDF，标记 `no_authorized_pdf_found`；
- 核心 25 中 14 篇已取得验证主文 PDF；
- 首批 15 中 11 篇已取得验证主文 PDF；未自动取得的是 R004、R020、R056、R071；
- 21/21 文件均通过 `%PDF`、MIME、页数、可提取文本、题名/DOI、bytes、SHA-256 核验；
- 没有把 HTML、图片或 Supporting Information 当作主文 PDF。

用户另报告此前建议的 legacy 文章已手动放入 Zotero：

```text
user_reported_legacy_articles_imported=true
verified=false
```

Phase 2 没有查询或修改 Zotero，故无法确认实际条目、附件或重复项；Phase 3 ZoteroAgent 应只读核实。“待导入”不再作为当前计划性结论。

## 2. 数据库与来源覆盖

| 来源 | 层级 | 用途 | 查询数 | API 总命中 | 本次取回 | 最终 100 条中的核验作用 |
|---|---:|---|---:|---:|---:|---|
| PubMed E-utilities | T1 | 临床主题发现、DOI→PMID、题录核验 | 8 个主题检索；5 个批量 DOI 反查 | 31,749 | 1,363 个主题检索出现；98 个最终候选有 PMID | 94 条与 Crossref 双源；4 条中文记录与官网/万方联合核验 |
| Crossref REST | T1 | 跨学科发现、DOI 精确核验、许可元数据 | 6 个主题检索；100 个 DOI 精确反查 | 34,375,538（宽检索 API 估计值） | 480 个主题检索出现；100 次精确反查 | 94 条与 PubMed 双源；2 条仅 Crossref T1 |
| Europe PMC REST | T2 | PubMed 记录的摘要、语言、PMCID 补充 | 4 个批次 | 98 | 98 | 元数据补充，不替代 PubMed/Crossref 的存在性核验 |
| OpenAlex REST | T2 | 补充覆盖与版本/遗漏检查 | 4 | 29,595 | 100 个出现，98 个唯一 | 与最终候选 DOI/题名重合 4 条；未提升新记录 |
| 中华医学会期刊网/期刊官网 | 中文权威记录 | 中文题录官网级核验 | 3 | 3 | 3 | 3 条中文候选的 DOI 官方落地页 |
| 万方医学 | T3 手工权威记录 | 中文题录官网级核验 | 1 | 1 | 1 | 1 条中文候选的万方记录 |
| arXiv | T1（预印本） | 仅拟用于相关方法学/预印本 | 0 | — | 0 | 预检可达；本轮没有需要保留的 arXiv-only 记录 |
| Scopus / Web of Science | T3/机构权限 | 补充查全 | 0 | — | 0 | 未挂载可调用接口；T1/T2 已达到预设候选量，列为覆盖限制 |
| CNKI | T3/机构权限 | 中文补充查全 | 0 | — | 0 | 未进行程序化检索；不得把不可访问结果当作已核验记录 |

说明：

- Crossref 的 `query.bibliographic` 总命中是宽检索估计值，不能解释为全部相关文献；本轮每式按相关性取前 80 条。
- PubMed 宽检索按相关性最多取前 180 条；Q5 实际仅 103 条。
- OpenAlex 仅作 T2 补充，不用于替换已由 T1 精确核验的主记录。
- 中文记录只有在 PubMed 题录存在且 DOI 能解析到中华医学会期刊网、期刊官网或万方记录时才保留。

## 3. 完整检索式与命中

### 3.1 PubMed

**Q1_AHF_WHF_definition** — 总命中 229，取回 180

```text
("acute heart failure"[Title/Abstract] OR "acute decompensated heart failure"[Title/Abstract])
AND ("worsening heart failure"[Title/Abstract] OR "in-hospital worsening"[Title/Abstract]
OR "treatment intensification"[Title/Abstract] OR "treatment escalation"[Title/Abstract])
```

**Q2_AHF_to_CS** — 总命中 427，取回 180

```text
("acute heart failure"[Title/Abstract] OR "acute decompensated heart failure"[Title/Abstract])
AND ("cardiogenic shock"[Title/Abstract])
AND (predict*[Title/Abstract] OR risk[Title/Abstract] OR progression[Title/Abstract]
OR "machine learning"[Title/Abstract])
```

**Q3_HF_sepsis_mixed** — 总命中 6,491，取回 180

```text
("heart failure"[Title/Abstract])
AND (sepsis[Title/Abstract] OR septic[Title/Abstract] OR infection[Title/Abstract])
AND ("intensive care"[Title/Abstract] OR ICU[Title/Abstract] OR shock[Title/Abstract]
OR mortality[Title/Abstract] OR outcome*[Title/Abstract])
```

**Q4_ICU_hemodynamic_deterioration** — 总命中 3,267，取回 180

```text
("hemodynamic deterioration"[Title/Abstract] OR "hemodynamic instability"[Title/Abstract]
OR "circulatory failure"[Title/Abstract] OR "cardiovascular intensive care"[Title/Abstract]
OR "cardiac intensive care"[Title/Abstract])
AND (predict*[Title/Abstract] OR "early warning"[Title/Abstract]
OR "machine learning"[Title/Abstract] OR deterioration[Title/Abstract])
```

**Q5_dynamic_EHR_landmark_leakage** — 总命中 103，取回 103

```text
("electronic health record"[Title/Abstract] OR EHR[Title/Abstract]
OR "intensive care"[Title/Abstract])
AND ("dynamic prediction"[Title/Abstract] OR landmark*[Title/Abstract]
OR "time-dependent"[Title/Abstract] OR "real-time prediction"[Title/Abstract]
OR "data leakage"[Title/Abstract])
AND (deterioration[Title/Abstract] OR shock[Title/Abstract]
OR "clinical prediction"[Title/Abstract])
```

**Q6_prediction_reporting_validation** — 总命中 19,898，取回 180

```text
("prediction model"[Title/Abstract] OR "machine learning"[Title/Abstract])
AND (TRIPOD[Title/Abstract] OR PROBAST[Title/Abstract] OR calibration[Title/Abstract]
OR "external validation"[Title/Abstract] OR "decision curve"[Title/Abstract]
OR "sample size"[Title/Abstract])
AND (clinical[Title/Abstract] OR diagnostic[Title/Abstract]
OR prognostic[Title/Abstract])
```

**Q7_MIMIC_transportability** — 总命中 960，取回 180

```text
("MIMIC-IV"[Title/Abstract] OR "MIMIC III"[Title/Abstract]
OR "Medical Information Mart for Intensive Care"[Title/Abstract])
AND ("external validation"[Title/Abstract] OR transportability[Title/Abstract]
OR generalizability[Title/Abstract] OR "dataset shift"[Title/Abstract]
OR multicenter[Title/Abstract])
```

**Q8_Chinese_language** — 总命中 374，取回 180

```text
(("heart failure"[Title/Abstract] OR "cardiogenic shock"[Title/Abstract])
AND (sepsis[Title/Abstract] OR "intensive care"[Title/Abstract]
OR deterioration[Title/Abstract] OR prognosis[Title/Abstract]))
AND chinese[Language]
```

最终 100 条另按 DOI 分 5 批执行：

```text
"<DOI_1>"[AID] OR "<DOI_2>"[AID] OR ... OR "<DOI_20>"[AID]
```

用于 DOI→PMID 精确反查。每个候选的独立 DOI、PMID、查询 URL 和结果状态均写入 `source_manifest.jsonl`。

### 3.2 Crossref

每式使用 `query.bibliographic=<query>&rows=80`，按 Crossref 默认相关性顺序取回。

| ID | 完整查询 | API 总命中 | 取回 |
|---|---|---:|---:|
| CR1_AHF_WHF | `acute heart failure worsening heart failure risk prediction treatment escalation` | 1,436,670 | 80 |
| CR2_CS_early_warning | `cardiogenic shock early prediction machine learning acute heart failure` | 7,078,545 | 80 |
| CR3_ICU_HD | `hemodynamic deterioration cardiovascular intensive care early warning` | 4,117,224 | 80 |
| CR4_dynamic_EHR | `dynamic prediction landmark electronic health record intensive care deterioration` | 8,812,687 | 80 |
| CR5_prediction_methods | `TRIPOD AI PROBAST AI calibration external validation prediction model` | 4,763,887 | 80 |
| CR6_transportability | `MIMIC external validation transportability clinical prediction model` | 8,166,525 | 80 |

最终 100 条均调用：

```text
GET https://api.crossref.org/works/<normalized-doi>
```

其中 96 条可由 Crossref 精确返回；4 条中文中华医学会/中文期刊 DOI 未被 Crossref 返回，改由 PubMed 加期刊官网/万方联合核验。

### 3.3 OpenAlex 补充检索

每式使用 `search=<query>&per-page=25&sort=relevance_score:desc`。

| ID | 完整查询 | API 总命中 | 取回 |
|---|---|---:|---:|
| OA1_AHF_CS_HD | `acute heart failure hemodynamic deterioration cardiogenic shock prediction` | 3,765 | 25 |
| OA2_HF_sepsis | `heart failure sepsis mixed shock fluid resuscitation` | 8,534 | 25 |
| OA3_dynamic_landmark | `dynamic prediction landmark electronic health record intensive care data leakage` | 513 | 25 |
| OA4_validation_transport | `clinical prediction model external validation calibration transportability` | 16,783 | 25 |

100 个出现中有 98 个唯一记录；与最终候选按 DOI 和标准化题名各重合 4 条。其余结果没有替代更直接相关、已通过 T1 核验的候选，因此未提升进入最终 100 条。

## 4. 去重、版本合并与 legacy 处理

去重键优先级：

1. 标准化 DOI：移除 `https://doi.org/`，转小写，清除尾随标点；
2. PMID；
3. PMCID；
4. arXiv ID；
5. 标准化题名 + 第一作者姓 + 年份；
6. 无 DOI 时，用标准化题名词元 Jaccard 相似度和第一作者辅助判断。

合并优先级：

1. 字段更完整的正式期刊记录；
2. 正式发表版优先于预印本；
3. PubMed/Crossref 主记录优先于 OpenAlex 补充记录；
4. 保留全部来源标签和版本关系事件。

流程计数：

- 主题检索取回出现：PubMed 1,363 + Crossref 480 = 1,843；
- legacy DOI 精确种子出现：13；
- 合计出现：1,856；
- 去重后广搜池：1,717；
- 去重/合并减少：139；
- 从广搜池进入候选：99；
- 精确题名/DOI 补齐的奠基性 landmarking 文献：1；
- 最终候选：100 条唯一 DOI、100 条唯一标准化题名。

legacy 处理：

- 旧目录提供 13 个 DOI 种子；
- 13 个均重新由 Crossref 精确反查，未继承旧文件的核验状态；
- 12 个进入最终候选；
- 1 个因相较配额内记录直接相关性较低而未进入 100 条；
- legacy 仅是种子来源，不是质量加分项。

曾发现并修正一个手工 DOI 错误：

- 错误：`10.1111/j.1467-985x.2007.00529.x`
- 正确：`10.1111/j.1467-9469.2006.00529.x`
- 正确 DOI 由 Crossref 精确题名检索确认；错误 DOI 未进入最终文件。

## 5. 两轮筛选流

### Pass 1：题名/元数据筛选

- 广搜唯一池：1,717；
- 进入候选：99；
- 排除：1,618；
- 另以精确 DOI 补齐 1 条奠基性方法文献；
- 最终题名/元数据候选：100。

排除理由由确定性题名/元数据规则生成，并逐条写入 `screening_exclusions.csv`：

| 排除理由 | 数量 |
|---|---:|
| 相比配额内记录直接相关性较低 | 771 |
| 主题相关性不足 | 462 |
| 儿童/妊娠人群 | 76 |
| 无转移性/外部验证重点 | 68 |
| 围术期、操作或邻近人群 | 62 |
| 无关临床领域 | 62 |
| 仅死亡结局且缺少早期恶化重点 | 57 |
| 通用预测方法但偏离当前问题 | 42 |
| 非纳入型文献格式 | 13 |
| 非人研究 | 5 |
| **合计** | **1,618** |

该排除统计是单人、规则辅助的题名/元数据筛选，不等同于双人独立系统综述筛选。

### Pass 2：摘要/元数据优先级筛选

- 100 条保留为候选；
- 40 条进入全文评估优先队列；
- 其中 25 条为临时核心证据集；
- 其中 15 条为首批 PDF 精读队列；
- 其余 60 条为保留候选。

`SI_choice=no` 后已完成 40 条的合法访问路径审计，其中 21 篇可在 Phase 2 完成主文文件级核验；19 篇仍需人工授权获取或没有授权 OA 主文。当前没有声称 40 篇均已完成内容级全文纳排，也没有把可获取性当作科学纳入标准。

## 6. 100 / 40 / 25 / 15 的选择依据

### 100 条候选的证据流配额

| 证据流 | 数量 |
|---|---:|
| AHF/WHF 结局定义与院内恶化 | 18 |
| AHF→心原性休克 | 18 |
| HF+sepsis / mixed physiology | 18 |
| ICU/CICU 血流动力学恶化 | 16 |
| landmark / dynamic EHR / leakage | 12 |
| TRIPOD+AI / PROBAST+AI / 校准 / 外部验证 | 12 |
| MIMIC→外部/中国医院可迁移性 | 6 |
| **合计** | **100** |

### 40 条全文优先队列

纳入全部核心 25，并增加 15 条用于：

- WHF 定义敏感性和发生时间；
- AHF→CS 的综述、分类和外部风险背景；
- HF+sepsis 的早期液体复苏、容量平衡和治疗冲突；
- 动态预测与 ICU 事件定义；
- 外部验证样本量、校准和 MIMIC-IV 数据集说明。

### 25 条临时核心集

满足以下至少一项：

- 直接定义 treatment-intensification–based WHF/HD；
- 直接研究 AHF 后续 CS 或 ICU/CICU HD；
- 直接研究 HF+sepsis 或 mixed septic-cardiogenic physiology；
- 对 landmark、信息泄漏、报告偏倚、校准或外部验证提供关键方法学约束。

核心 25 全部为 PubMed + Crossref 双 T1 核验。

### 15 条首批精读集

优先覆盖：

- 2 条 WHF 结局/传统风险模型；
- 4 条 AHF→CS 直接预测；
- 2 条广义 ICU/CICU HD；
- 4 条 HF+sepsis/mixed physiology；
- 1 条 landmark EHR 方法；
- 2 条 TRIPOD+AI / PROBAST+AI。

本阶段只选择 15 条，不生成 Paper Card、高光或笔记。

## 7. 题录核验质量

最终 100 条：

- PubMed + Crossref 双 T1：94；
- PubMed + 中文期刊官网/万方：4；
- Crossref 单 T1：2；
- 未核验：0；
- 核心 25 双 T1：25/25；
- 唯一 DOI：100/100；
- 唯一标准化题名：100/100。

中文 4 条：

1. PubMed PMID 39502048 + 官方期刊站；
2. PubMed PMID 33463505 + 中华医学会期刊网；
3. PubMed PMID 29216952 + 万方医学；
4. PubMed PMID 41331884 + 中华医学会期刊网。

`quality_grade` 是基于文献设计、来源核验和与当前问题相关性的临时分级，不是完整 RoB 结论。未读取全文前，无法可靠完成：

- 参与者选择偏倚；
- 预测变量测量时间；
- 结局盲法与治疗行为依赖；
- 缺失数据处理；
- 校准与过拟合；
- 资助和利益冲突。

## 8. 合法全文获取、失败状态与文件核验

Controller 选择 `SI=no` 后，40 条全文候选全部按 `--no-si` 执行 OA-only 路由。实际结果：

| 状态 | 数量 | 含义 |
|---|---:|---|
| `verified_main_pdf` | 21 | 合法 OA 主文 PDF 已下载并通过全部文件级核验 |
| `manual_authorized_retrieval_required` | 11 | OA/全文证据存在，但自动获取失败或官方数据集没有主文 PDF 对象；只能人工授权获取 |
| `no_authorized_pdf_found` | 8 | 审计路径中没有发现授权 OA 主文 PDF；未绕过付费墙 |
| **合计** | **40** | 每篇一行写入 `download_log.csv` |

已验证 21 篇的来源：

- 19 篇来自官方 PMC OA S3 中严格匹配 `<PMCID>.<version>.pdf` 的主文对象；
- 2 篇来自 BMJ 出版社 OA 主文地址；
- 每篇均只有一个本地主文 PDF，且 `si_requested=false`。

文件级验证：

- `%PDF` 文件头：21/21；
- MIME `application/pdf`：21/21；
- 可解析页数且页数大于 0：21/21；
- 前 5 页可提取文本：21/21；
- 题名词元匹配：21/21 为 1.000；
- DOI 文本匹配：21/21；
- bytes 与 SHA-256：21/21 已记录；
- 人工复核待定：0/21。

`download_log.csv` 对未获得主文的 19 篇保留空的 `local_path`、MIME、bytes、page_count、SHA-256，并在 `failure_or_manual_action` 中记录真实失败与后续人工动作。没有测试或绕过付费墙、DRM、登录或双因素认证。

## 9. 分布偏斜与覆盖限制

### 时间

| 时段 | 数量 |
|---|---:|
| 2007–2013 | 2 |
| 2014–2019 | 30 |
| 2020–2023 | 42 |
| 2024–2026 | 26 |

2014 年以后 98/100，符合“优先 2014 年以后、保留奠基性更早文献”的范围。

### 语言

| 语言 | 数量 |
|---|---:|
| English | 96 |
| Chinese | 4 |

`DISTRIBUTIONAL_SKEW_ADVISORY`：

- 维度：语言；
- 集中：English = 96/100（96%）；
- 含义：这是覆盖分布信号，不是单篇文献缺陷；
- 响应：已纳入 4 条可由 PubMed + 中文官网/万方核验的中文记录；CNKI/万方系统检索仍需机构环境下人工补查。

### 方法

最大单类为预测模型开发/验证 23/100；其次为回顾性队列 15/100。没有方法类别达到 70% 集中阈值。

### Venue

最高单一期刊各 4/100（American Heart Journal、European Journal of Heart Failure）。没有单一期刊或前 3 期刊达到 70% 集中阈值。

### 地域

多数题录元数据没有可靠的研究地点字段，不能据作者姓名、期刊或标题推断地域，因此不计算地域集中比例。可明确识别的中国相关信号仅包括 4 条中文文献和 2 条标题明确描述 MIMIC→中国队列外部验证的实例；这不足以替代对全部研究地点的全文核对。

## 10. 工具失败与修复记录

1. 系统 Python 的 PubMed/Crossref/arXiv 预检因本机证书链失败；按 `dependency_setup.md` 改用捆绑 Python 后三项均通过。
2. Crossref 第一次调用因 `select` 参数含不接受字段返回 HTTP 400；移除 `select` 后成功。
3. 13 个 PubMed 精确题名种子检索因标点/副标题严格匹配均为 0；最终改用 DOI `[AID]` 批量反查，98 个候选获得 PMID。
4. 学术检索 MCP 未挂载；按技能规则降级到官方公共 API 和 OpenAlex fallback。
5. 4 个中文期刊 DOI 未被 Crossref 返回；使用 PubMed 加期刊官网/万方核验。
6. 一条原拟中文记录的 DOI 当前返回 502，未满足中文官网硬门，已移出并由另一条可解析到官方期刊站的相关中文研究替换。
7. 未使用 Semantic Scholar：无 API key 情况下逐条 1 req/s 会增加延迟；T1 已覆盖全部候选，OpenAlex T2 已完成补充检查。
8. 系统 `PATH` 没有 Node；按工作区依赖清单改用捆绑 Node v24.14.0。下载器不支持 `--help`，返回 `unknown arg --help`，不影响按技能文档中的显式参数执行。
9. 下载器最初依据 PMC OA Web Service 的旧 FTP-PDF 地址尝试时，19 个可用主文候选返回 404。依据 PMC 官方 2026 数据分发说明，改用官方 `pmc-oa-opendata` S3 的统一对象结构，并只接受严格的 `<PMCID>.<version>.pdf` 主文命名；没有获取同一前缀中的 `mmc*`、`s001`、`wt*`、`ww*` 等补充 PDF。
10. OpenAlex 的一条 `best_oa_location.pdf_url` 实际指向 `.jpg` 图片，已由 URL 类型门和下载器内容检查共同拒绝；没有计为 PDF。
11. 出版社 OA 直链中的 Wiley、AHA、OUP、Nature 与部分机构库返回 403、HTML 挑战页、502 或网络失败；这些条目保留为人工授权获取，不使用非法镜像或绕过手段。

## 11. 限制

- 这不是完成态系统综述；40 篇已完成访问路径审计，但只有 21 篇完成主文文件级核验，内容级全文纳排仍需后续人工阅读。
- PubMed/Crossref 宽检索使用相关性截断，可能遗漏排名靠后的相关记录。
- Scopus、Web of Science、CNKI 未完成系统检索，是主要数据库覆盖缺口。
- 中文仅 4 条，不能代表完整国内证据。
- 题名/摘要阶段不能判定治疗变量是否发生在预测时点之后，也不能完成泄漏审计。
- 未完成全文级 COI、撤稿、勘误、样本重叠和模型复用检查。
- 没有在本阶段作“首次”“绝对没有同构研究”或其他无界新颖性结论。

## 12. 当前真实阻塞项与交接

Phase 2 没有未决 SI 门：

```text
SI_choice=no
SI_downloaded=0
status=Waiting review
```

真实未决项：

1. 11 篇需用户在合法授权环境下人工取得主文 PDF；不得自动绕过 403、挑战页、登录、DRM 或付费墙。
2. 8 篇在本轮 OA-only 审计中没有发现授权主文 PDF；若用户已有授权附件，只能在 Phase 3 由 ZoteroAgent 只读核实。
3. 用户报告 legacy 文章已经手动放入 Zotero，但该信息尚未核验：

```text
user_reported_legacy_articles_imported=true
verified=false
```

Phase 2 没有查询或修改 Zotero，也没有读取 `zotero.sqlite`。下一步只能由 Controller 审查 Phase 2 工件；本阶段停在 `Waiting review`。
