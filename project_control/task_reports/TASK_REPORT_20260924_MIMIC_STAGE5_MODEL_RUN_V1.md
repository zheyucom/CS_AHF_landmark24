# MIMIC Stage 5：探索性模型压力测试报告（2026-09-24，状态已更正）

> **状态更正（2026-09-24）：`exploratory_only / not_for_inference / not_model_freeze`。**
>
> 本轮是在研究一仍在推进、第二阶段重置合同尚未完成时提前执行的技术性压力测试。它没有按原方案完成惩罚化建模、部署兼容的缺失处理、患者级重采样和完整性能评价，因此不得作为正式模型、论文结果、锁模对象或本院外部验证输入。下列数值只用于定位数据和流程薄弱点。

## 结论先行

已在冻结的 MIMIC 紧凑特征矩阵上完成一次探索性压力测试。主开发队列为 V4（1,083 个 ICU stay），V3（761 个 stay）仅作为预先指定的严格表型敏感性层；两者没有被当作相互独立的外部验证集。

本次压力测试使用普通 Fine–Gray 竞争风险框架，预测 T12 后 48 小时内“治疗升级相关血流动力学恶化或 ICU 内死亡”复合结局。活着离开 ICU 作为竞争事件，48 小时内未发生事件且仍可观察者为行政删失。它不是方案预定的惩罚化正式模型。

压力测试在 V4 的表观 48 小时 AUC 为 0.695；经 200 次 stay 级 bootstrap 后为 0.675。V3 敏感性层表观 AUC 为 0.692，100 次 stay 级 bootstrap 后为 0.669。由于本轮流程不符合正式锁模合同，这些数值不用于判断最终模型优劣；它们仅提示当前十变量静态矩阵的信息量有限。

## 本轮暴露的关键问题

1. **执行顺序错误：**研究一尚未完成，第二阶段重置方案也未封存，本轮不应被称为正式模型运行。
2. **特征层过窄：**十个特征主要是实验室最后值和 MAP，缺少心率、呼吸、SpO₂、尿量、T12 基线支持状态及 T0–T12 动态变化。
3. **关键变量缺失过高：**V4 的 NT-proBNP 仅 185/1,083 可用（17.1%），不适合作为核心模型必备变量；乳酸和 pH 也分别缺失 36.2% 和 30.2%。
4. **缺失处理与原方案不一致：**本轮使用训练样本中位数插补，未完成部署兼容的缺失策略比较，也没有执行原计划中的完整重采样内插补/惩罚选择。
5. **结局组成不均衡：**V4 的 182 个目标事件中，血管活性药新启动 136 例（74.7%），ICU 死亡 22 例、NEE 强化 20 例、机械支持 4 例；当前标签主要反映治疗升级行为，必须审计感染、围术期、镇静和 ICU 实践差异的影响。
6. **验证不完整：**bootstrap 以 stay 为单位，尚未审计同一 `subject_id` 的重复 episode；未完成患者级聚类重采样、嵌套惩罚调参、校准截距/斜率、决策曲线或时间验证。

正式第二阶段必须先按 `MIMIC_STAGE2_RESET_PROTOCOL_V2_20260924.md` 通过重新设计的无运行门槛；本文件不再承担正式模型报告功能。

## 数据与结局

- 冻结矩阵：`project_control/runs/20260924_mimic_compact_feature_matrix_v1.csv`（本地生成文件，已被 `.gitignore` 排除，不提交 GitHub）。
- BigQuery 建表 SQL：`project_control/bigquery/160_freeze_mimic_dhf_compact_feature_matrix_v1.sql`。
- 独立质量门 SQL：`project_control/bigquery/161_verify_mimic_dhf_compact_feature_matrix_v1.sql`。
- V4：1,083 行；目标事件 182，竞争事件 514，行政删失 387。
- V3：761 行；目标事件 164，竞争事件 313，行政删失 284。
- 所有事件时间均由 T12 起算并截断在 48 小时；未通过时间顺序和事件状态校验的行会直接终止运行。

## 预先冻结的 10 个特征

`age_years`、`ntprobnp_log1p`、`lactate_log1p_raw`、`bun_log1p_blood_only`、`creatinine_log1p`、`ph_raw`、`sodium_raw`、`hemoglobin_raw`、`wbc_log1p`、`mbp_raw`。

