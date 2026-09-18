# MIMIC DHF提取来源覆盖登记表

版本：2026-09-16。用途：在正式SQL冻结前区分“来源已审查”“可执行但尚未运行”“项目当前不可用”，避免把目录检索结果误写成已经提取的数据。

## 研究对象和执行状态

研究对象为成人、首次符合选择过程的index ICU episode；先确定 episode、T0、T12 和 `[T0,T12)`预测窗，再按 A（HF锚点）+B（失代偿/充血）+C（客观或管理支持）构建DHF表型。MIMIC计划作为开发/内部验证库，不要求每例有心超；本院床旁心超选择分母的差异在外部验证中单独报告。

当前环境已完成目录和字段资源验证，但没有在本地提供可直接查询的患者级MIMIC数据库连接。因此本登记表的 `execution_status` 为 `not_run` 或“已有BigQuery导出”，不把目录候选或旧运行结果当成新的冻结提取结果。

## 来源覆盖表

| source_id | 模块/来源 | 计划字段或概念 | 研究用途 | 事件时间 | 状态 | 当前限制与去重规则 |
|---|---|---|---|---|---|---|
| M1 | `mimiciv_icu.icustays` | `subject_id, hadm_id, stay_id, intime, outtime, first_careunit, last_careunit` | ICU episode、T0/T12、再入ICU分段 | `intime/outtime` | `reviewed_included; not_run` | 以`stay_id`为episode主键；同次住院多段不合并；时间相同按stay_id稳定排序 |
| M2 | `mimiciv_hosp.admissions/transfers/services` | 入院、转科、出院、死亡和服务变化 | episode边界、死亡/出院核对、竞争事件 | `admittime, dischtime, deathtime, event time` | `reviewed_included; not_run` | 不以普通病房转科替代ICU出入；同一事件保留来源优先级 |
| M3 | `mimiciv_icu.chartevents/datetimeevents` | 生命体征、呼吸支持、床旁观察、尿量 | T0-T12预测器和治疗强度 | `charttime, storetime` | `reviewed_included; not_run` | 以charttime为临床时间，storetime仅QC；按item、stay、时间和优先级去重 |
| M4 | `mimiciv_hosp.labevents` + `d_labitems` | 乳酸、血气、BNP候选及单位 | 失代偿/休克代理和预测器 | `charttime`（需核实语义） | `reviewed_included; audit_sql_ready; not_run` | 已生成`MIMIC_LABEVENTS_TRUNCATION_AUDIT_V1.sql`；须保留原值、单位、异常标志，审计比较符号、itemid和单位分布后才能冻结实验室特征 |
| M5 | `mimiciv_icu.inputevents/procedureevents/ingredientevents` | 血管活性药、机械循环/呼吸支持、治疗过程 | C域管理支持、结局升级 | `starttime, endtime, charttime` | `reviewed_included; not_run` | 订单、泵速、实际输入分开；总剂量不反推泵速/NEE；同一事件按event_id去重 |
| M6 | `mimiciv_hosp.prescriptions/pharmacy/poe` | 药物开停、途径和处方 | 治疗组成和敏感性分析 | `starttime, stoptime` | `reviewed_included; not_run` | 处方不是执行；若无eMAR只能作为暴露代理并标记代理状态 |
| M7 | `mimiciv_hosp.emar/emar_detail` | 给药执行、执行时间、剂量和途径 | 执行级治疗暴露和结局判定 | `charttime` | `reviewed_included; not_run` | 需与处方/药品字典连接；当前未形成新导出 |
| M8 | MIMIC-derived concepts（如`mimiciv_derived.bg`） | 血气和派生实验室 | 交叉QC，不作为唯一来源 | 派生表定义时间 | `reviewed_included; not_run` | 与原始labevents对账，保留原始来源；不能静默替代原始表 |
| M9 | MIMIC-IV-Note | 病历文本、SOAP、出入ICU语义 | HF锚点、否定/替代诊断 | `charttime/chartdate`依文书定义 | `known_excluded_source; unavailable` | 当前提取skill不含Note；需单独授权/下载后才能纳入，不能把缺失当阴性 |
| M10 | MIMIC-CXR/CXR-JPG | 胸片图像/报告 | 肺充血及替代诊断 | 检查/报告时间依来源定义 | `known_excluded_source; unavailable` | 当前skill明确排除；项目已有BigQuery报告导出，须以独立导出QC对接，不写成该skill已执行 |
| M11 | MIMIC-IV-Echo | 心超检查及结果 | 表型支持和严格敏感性层 | 检查/报告时间依来源定义 | `unresolved; not_run` | 先核对版本、字段和与ICU stay的链接；不得因6例strict draft直接设为主队列硬门槛 |

## 提取合同和质控门

- 主键：`stay_id`（episode级）；患者级汇总只能在episode裁决之后生成。
- 时间：T0优先使用`icustays.intime`并与转运/护理证据核对；预测器严格限制在`[T0,T12)`，表型支持可使用`[T0-24h,T0+12h)`，报告时间与采样/执行时间差异列为敏感性分支。
- 单位和结果：原始字符串、单位、比较符号、异常标志和来源行必须保留；`>xx/<xx`用边界和删失标志保存，不能直接取精确值。
- 缺失：结构性缺失仅在变量定义明确时填0；测量性缺失采用训练折内MICE；心超、胸片、CT不做数值插补。
- 事件：目标事件、alive ICU discharge竞争事件和删失在同一episode时间轴上重建；T12前已发生或观察不完整者不静默编码为无事件。

## Gate状态

```text
semantic_gate = pass（研究术语、DHF三域及否定/替代诊断规则已登记）
episode_first_gate = pass（stay_id episode及再入ICU分段规则已登记）
anchor_window_gate = pass（T0/T12/T60及边界已登记）
eligibility_gate = draft（正式SQL尚未在患者级MIMIC快照运行）
source_coverage_gate = partial（M9/M10已知排除，M11待版本和链接核验）
contract_status = draft
sql_status = blocked_until_snapshot_and_schema_check
source_review_status = incomplete
execution_status = not_run（本文件登记的新增提取）
validation_status = partially_validated（目录资源通过，患者级结果未验证）
case_ascertainment_status = not_established
```

实验室截断审计模板已完成，但尚未在 BigQuery 快照运行；因此 `M4` 的来源规划可以继续，最终 lab feature freeze 仍被阻塞。

## 下一次MIMIC运行的最小输出

运行前先补齐数据库快照、MIMIC版本、BNP/乳酸项目编码、单位和检验时间语义；随后输出 `episode_master`、`dhf_domain_evidence`、`predictor_t12`、`outcome_t12_t60`、`missingness_and_units_qc` 五张表及输入指纹。只有五表通过行数、主键、时间边界、单位和重复值QC后，才允许将 `contract_status` 改为 `frozen`。
