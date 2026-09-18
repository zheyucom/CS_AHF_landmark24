# 任务报告：双库队列口径与数据清洗合同

日期：2026-09-16（CST）

## 本次完成

1. 修订研究总览中的“待导师决定”：将两库主队列、`>xx/<xx`检验值和医嘱执行代理列为三项推荐默认口径；第二位标注者kappa降为影响验证强度的独立决定。
2. 在开题方法初稿新增“数据清洗、测量误差与缺失值”小节，明确原始值保留、单位缺失、比较符号、异常值、结构性/测量性/信息性缺失、折内MICE、选择性心超不插补及报告时间代理。
3. 将缺失数据和心超方案升级为v1.2，补充比较符号、单位推断和异常值合同。
4. 新增`MIMIC_DHF_SOURCE_COVERAGE_LEDGER_20260916.md`，登记episode、实验室、用药、eMAR、文本、CXR和Echo的覆盖状态；明确当前MIMIC extraction skill目录验证通过，但本地新增患者级提取尚未运行。
5. 修正`prepare_case_review_20260916.py`默认读取修正后运行`20260916_semantic_corrected`，重新生成368例病例来源缓存（235例优先语义/风险集、91例T12观察链、42例HF锚点；15,105条文书、528条护理备注），避免旧版T0工作台混入当前复核。
6. 在总览中补回Gate3 45例语义优先队列的已完成状态（8例保留候选、37例保守排除、0例未决），并明确其仍是预审核证据而非全量临床金标准。

## 当前可以确定的研究口径

- MIMIC：多域DHF operational phenotype作为开发/内部验证主队列，心超为支持域和敏感性层。
- 本院：8,385名为床旁心超选择后的成人候选分母，不声称全院成人ICU；同窗心超结果可用层用于严格敏感性分析。
- `>xx/<xx`：保留边界和删失标志；阈值只有在整个区间位于一侧时成立；BNP `>5000`不能当精确值或单独确诊DHF。
- eMAR暂缺：有效医嘱区间可作预先登记的治疗暴露代理，但不从总剂量推导泵速或NEE；eMAR取得后在同一冻结队列重跑敏感性分析。

## 尚未冻结的内容

- 院内235例优先复核、91例T12观察链和42例HF锚点尚未完成临床裁决。
- MIMIC正式患者级提取仍需数据库快照、项目编码、单位和时间语义核验。
- 因此目前没有正式`cohort_freeze.csv`、`outcomes_frozen.csv`或可用于论文的最终性能数字。

## 复现与检查

- 研究总览：[RESEARCH_DASHBOARD.md](../RESEARCH_DASHBOARD.md)
- 队列决策登记：[COHORT_DECISION_REGISTER_20260916.md](../COHORT_DECISION_REGISTER_20260916.md)
- MIMIC来源登记：[MIMIC_DHF_SOURCE_COVERAGE_LEDGER_20260916.md](../MIMIC_DHF_SOURCE_COVERAGE_LEDGER_20260916.md)
- 语义回归测试：`python3 -m unittest discover -s project_control -p test_internal_dhf_semantics_20260915.py`
- 来源缓存：`python3 project_control/prepare_case_review_20260916.py --base project_control/internal_validation/20260916_semantic_corrected`

## 2026-09-16 后续补全

研究者已确认院内 BNP 单位为 `pg/mL`、乳酸单位为 `mmol/L`。本轮新增并锁定：

1. `INTERNAL_DHF_VARIABLE_DICTIONARY_V1.csv`：覆盖当前候选预测器、DHF A/B/C 证据、时间、结局、竞争事件和缺失语义；单位状态分为 `confirmed_user`、`confirmed_dictionary`、`manual_check_required`、`unknown`。除 BNP 和乳酸外，未唯一确认的单位不用于正式阈值排除。
2. `DHF_SEMANTIC_RULE_DICTIONARY_V1.md`：明确 HF 锚点、失代偿/充血、支持域、否定、不确定、既往史、模板语句、替代诊断及多次 ICU episode 时间归属；规则词典在全量表型冻结前属于阻塞项。
3. `internal_validation/20260916_case_review/AI_REVIEW_PROVENANCE.json`：登记 11 例 AI 预审核的输入、输出、来源行号、QC 和独立金标准状态。模型标识、prompt 版本和完整运行参数当时未记录，已明确标记 `not_recorded`，不得回填猜测。
4. `MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql` 与对应说明：审计 MIMIC `labevents` 的比较符号、区间、文本值、单位和 itemid 分布。当前执行状态为 `not_run`，待最终 BigQuery 导出后运行。

### 五项工作的门控结论

- 变量字典：冻结前必须完成（`blocking`）。
- 语义规则词典：冻结前必须完成（`blocking`）；独立 kappa 仅在论文要报告一致性时要求第二位盲法标注者，重复同一标注者不构成独立 kappa。
- 医嘱代理验证：结局冻结前必须完成抽样一致性审计（`blocking_for_outcome_freeze`）；当前仍明确是医嘱代理，不等同 eMAR。
- AI 判读留痕：不阻塞当前工程预审核，但论文和审计必须补全（`nonblocking_but_required`）。
- MIMIC 截断审计：不阻塞当前来源规划，但阻塞最终实验室特征冻结（`blocking_for_final_lab_freeze`）。

因此，当前可以继续做来源覆盖、规则预审核和 MIMIC SQL 准备；在上述阻塞项完成前，不生成或宣称正式 `cohort_freeze.csv`、`outcomes_frozen.csv` 或最终模型性能。
