SQL 生成数据库表
→ 导出 CSV 到 data/raw
→ Python QC 到 outputs/qc
→ 模型结果到 outputs/tables, outputs/figures, outputs/models
→ 变量清单到 docs

| 指标            | 结果   |
| --------------- | ------ |
| Test AUROC      | 0.714  |
| Test AUPRC      | 0.242  |
| Test Brier      | 0.199  |
| Test event rate | 13.81% |

# 我建议采用的算法筛选方法

目前最适合你的是：

```
Elastic Net + bootstrap stability selection
```

也就是：

1. 在训练集上重复抽样，比如 100 次；
2. 每次用 elastic-net logistic 训练；
3. 记录每个变量被选中的次数；
4. 计算 selection frequency；
5. 保留稳定出现的变量，比如频率 ≥30% 或 ≥50%；
6. 用这些稳定变量建立简化模型；
7. 在测试集上评估。

这样比单次 LASSO 更稳，因为单次 LASSO 很容易因为样本波动选择不同变量。

| 变量                               | 频率 | 方向 | 临床含义                             |
| ---------------------------------- | ---- | ---- | ------------------------------------ |
| `sbp_min`                          | 1.00 | 负   | 早期最低收缩压越低，后续恶化风险越高 |
| `sbp_last`                         | 1.00 | 负   | landmark 前收缩压越低，风险越高      |
| `rr_mean`                          | 0.92 | 正   | 呼吸频率高提示应激/肺淤血/感染严重   |
| `aniongap_mean`                    | 0.92 | 正   | 代谢紊乱越重，风险越高               |
| `nee_0_12h_last`                   | 0.90 | 正   | 早期升压药剂量越高，风险越高         |
| `creatinine_delta`                 | 0.90 | 正   | 早期肾功能恶化趋势                   |
| `vasopressor_any_0_12h_flag`       | 0.90 | 正   | 已需升压药支持                       |
| `aniongap_max`                     | 0.88 | 正   | 酸碱/灌注异常                        |
| `hr_delta`                         | 0.88 | 正   | 心率变化趋势                         |
| `temp_mean`                        | 0.84 | 负   | 低体温/体温反应异常可能提示重症      |
| `lactate_available_flag`           | 0.80 | 正   | 是否检测乳酸，本身反映临床重症关注   |
| `norepinephrine_0_12h_flag`        | 0.78 | 正   | 早期去甲肾上腺素使用                 |
| `low_urineoutput_0_12h_crude_flag` | 0.76 | 正   | 低尿量                               |
| `early_sepsis12_max_sofa_score`    | 0.76 | 正   | 早期器官功能障碍严重度               |



| 模型                                    | 特征数 | Test AUROC | Test AUPRC | 判断                        |
| --------------------------------------- | ------ | ---------- | ---------- | --------------------------- |
| freq ≥0.80 compact elastic-net          | 20     | 0.691      | 0.229      | 太精简，性能下降            |
| top30 compact elastic-net               | 24     | 0.694      | 0.227      | 也偏少                      |
| top50 compact elastic-net               | 44     | 0.708      | 0.237      | 很好的折中                  |
| freq ≥0.50 compact elastic-net          | 55     | 0.706      | 0.237      | 可作为备选                  |
| top80 compact elastic-net               | 68     | **0.711**  | **0.243**  | 当前最佳简化模型            |
| freq ≥0.30 compact elastic-net          | 102    | 0.700      | 0.239      | 变量多但性能没更好          |
| portable top50 compact elastic-net      | 36     | 0.684      | 0.239      | 外部验证友好，但 AUROC 下降 |
| portable freq ≥0.50 compact elastic-net | 45     | 0.683      | 0.239      | 类似 portable top50         |



68 个变量，明显少于 full model；
性能几乎等同 full elastic-net；
是算法筛选结果，不是人工筛选；
AUPRC 最高。

——————————

```
073：候选模型正式评估
```

重点评估三个模型：

```
1. full_elasticnet_reference
2. top80_compact_elasticnet
3. portable_top50_compact_elasticnet
```

输出：

```
AUROC / AUPRC / Brier
校准表
风险十分位事件率
top 10%、top 20%、top 30% 高风险组事件率
ROC / PR / calibration 图
```