血尿素氮只接受血样、itemid 51006、精确数值；体液 BUN 不进入矩阵。乳酸主矩阵使用可追溯的原始精确测量，derived 乳酸没有偷偷并入主模型。缺失值用训练样本中位数插补，连续变量用训练样本均值和标准差标准化；bootstrap 每次重新估计这些参数，避免信息泄漏。

## 压力测试流程（非正式内部验证）

模型脚本：`project_control/run_mimic_stage5_model.R`。

- Fine–Gray 子分布风险模型，目标原因为 1，活着离开 ICU 为竞争原因为 2。
- 10 个预先冻结特征全部保留；没有按本院 G7 结果筛特征，也没有用结局显著性做逐步选择。
- 训练集内插补、标准化；V4 使用 200 次 bootstrap，V3 使用 100 次 bootstrap，计算 AUC/Brier 的乐观校正值。
- 48 小时风险、AUC 与 Brier 由 `riskRegression::Score` 计算；校准表使用含竞争事件的 Aalen–Johansen 累积发生率。

## 主要结果

| 队列 | n | 目标事件 | 竞争事件 | 行政删失 | 表观 AUC | 乐观校正 AUC | 表观 Brier | 乐观校正 Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V4 主开发 | 1,083 | 182 | 514 | 387 | 0.695 | 0.675 | 0.130 | 0.131 |
| V3 严格敏感性 | 761 | 164 | 313 | 284 | 0.692 | 0.669 | 0.152 | 0.152 |

V4 十分位校准中，平均预测风险从 0.050（最低十分位）升至 0.404（最高十分位），Aalen–Johansen 观察到的 48 小时累积发生率从 0.065 升至 0.417；中间十分位有随机波动，后续外部验证需重新报告校准截距、斜率和决策曲线。

## 输出文件（完整路径）

模型运行目录：

`/Users/zheyu/Desktop/CS_AHF_landmark24/project_control/runs/20260924_mimic_stage5_model_v1/`

其中包括：

- `model_performance_summary.csv`：V4/V3 事件数、AUC、Brier 与 bootstrap 校正结果；
- `coefficients_V4_main.csv`、`coefficients_V3_strict_sensitivity.csv`：标准化特征的 Fine–Gray 系数、HR、95% CI；
- `calibration_deciles_V4_main.csv`、`calibration_deciles_V3_strict_sensitivity.csv`：48 小时十分位校准表；
- `predictions_V4_main_full.csv`、`predictions_V3_strict_sensitivity_full.csv`：本地受控的 stay-level 预测结果；
- `preprocessing_V4_main.csv`、`preprocessing_V3_strict_sensitivity.csv`：训练样本插补/标准化参数；
- `bootstrap_V4_main.csv`、`bootstrap_V3_strict_sensitivity.csv`：内部验证迭代明细；
- `sessionInfo.txt`：R 包和运行环境记录。

## 当前不能过度解读的地方

1. 这是 MIMIC 探索性压力测试，不是正式内部开发、更不是本院外部验证；本院验证切点尚未冻结。
2. 当前运行的是结构化紧凑矩阵基线。V4 的 ED 症状文本/NLP 增量版本尚未纳入，不能把本结果写成“多模态模型”。
3. Fine–Gray 系数是预测模型参数，不是病因效应或治疗因果效应；不能依据 p 值宣称某变量是独立危险因素。
4. 本院 eMAR 尚未回传前，无法把本院治疗升级结局重建为执行级定义；取得 eMAR 后需重建本院 T12–T60 结局，再按冻结模型进行时间外部验证。

## 下一步

1. 继续研究一，不继续运行第二阶段模型。
2. 按 `MIMIC_STAGE2_RESET_PROTOCOL_V2_20260924.md` 完成患者级 episode、结局组成、变量可得性、动态特征、缺失策略和正式验证方案。
3. 待本院 eMAR 到位后，按同一治疗升级合同重建本院 T12–T60 复合结局，但不提前读取外部验证性能。
4. 重置方案全部硬门通过后，使用新版本号重新开始 M0–M3 递进开发；本次十特征压力测试不继承为正式基线模型。
