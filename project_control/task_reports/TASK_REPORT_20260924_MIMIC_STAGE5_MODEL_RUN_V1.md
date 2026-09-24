# MIMIC Stage 5：冻结特征矩阵与竞争风险模型运行报告（2026-09-24）

## 结论先行

已在冻结的 MIMIC 紧凑特征矩阵上完成第一轮正式模型运行。主开发队列为 V4（1,083 个 ICU stay），V3（761 个 stay）仅作为预先指定的严格表型敏感性层；两者没有被当作相互独立的外部验证集。

主模型使用 Fine–Gray 竞争风险框架，预测 T12 后 48 小时内“治疗升级相关血流动力学恶化或 ICU 内死亡”复合结局。活着离开 ICU 作为竞争事件，48 小时内未发生事件且仍可观察者为行政删失。

主模型在 V4 的表观 48 小时 AUC 为 0.695；经 200 次 bootstrap 乐观校正后为 0.675。V3 敏感性层表观 AUC 为 0.692，100 次 bootstrap 乐观校正后为 0.669。结果提示模型具有中等区分度，但还不能称为临床可部署模型，必须待本院时间外部验证及再校准后再作结论。

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

## 模型与内部验证

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

1. 这是 MIMIC 内部开发与 bootstrap 校正，不是本院外部验证；本院验证切点尚未冻结。
2. 当前运行的是结构化紧凑矩阵基线。V4 的 ED 症状文本/NLP 增量版本尚未纳入，不能把本结果写成“多模态模型”。
3. Fine–Gray 系数是预测模型参数，不是病因效应或治疗因果效应；不能依据 p 值宣称某变量是独立危险因素。
4. 本院 eMAR 尚未回传前，无法把本院治疗升级结局重建为执行级定义；取得 eMAR 后需重建本院 T12–T60 结局，再按冻结模型进行时间外部验证。

## 下一步

1. 对 MIMIC 模型做独立复核：检查矩阵行数、stay 唯一性、缺失处理参数和预测值范围，并将质量门写入运行登记。
2. 待本院 eMAR 到位后，按同一治疗升级合同重建本院 T12–T60 复合结局。
3. 冻结本院时间外部验证切点；仅使用冻结的 10 个特征和 MIMIC 模型参数，报告区分度、校准、决策曲线、亚组与分布漂移。
4. 外部验证完成后，再决定是否增加 ED 症状文本增量层、动态轨迹特征或再校准；这些不能在主模型结果出来后临时改写。