| 模型                   | 特征数 | AUROC | 95% CI      | AUPRC | 95% CI      | Brier |
| ---------------------- | ------ | ----- | ----------- | ----- | ----------- | ----- |
| full elastic-net       | 357    | 0.714 | 0.644–0.774 | 0.242 | 0.178–0.329 | 0.199 |
| top50 compact          | 44     | 0.708 | 0.639–0.767 | 0.237 | 0.177–0.320 | 0.199 |
| top80 compact          | 68     | 0.711 | 0.642–0.768 | 0.243 | 0.181–0.331 | 0.198 |
| portable top50 compact | 36     | 0.684 | 0.614–0.744 | 0.239 | 0.174–0.334 | 0.211 |

| 模型                              | 特征数 | AUROC     | AUPRC     | Brier     |
| --------------------------------- | ------ | --------- | --------- | --------- |
| top50 compact weighted + Platt    | 44     | 0.708     | 0.237     | 0.118     |
| top50 compact unweighted + Platt  | 44     | 0.707     | 0.233     | 0.118     |
| top80 compact weighted + Platt    | 68     | **0.711** | **0.243** | **0.117** |
| top80 compact unweighted + Platt  | 68     | 0.707     | 0.236     | 0.118     |
| portable top50 weighted + Platt   | 36     | 0.684     | 0.239     | 0.117     |
| portable top50 unweighted + Platt | 36     | 0.687     | 0.234     | 0.117     |

目前综合最好的是：

```
top80_compact_weighted_platt
```

| 模型                                    | 定位                                     |
| --------------------------------------- | ---------------------------------------- |
| `top80_compact_weighted_platt`          | 主模型候选，内部性能最好                 |
| `top50_compact_weighted_platt`          | 简洁模型候选，性能接近且变量更少         |
| `portable_top50_compact_weighted_platt` | 外部验证优先模型，去掉流程/编码/科室变量 |

![image-20260501202622002](/Users/zheyu/Library/Application Support/typora-user-images/image-20260501202622002.png)

在训练集内通过 elastic-net 与 bootstrap stability selection 进行算法筛选后，top50/top80 compact 模型在测试集上取得接近全变量模型的区分度。经 cross-fitted Platt scaling 校准后，top80 compact weighted 模型表现最佳，测试集 AUROC 为 0.711、AUPRC 为 0.243、Brier score 为 0.117。风险分层显示，高风险前 20% 患者事件率约 24.7%，高风险前 30% 可捕获约 61.2% 的事件。模型主要适合用于 ICU 入科早期的血流动力学恶化风险分层和预警。

072：baseline elastic-net
072C：算法稳定特征筛选
072D：筛选阈值敏感性分析
073：候选模型评估
073B：概率校准



| 模型                          | Test AUROC mean ± SD | Test AUPRC mean ± SD | Brier mean ± SD   | 判断                   |
| ----------------------------- | -------------------- | -------------------- | ----------------- | ---------------------- |
| `top80_elasticnet_platt`      | **0.754 ± 0.029**    | 0.337 ± 0.042        | **0.107 ± 0.004** | 最稳，推荐主模型候选   |
| `top80_lightgbm_platt`        | 0.743 ± 0.031        | 0.339 ± 0.041        | 0.107 ± 0.003     | 性能接近，但过拟合明显 |
| `top50_histgb_platt`          | 0.742 ± 0.030        | **0.342 ± 0.044**    | 0.107 ± 0.003     | 可作为非线性 benchmark |
| `portable_top50_histgb_platt` | 0.718 ± 0.032        | 0.324 ± 0.038        | 0.109 ± 0.002     | 外部验证友好模型       |

训练-测试差距：

| 模型                          | Train AUROC | Test AUROC | AUROC gap | Train AUPRC | Test AUPRC | AUPRC gap |
| ----------------------------- | ----------- | ---------- | --------- | ----------- | ---------- | --------- |
| `top80_elasticnet_platt`      | 0.804       | 0.754      | 0.050     | 0.389       | 0.337      | 0.051     |
| `top80_lightgbm_platt`        | 0.999       | 0.743      | 0.256     | 0.993       | 0.339      | 0.653     |
| `top50_histgb_platt`          | 0.928       | 0.742      | 0.186     | 0.714       | 0.342      | 0.372     |
| `portable_top50_histgb_platt` | 0.904       | 0.718      | 0.187     | 0.633       | 0.324      | 0.309     |

| 模型                          | Top 20% event rate | Top 20% 捕获事件比例 |
| ----------------------------- | ------------------ | -------------------- |
| `top80_elasticnet_platt`      | 32.5%              | 47.0%                |
| `top80_lightgbm_platt`        | 32.9%              | 47.7%                |
| `top50_histgb_platt`          | 32.3%              | 46.7%                |
| `portable_top50_histgb_platt` | 30.7%              | 44.4%                |

