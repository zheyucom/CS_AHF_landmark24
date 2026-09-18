# Dependency Setup & Readiness Audit

审计时间：2026-07-29T20:29:23+08:00  
审计阶段：Phase 1 — Controller Console  
总体结论：**Conditionally ready / Waiting review**

## 1. 环境摘要

| 组件 | 检测结果 | 状态 | 后续动作 |
|---|---|---|---|
| 系统 Python | 3.14.3 | 可运行，但缺少本流程常用模块且直接联网出现证书链失败 | 不作为默认检索运行时 |
| 项目 `.venv` | Python 3.13.9；含 `requests`、`PyYAML`、`pandas` | 可用于项目分析；缺 `fitz`、`pdfplumber`、`pypdf` | 不修改现有环境；文献流程优先使用 Codex runtime |
| Codex bundled Python | 3.12.13；含 `pdfplumber`、`pypdf`、`pandas` | 可用 | 作为默认文献/PDF运行时 |
| PubMed E-utilities | bundled runtime preflight OK | Ready | Phase 2 重新记录检索时间与命中数 |
| Crossref REST | bundled runtime preflight OK | Ready | Phase 2 使用 |
| arXiv API | bundled runtime preflight OK | Ready | 仅在相关方法学/预印本时使用 |
| Pandoc | 3.8 | Ready | 可用于后续格式转换 |
| `pdftotext` | 未发现 | Optional missing | 使用 `pypdf`/`pdfplumber`；必要时再安装 |
| Zotero Desktop | 9.0.4 | Ready | Local API/Connector 均为 200 |
| Obsidian Desktop | 未发现 | Blocker for direct vault integration | 用户安装或提供现有 vault 绝对路径 |
| Git | 2.50.1 | 可用 | 源项目不是 Git 仓库；未启用 checkpoint |

## 2. Python 运行时细节

### 系统 Python

```text
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
Python 3.14.3
requests=false
yaml=false
fitz=false
pdfplumber=false
pypdf=false
pandas=false
```

使用系统 Python 运行学术检索 preflight 时，PubMed、Crossref、arXiv 均因本机证书链验证失败。不得通过关闭 TLS 校验绕过该问题。

### 项目虚拟环境

```text
/Users/zheyu/Desktop/CS_AHF_landmark24/CS_AHF_hemodynamic_deterioration_ml_project/.venv/bin/python
Python 3.13.9
requests=true
yaml=true
fitz=false
pdfplumber=false
pypdf=false
pandas=true
```

不向该环境擅自安装文献工作流依赖，以免影响现有建模项目的可复现性。

### Codex bundled runtime

```text
/Users/zheyu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
Python 3.12.13
pdfplumber=true
pypdf=true
pandas=true
```

使用此 runtime 执行 `nature-academic-search/scripts/preflight.py`：

```text
PubMed E-utilities : OK
CrossRef REST      : OK
arXiv API          : OK
3/3 endpoints reachable
```

因此 Phase 2 可以使用 bundled runtime，而不需要关闭证书验证。

## 3. Zotero 连接

只读状态检查结果：

```text
profile: /Users/zheyu/Library/Application Support/Zotero/Profiles/hhgf4ake.default
local_api_enabled_pref: true
api_running: true
api_status: 200
connector_running: true
connector_status: 200
base_url: http://127.0.0.1:23119
```

当前选中目标：

```text
library: 我的文库
collection: #心衰早期预测
collection key: 4EMWVUHV
```

Phase 1 没有读取 Zotero 条目、执行重复检测、导入题录或链接附件。Phase 3 只通过 Local API 做只读库存与验证，不访问 `zotero.sqlite`。

## 4. Obsidian

检查范围：

- `/Applications/Obsidian.app`
- `/Users/zheyu/Documents`
- `/Users/zheyu/Desktop`
- 常见 iCloud Obsidian Documents 路径
- Spotlight 中名为 `.obsidian` 的目录
- 常见 Obsidian `obsidian.json` 配置路径

结果：没有发现应用、vault 或配置。  
结论：不影响 Phase 2–3，但会阻止 Phase 4 的直接 vault 写入。

## 5. Companion skills

| Skill | 状态 | 版本/替代 | 安全说明 |
|---|---|---|---|
| `codex-literature-workflow` | 未安装；未找到可核验的同名公开来源 | 本 Controller 按用户消息中的阶段门要求实现，不冒充该 skill | 不执行未知安装脚本 |
| `academic-research-suite` | **已完整安装**；下一轮任务生效 | adapter 0.1.22；仓库审计 commit `f8d6b061efe98564a3f554c917fce66dcef6ca54`；1,140 files | Codex hook 默认关闭；未启用 hook；未运行仓库脚本 |
| `nature-academic-search` | 已安装且 preflight 3/3 | 作为多源检索和引用管理的可验证辅助/后备 | Phase 2 才执行真实检索 |
| `zotero:Zotero` | 已安装且连接可用 | Local API 只读；用户控制写入 | 禁止直接写 `zotero.sqlite` |
| `zotero-linked-attachments` | 未安装；未找到可核验的同名来源 | Phase 3 可基于已审计 Zotero 接口生成透明、用户手动运行的脚本 | 当前不安装未知同名代码 |
| `research-lr-ra` | 未安装；未找到可核验的同名来源 | 可选项，暂不阻塞 | 不擅自替换为不明第三方实现 |

`academic-research-suite` 安装来源：

```text
https://github.com/Imbad0202/academic-research-skills-codex
installed path: /Users/zheyu/.codex/skills/academic-research-suite
adapter version: 0.1.22
SKILL.md sha256: cbd0039781d86992e06c1863f3e03a6de3cb98d46bfdb600b4810683fa0238fd
manifest.json sha256: 29bfe7c35562e22b7abcfb20560b60a2ae64e174668fe7d1b8938ebf1393aacb
```

安装前做了只读文件、可执行脚本、敏感模式、manifest 和 hook 配置审计；安装目录与审计 checkout 无差异。该 skill 会从下一轮任务起进入 Codex skill 发现范围。

## 6. PDF 与页码证据准备度

- bundled runtime 提供 `pypdf` 与 `pdfplumber`，可逐页提取文本。
- `fitz`/PyMuPDF 和 `pdftotext` 当前不可用，但不是硬性依赖。
- Phase 4 必须对每份 PDF 做可读性/加密/页数/哈希 preflight；解析失败时不得生成伪页码。
- 只有 PDF 页码可核验的内容才能标记为 `page_evidence_verified=true`。

## 7. 阻塞项

进入 Phase 2 前：

1. 用户确认检索数量、语言、时间范围和 Zotero collection。
2. 用户明确设置 `user_scope_confirmed=true`。

进入 Phase 4 前：

3. 用户提供 Obsidian vault 绝对路径，或明确选择“暂不接入 Obsidian”。

当前不需要用户修复系统 Python 的 TLS；已验证可使用 Codex bundled runtime 安全联网。
