# CS_AHF 文献补更与 MIMIC 清洗 Skill 设计

日期：2026-09-17

## 1. 目标与分阶段边界

本工作分三阶段顺序执行，避免把文献综合、项目决策和工具开发混成一次不可审计的修改。

1. 补齐 Zotero 子集合 `00_首批精读15_CS_AHF`（key `A63I4DT4`）自 2026-07-30 后的文献卡、知识地图和文献周报。
2. 检索近期相关临床预测、DHF/血流动力学恶化、HF 合并脓毒症及 MIMIC 清洗方法，区分可采用、待验证和仅供参考的方法。
3. 创建可测试、可版本化、可分享的 `mimic-iv-data-cleaning` Codex Skill，并形成以后扩展到其他数据库的适配模式。

本工作不修改 Zotero 数据库，不覆盖人工总结、临床判断或历史周报，不把自动整理内容冒充人工金标准，也不在未通过门控前生成最终队列、事件数或模型性能。

## 2. 第一阶段：7 篇文献分层补更

### 2.1 范围

深度精读并按现有 12 章节模板补齐：

- Pirracchio 2008：脓毒性休克中的 BNP 清除。
- Girouard 2024：心衰临床与科研 NLP 应用。
- Zhuang 2024：脓毒症相关急性心衰连续识别与 LSTM。

建立有全文证据的间接参考卡：

- Zhai 2026：慢性心衰合并肺部感染 ICU 死亡预测。
- Sun 2026：MIMIC-IV ICU 心衰住院死亡预测。
- Feng 2025：ICU 急性心衰 AKI 动态列线图。

刷新既有卡：

- Gao 2026：心血管 ICU 血流动力学恶化早期预警。

为避免与现有最大编号 `R084` 冲突，新卡固定编号如下：

- `R085` Zhai 2026（Zotero key `V2TFV7Q6`）。
- `R086` Sun 2026（Zotero key `2VII7HIU`）。
- `R087` Girouard 2024（Zotero key `Y5RU8DL9`）。
- `R088` Zhuang 2024（Zotero key `G8M793SR`）。
- `R089` Pirracchio 2008（Zotero key `357TRC8L`）。
- `R090` Feng 2025（Zotero key `NX3VCU3R`）。

### 2.2 数据流与写入边界

1. 从本地 Zotero PDF、题录、批注和 DOI 读取证据。
2. 现有同步器只维护 `zotero-sync:start/end` 区块；人工内容不被覆盖。
3. 新卡沿用 `templates/literature-note-template.md`，保留 `zotero_item_key`、DOI、来源状态和证据边界。
4. 无法由全文核实的字段写为“未报告/待复核”，不得依据摘要或常识补造。
5. 更新 `Literature Index.md` 和 `CS_AHF 文献知识地图.md` 时只增加有证据的链接、结论及适用边界。
6. 知识地图当前仍写有旧 `2,424/334`、elastic-net 主模型和旧 `0-12 h → 12-60 h` 表述；更新时必须以 `project_control/RESEARCH_DASHBOARD.md` 的 2026-09-16 状态为事实入口，将旧数字和旧模型口径明确降级为历史探索，不得继续当作当前研究合同。

### 2.3 周报与项目影响输出

新建 `notes/literature/周报/2026-09-17.md`，覆盖 2026-07-31 至 2026-09-17，不覆盖 2026-07-30 历史周报。周报新增以下内容：

- 新证据对现有结论的支持、冲突或条件差异。
- 对 DHF 多域表型、early-sepsis 亚组、文本证据抽取、T12 时间合同、治疗升级结局、竞争风险和外部验证的影响。
- “改变当前设计 / 需要新增敏感性分析 / 只作讨论或方法学对照”三级行动矩阵。
- 对未来 7 天项目工作的具体帮助及不应改变的既定合同。

### 2.4 第一阶段验收

- 7 个目标 Zotero key 均可追溯到对应 Obsidian 卡。
- 3 张深度卡章节完整；3 张间接卡明确适用性边界；Gao 卡完成与当前方案的重新对齐。
- 同步脚本二次运行无非预期覆盖，周报生成脚本成功且历史周报未变。
- 所有引用数字可回到 PDF 页码、Zotero 高光或明确的原文位置。
- 文献知识地图不再把旧 `2,424/334` 或未冻结模型写成当前事实，并与研究 Dashboard 的表型、竞争风险和冻结门控一致。

## 3. 第二阶段：近期证据与公开清洗方法检索

### 3.1 检索主题

- 2024-2026 年 DHF、worsening HF、hemodynamic deterioration、HF + sepsis、动态/landmark 预测及竞争风险。
- MIMIC-IV 临床预测的数据清洗、变量构建、外部验证、可复现性和数据泄漏控制。
- MIT-LCP `mimic-code` 官方派生概念、论文附属代码和公开复现仓库。
- 对当前缺口有直接意义的早期经典文献不受年份限制。

### 3.2 证据分级

- **可直接采用**：与当前数据版本、变量语义和时间合同兼容，并有代码或可复核定义。
- **需本项目验证**：方法合理，但需用本项目快照、单位、itemid、结局或人群重新审计。
- **仅作参考**：结局、人群、时间窗或数据源不一致，不进入主分析规则。

