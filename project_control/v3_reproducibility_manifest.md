# v3 可复现性清单

## 事实源优先级

1. MIMIC 原始表与官方 derived 表。
2. 经审阅、版本化的 v3 SQL。
3. v3 原始导出 CSV 及 SHA-256。
4. 冻结 Python config、脚本与依赖版本。
5. 同一 run 生成的 QC、模型、表、图和报告。

旧派生表、旧 CSV、README 数字和手工笔记只能用于差异核对，不能反向修改
v3 结果。

## 必需 SQL 模块

| 模块 | 目标 | 当前状态 |
|---|---|---|
| 001 | 新 schema、run manifest、cohort flow | 完成；每次仅重建 `study_ahf_v3` |
| 010-020 | 成人首次 ICU、HF ICD candidate | 完成；Navicat 原件已归档 |
| 061-062 | strict AHF12、landmark12、early sepsis12、pre12 shock | 完成 |
| 063-064 | 结局组件与主/次结局 | 完成 |
| 070A-070G | 0-12 h 基础特征与 modeling dataset v1 | 完成 |
| 079A | 患者级事件时间审计 | 完成；标签/时间 mismatch = 0 |
| 080A/080G | 动态生命体征负荷与 modeling dataset v2 | 完成；当前主建模输入 |
| 081A | 结构化心超可得性审计 | 完成；不进入当前主模型 |

## 每次运行必须记录

- run ID、开始/结束时间、操作者、数据库名和 PostgreSQL 版本；
- 输入 schema/table 行数及必要表的快照时间；
- SQL、Python、配置、原始导出和最终工件 SHA-256；
- Python 与核心依赖版本、随机种子；
- 每一步命令、退出码、stdout/stderr 日志；
- cohort flow、事件数、唯一键、时间窗、泄漏和缺失 QC；
- 与前一 run 的差异及解释；
- 失败步骤和人工判断。

## 强制一致性检查

- `subject_id`、`hadm_id`、`stay_id` 在主队列均唯一且非空；
- predictor 不能使用 12 h 后信息；label、event time、death/follow-up 列全部排除；
- 主标签与患者级首次事件时间一一对应；
- 训练/验证拆分发生在插补、缩放、特征选择和校准之前；
- 主分析同时报告 AUROC、AUPRC、Brier、校准、DCA 和风险富集；
- 外部验证使用锁定特征顺序、预处理参数和系数。

## 数据库权限

推荐角色权限：

- `SELECT`：`mimiciv_hosp`、`mimiciv_icu`、`mimiciv_derived`；
- `USAGE`：上述 schema；
- `CREATE/USAGE`：仅新 schema `study_ahf_v3`；
- 不需要修改或删除 MIMIC 源表。

凭据应配置在本机 `.pgpass` 或受控环境变量中，不写入仓库、日志或聊天。