过拟合——

| 模型                      | Train AUROC | Test AUROC | 过拟合程度 |
| ------------------------- | ----------- | ---------- | ---------- |
| top80 elastic-net + Platt | 0.804       | 0.754      | 可接受     |
| top50 HistGB + Platt      | 0.928       | 0.742      | 明显过拟合 |
| top80 LightGBM + Platt    | 0.999       | 0.743      | 严重过拟合 |
| portable HistGB + Platt   | 0.904       | 0.718      | 明显过拟合 |

敏感性——

| 缺失处理策略                    | 特征数 | AUROC mean ± SD   | AUPRC mean ± SD   | Brier mean ± SD     |
| ------------------------------- | ------ | ----------------- | ----------------- | ------------------- |
| current strategy                | 68     | 0.754 ± 0.029     | 0.337 ± 0.042     | 0.1069 ± 0.0040     |
| no generated missing indicators | 68     | 0.754 ± 0.029     | 0.337 ± 0.042     | 0.1069 ± 0.0040     |
| no missingness features         | 66     | **0.754 ± 0.028** | **0.338 ± 0.042** | **0.1068 ± 0.0040** |
| low missing ≤30%                | 62     | 0.751 ± 0.028     | 0.330 ± 0.042     | 0.1073 ± 0.0037     |
| NEE median instead of zero      | 68     | 0.753 ± 0.028     | 0.335 ± 0.041     | 0.1071 ± 0.0039     |

1. 去掉 generated missing indicators 后，模型几乎完全不变；
2. 去掉 available_flag / missingness features 后，性能没有下降；
3. 只保留缺失率 ≤30% 的变量，性能仅轻度下降；
4. NEE 缺失填 0 vs 中位数填补，结果几乎一致。

![image-20260506202235507](/Users/zheyu/Library/Application Support/typora-user-images/image-20260506202235507.png)

| 敏感性策略               | 特征数 | AUROC mean ± SD   | AUPRC mean ± SD   | Brier mean ± SD     |
| ------------------------ | ------ | ----------------- | ----------------- | ------------------- |
| current top80            | 68     | **0.754 ± 0.029** | **0.337 ± 0.042** | **0.1069 ± 0.0040** |
| no NEE                   | 65     | 0.751 ± 0.028     | 0.332 ± 0.042     | 0.1072 ± 0.0037     |
| no dose, keep exposure   | 65     | 0.751 ± 0.028     | 0.332 ± 0.042     | 0.1072 ± 0.0037     |
| broad exposure only      | 62     | 0.751 ± 0.028     | 0.330 ± 0.041     | 0.1073 ± 0.0037     |
| no vaso / inotrope / NEE | 61     | 0.744 ± 0.030     | 0.321 ± 0.041     | 0.1082 ± 0.0037     |

![image-20260506203910385](/Users/zheyu/Library/Application Support/typora-user-images/image-20260506203910385.png)

075 repeated internal validation：
证明 elastic-net 主模型比 LightGBM 更稳，过拟合更少。

075B missing data sensitivity：
证明模型不依赖某一种缺失值处理策略。

076 treatment-support sensitivity：
证明模型不完全依赖早期升压药 / NEE / 强心药变量。

\

59 个 active predictors 的模块结构合理

| 模块                              | active features |
| --------------------------------- | --------------- |
| Vital signs                       | 10              |
| Comorbidities                     | 7               |
| Perfusion / blood gas / acid-base | 7               |
| Vasoactive / inotropic support    | 7               |
| AHF evidence / diagnosis          | 4               |
| Complete blood count              | 4               |
| ICU unit / care process           | 4               |
| Chemistry / renal / electrolytes  | 3               |
| Urine output / renal perfusion    | 2               |
| Infection timing / care process   | 2               |
| Coagulation                       | 2               |
| Sepsis / illness severity         | 2               |
| Demographics                      | 1               |
| Neurologic status                 | 1               |
| Respiratory support               | 1               |

这个分布符合研究问题：不是单一依赖药物或诊断编码，而是包含血压、呼吸、酸碱/灌注、肾功能、尿量、感染严重程度、合并症和治疗支持。

078_final_model_visualization.py

\1. 绘制最终 active model 的 top 20 系数条形图；
\2. 绘制 active predictors 的模块分布图；
\3. 输出可用于论文/汇报的主模型解释图；
\4. 生成 top 20 / top 30 系数表。