所有新方法必须注明来源、MIMIC 版本、队列单位、时间窗、结局、验证层级及代码可用性。论文中的方法不因“已发表”而直接升级为本项目规则。

## 4. 第三阶段：`mimic-iv-data-cleaning` Skill

### 4.1 形式与位置

首次实现安装到 `~/.codex/skills/mimic-iv-data-cleaning`，包含 `SKILL.md`、`agents/openai.yaml`、`scripts/`、`references/` 和最小匿名测试夹具。目录保持独立、无患者级数据，可整体发布到 GitHub 后供他人通过 Skill Installer 安装。

未来其他数据库不硬塞进本 Skill。先抽取稳定的通用临床清洗合同，再建立 `eicu-data-cleaning`、`omop-data-cleaning` 等数据集适配 Skill。

### 4.2 核心工作流

1. **版本与来源合同**：确认 MIMIC 版本、表、schema、episode 主键、时间字段及官方概念版本。
2. **变量合同**：每个 analyte/变量必须登记精确 `itemid`、预期 `fluid`、`category`、允许单位、来源表、官方 derived concept 和排除项。
3. **原始值保留**：保存 `value`、`valuenum`、单位、比较符号、上下界、flag、comments、`specimen_id` 和来源行键。
4. **时间与 episode**：先冻结患者/住院/ICU stay，再执行每变量时间窗；不得把结果可用时间、采样时间和录入时间混为一谈。
5. **重复与聚合**：说明同一 specimen、同一时点和多次测量的去重及 first/last/min/max 规则。
6. **缺失与来源差异**：区分未测、派生概念漏收、连接失败、超窗和结构性不可用；原始表与官方 derived concept 双向对账。
7. **泄漏与合理性门控**：检查预测时点后信息、结局组成变量、单位不一致、错误标本和静默截断。
8. **输出审计**：生成 itemid × fluid × category × unit × source 的纳入/排除表、行数变化、异常样例和未决问题。

### 4.3 必须固化的首批回归案例

#### 血液尿素氮

- BUN 主合同采用官方 `mimiciv_derived.chemistry` 对应的 `itemid=51006`，其定义为 `UREA NITROGEN | CHEMISTRY | BLOOD`。
- 任何从原始 `labevents` 按 label 搜索的查询，必须同时验证精确 itemid、`fluid` 和 `category`；其他体液、尿液或未确认项目进入排除审计，不能凭数值范围混入。
- 测试夹具必须包含同名但错误 fluid 的污染行，并断言其被排除。

#### 乳酸来源缺口

- 保留本项目已发现的回归案例：`mimiciv_derived.bg` 曾漏掉原始 `labevents itemid=50813` 中 550 个有效 stay。
- Skill 不得假设 derived concept 等于完整原始来源；必须输出 raw-only、derived-only 和 both 三类对账。

#### 截断值与单位

- `>x`、`<x` 和区间值保留边界及删失类型，不改写成精确值。
- 单位缺失或多单位项目不得凭数值范围静默转换。

### 4.4 受控学习机制

Skill 不进行无审查的自我改写。每个新发现按以下状态流转：

`observed → sourced → fixture-added → regression-tested → active`

每条规则必须包含：触发案例、错误风险、权威或可复核来源、适用的 MIMIC 版本、修复规则、最小失败夹具、测试结果和版本记录。证据不足的规则保持 `proposed`，只在报告中提示，不参与数据过滤。

### 4.5 验证与发布

- 使用 Skill Creator 的 `quick_validate.py` 验证目录结构和 frontmatter。
- 对变量合同、错误 fluid、单位、删失值、重复 specimen、时间泄漏和 raw/derived 对账运行自动测试。
- 用当前项目 SQL 做只读审计，列出违规项；未经用户确认不批量改写既有 SQL。
- 新线程前向测试必须只给 Skill 和原始任务，不泄露预期答案。
- 发布物不包含患者级数据、密钥、本机绝对路径或项目私有结果。

## 5. 已知现状与需修复问题

- 当前 `sql_v4_2` 和 `sql_v3_2` 的 BUN 来自 `mimiciv_derived.chemistry`，官方定义使用血液 `itemid=51006`；当前主路径并非按名称混合所有体液。
- `project_control/MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql` 通过 label 正则选择 analyte，但尚未强制 fluid/category/itemid 合同；这是未来原始表提取的真实污染风险。
- 2026-09-16 任务报告声称 `mimic-iv-data-extraction` Skill 已验证，但本机 `~/.codex/skills` 和项目目录当前均无该 Skill。后续报告必须区分“曾在某会话检查”与“当前已安装可调用”。
- 当前项目目录不是 Git 仓库，无法在本目录提交设计文档；在不擅自初始化仓库的前提下，只能保存文件并报告该限制。

## 6. 总体验收标准

- 文献补更、近期检索和 Skill 开发各自有独立产物、证据与验证记录。
- 任何会改变分析数据的规则都具备来源、测试和版本，不依赖聊天记忆。
- 同一输入快照和配置可重复得到同一清洗结果与排除审计。
- Codex 在收到“MIMIC 清洗/提取/特征构建”请求时能触发该 Skill，并主动检查标本、itemid、单位、时间、重复、缺失和泄漏，不再等待用户逐项提醒。
