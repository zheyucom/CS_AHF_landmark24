# 院内 DHF 最小数据补提请求（v2026-09-14）

## 目的

2026-09-15状态更正：本文件原来的补提清单已被用户提供的数据与语义确认覆盖，现归为历史字段说明，不是当前任务或数据管理员必办事项。先用现有文书、护理、检查检验及医嘱重建episode、表型和结局；正式检查/采样时间与eMAR是后续增强。尚未冻结代表派生与验证未完成，不能一概写成原始数据缺失。最新进度见`RESEARCH_DASHBOARD.md`。

## 统一主键与时间

- 主键：`patient_id`、`visit_id`、`icu_episode_id`（若没有 episode_id，必须提供可排序的 ICU episode 序号）。
- 时间格式：`YYYY-MM-DD HH:MM:SS`，注明时区。
- 保留原始来源时间字段及来源表名；不要用文书创建时间替代事件时间。
- 同一次住院多次 ICU 进出必须逐 episode 提供，不能只保留一次住院的最早或最晚时间。

## A. ICU episode 与结局（必需）

每个 index ICU episode 一行：

1. `icu_intime_actual`：优先护理记录中明确“由某处进入 ICU”的时间；若缺失，提供“入住 ICU/入 ICU 记录”正文时间，并保留 `icu_intime_source`。
2. `icu_outtime_actual`：明确转出 ICU 的时间，并保留 `icu_outtime_source`。
3. `icu_disposition`：`alive_icu_transfer`、`icu_death`、`hospital_death`、`discharge_home_or_other`、`auto_discharge`、`unknown`。
4. `death_time`、`alive_icu_transfer_time`、`hospital_discharge_time`（能提供则全部提供）。
5. `disposition_source_note_id`、`disposition_source_text_span` 或等价可追溯来源。

需要特别标记：先转出 ICU 后再次转入 ICU 的患者。index episode 只按预先定义的首次成人 ICU episode 纳入，但后续 episode 仍需提供，以便审计误把后续 ICU 事件合并到 index episode 的风险。

## B. DHF 语义证据（必需）

仅限 index ICU episode 的 `T0-24 h` 至 `T12` 可见证据，另保留来源时间：

- 全部 ICU 相关文书正文和 `note_id`、`charttime`、`sign_time`、`document_type`：入 ICU 记录、出 ICU 记录、ICU 转病房/转出记录、每日查房 SOAP、会诊、死亡记录、出院记录。
- 症状/体征 NLP 候选：呼吸困难、端坐呼吸、湿啰音、颈静脉怒张、外周水肿、低氧恶化、低灌注；同时保留否定、推测、模板和替代诊断上下文。
- HF anchor 候选：急性心衰、心力衰竭、心功能不全、心源性休克、心肌病、严重瓣膜病或显著心室功能异常。
- 替代/并存诊断：肺炎、ARDS、误吸、肺出血、创伤、术后状态、脓毒症、肾功能不全等。

输出可以是全文或按候选语句窗口导出，但必须能回溯到原文档、时间和原文片段；不得只给一个不可解释的二分类标签。

## C. 检验、检查和治疗强化（必需）

- BNP/NT-proBNP：报告时间、数值、单位、参考范围、检验状态。
- 床旁心超/TTE/TEE：报告时间、所见/结论全文，EF、右室、舒张功能、瓣膜、肺高压、IVC 等结构化字段（如有）。
- 胸片/胸部 CT/CTA：检查时间、报告可见时间、全文；单独记录肺水肿/肺充血、胸腔积液、PE、肺炎/ARDS 等。
- 用药：药品、途径、剂量/单位、开嘱时间、停嘱时间、实际给药时间或 eMAR 执行状态；若没有执行级记录，明确标记为医嘱区间，不能冒充实际执行。
- 呼吸/循环支持：给氧方式及浓度、无创/有创通气、升压药/正性肌力药、液体管理；记录开始、停止和每次升级时间。
- 护理时间序列：乳酸、尿量（保留记录区间起止时间和累计量）、血压/心率/呼吸频率/SpO2；至少覆盖 `T0-T12` 和 `T12-T60`。

## D. 最小输出格式

建议按以下 5 张表输出，均使用上述主键：

| 表 | 一行代表 | 关键字段 |
|---|---|---|
| `icu_episode` | 一个 ICU episode | 入/出 ICU、episode 序号、转归、死亡/转出时间 |
| `icu_note_evidence` | 一份文书或证据片段 | 文书类型、时间、正文/片段、来源 ID |
| `diagnostic_evidence` | 一项检验/检查 | 类型、采集/检查/报告时间、结果、单位、全文 |
| `treatment_execution` | 一次执行或连续支持区间 | 治疗、途径、剂量、开始/停止/执行状态 |
| `icu_timeseries` | 一个时间点或累计区间 | 变量、时间/区间、值、单位、来源 |

## 数据管理员完成标志

只有同时满足以下条件，才进入全量表型冻结：

1. 8,385 个成人 index episode 均能连接到 episode 或明确标记缺失；
2. 多次 ICU episode 可区分；
3. T0/T12 所需证据均带来源时间；
4. 结局能区分 ICU 内死亡、存活转出和仍在 ICU 的删失；
5. 治疗升级至少有可审计的执行时间，或明确哪些病例只能使用医嘱区间；
6. 不能连接、时间冲突和文本缺失均有单独状态码，不能静默删除。

## 当前不会改变的决定

- 成人 index ICU 分母固定为 8,385（女 2,842，男 5,543），患者 9204020 已排除。
- `T0` 优先护理“进入 ICU”事件，其次入住 ICU 文书正文，结构化入区时间仅作代理。
- `T12=T0+12 h`；报告时间窗口为 `[T0-24 h,T12)`。
- DHF 继续采用 A（HF anchor）+ B（失代偿/充血）+ C（支持域）；单独 BNP、心超、影像或利尿剂不构成 DHF。
- 所有自动标签在人工裁决前均为 `draft/weak label`。
